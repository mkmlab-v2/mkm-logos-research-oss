#!/usr/bin/env python3
"""Smoke: hybrid codec router lib + v2 stub on WTT CS 30-case corpus [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CORPUS = ROOT / "data/compression/stateless_poc_prospect_wtt-premium-cs-customer-v1_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/compression_hybrid_codec_router_smoke_v1_latest.json"
JACCARD_FLOOR = 0.73


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_cases(path: Path, max_cases: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or len(rows) >= max_cases:
            continue
        obj = json.loads(line)
        text = obj.get("text")
        if isinstance(text, str) and text.strip():
            rows.append(obj)
    return rows


def _run_corpus_gate(router: str, *, corpus: Path, max_cases: int) -> dict[str, Any]:
    from fastapi.testclient import TestClient
    from scripts.compression_b2b_must_keep_overlay_v1_lib import load_overlay_terms
    from scripts.compression_b2b_off_the_shelf_shard_sku_v1_lib import build_sku_context
    from scripts.compression_token_api_v2_stub import app
    from scripts.report_multilens_performance_eval import _jaccard

    overlay_path = ROOT / "docs/final/artifacts/tenant_wtt-premium-cs-customer-v1_must_keep_overlay_v1.json"
    overlay = load_overlay_terms(overlay_path) if overlay_path.is_file() else []
    sku_ctx = build_sku_context(
        workspace_root=ROOT,
        spec_path=ROOT / "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json",
        external_sku="MKM-CHAT-D1",
        shard_json_override=None,
    )
    forced_shard = sku_ctx.get("forced_shard_id") or sku_ctx.get("override_shard_id")

    client = TestClient(app)
    cases = _load_cases(corpus, max_cases)
    passed = 0
    fail_ids: list[str] = []
    fallback_count = 0
    per_case: list[dict[str, Any]] = []

    for obj in cases:
        row_id = str(obj["id"])
        body = {
            "text": obj["text"],
            "loss_profile": "semantic_general",
            "compression_profile": "economy",
            "client_request_id": row_id,
            "stateless_packet": True,
            "hybrid_codec_router": router,
            "session_turns": obj.get("turns"),
            "must_keep_overlay_terms": overlay or None,
            "forced_shard_id": forced_shard,
        }
        cr = client.post("/v2/compress", json=body)
        if cr.status_code != 200:
            fail_ids.append(row_id)
            per_case.append({"id": row_id, "ok": False, "error": cr.text[:120]})
            continue
        flags = cr.json().get("integrity_flags") or {}
        pkt = cr.json()["compression_packet"]
        er = client.post("/v2/expand", json={"compression_packet": pkt, "decode_mode": "codebook_only"})
        expanded = er.json().get("text") or "" if er.status_code == 200 else ""
        jac = float(_jaccard(obj["text"], expanded))
        ok = jac >= JACCARD_FLOOR
        if ok:
            passed += 1
        else:
            fail_ids.append(row_id)
        if flags.get("hybrid_codec_fallback_used"):
            fallback_count += 1
        per_case.append(
            {
                "id": row_id,
                "ok": ok,
                "jaccard_proxy": round(jac, 6),
                "compression_profile_effective": flags.get("compression_profile_effective"),
                "hybrid_codec_route_reason": flags.get("hybrid_codec_route_reason"),
                "hybrid_codec_fallback_used": flags.get("hybrid_codec_fallback_used"),
            }
        )

    n = len(cases)
    return {
        "router": router,
        "case_count": n,
        "cases_passed": passed,
        "pass_rate": round(passed / n, 4) if n else 0.0,
        "fail_ids": fail_ids,
        "fallback_used_count": fallback_count,
        "cases": per_case,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_compression_hybrid_codec_router_v1.py", "-q"],
            cwd=str(ROOT),
        )
        if proc.returncode != 0:
            return proc.returncode

    corpus = args.corpus.resolve()
    results = [
        _run_corpus_gate("assistant_literal", corpus=corpus, max_cases=args.max_cases),
        _run_corpus_gate("economy_fallback", corpus=corpus, max_cases=args.max_cases),
    ]
    doc = {
        "schema": "compression_hybrid_codec_router_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_promotion": False,
        "jaccard_floor": JACCARD_FLOOR,
        "corpus": corpus.relative_to(ROOT).as_posix() if corpus.is_relative_to(ROOT) else str(corpus),
        "max_cases": args.max_cases,
        "policies": results,
        "conclusion_ko": (
            f"assistant_literal={results[0]['cases_passed']}/{args.max_cases}; "
            f"economy_fallback={results[1]['cases_passed']}/{args.max_cases}; Track A·SEND 승격 아님."
        ),
    }
    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    ok = all(r["cases_passed"] == r["case_count"] for r in results)
    print(json.dumps({r["router"]: f"{r['cases_passed']}/{r['case_count']}" for r in results}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
