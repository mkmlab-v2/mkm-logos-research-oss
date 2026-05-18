#!/usr/bin/env python3
"""Focused v2 routing A/B on bench case cmp2_011 (health shard · lexicon hit 0)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_v2_cmp2_011_routing_ab_latest.json"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
CASE_ID = "cmp2_011"
PROFILES = ("default", "track_a_promoted", "b_track_domain_relax")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_case_text() -> str:
    doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    for case in doc.get("compression_cases") or []:
        if isinstance(case, dict) and str(case.get("id")) == CASE_ID:
            return str(case.get("raw_text") or "")
    raise SystemExit(f"Case {CASE_ID} not found in {INPUT_V2}")


def run_ab() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    text = _load_case_text()
    client = TestClient(app)
    rows: list[dict[str, Any]] = []
    for profile in PROFILES:
        cr = client.post(
            "/v2/compress",
            json={
                "text": text,
                "loss_profile": "semantic_general",
                "client_request_id": CASE_ID,
                "routing_profile": profile,
            },
        )
        body = cr.json() if cr.status_code == 200 else {}
        metrics = body.get("compression_metrics") or {}
        flags = body.get("integrity_flags") or {}
        pkt = body.get("compression_packet") or {}
        route = pkt.get("router_meta") if isinstance(pkt, dict) else {}
        rows.append(
            {
                "routing_profile": profile,
                "http_status": cr.status_code,
                "token_in": metrics.get("token_in"),
                "token_out": metrics.get("token_out"),
                "savings_ratio": metrics.get("savings_ratio"),
                "shard_id": route.get("shard_id") if isinstance(route, dict) else None,
                "domain": route.get("domain") if isinstance(route, dict) else None,
                "routing_research_only": flags.get("routing_research_only"),
            }
        )
    base_s = rows[0].get("savings_ratio") if rows else None
    for row in rows[1:]:
        if base_s is not None and row.get("savings_ratio") is not None:
            row["delta_savings_vs_default"] = round(float(row["savings_ratio"]) - float(base_s), 6)
    return {
        "schema": "mkm_v2_cmp2_011_routing_ab_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "hypothesis_tier": "B",
        "case_id": CASE_ID,
        "raw_text_preview": text[:120] + ("..." if len(text) > 120 else ""),
        "boundary_ack": "Single bench case API replay — not full 40-case promotion. Track A signoff remains ssot top5 only.",
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_ab()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
