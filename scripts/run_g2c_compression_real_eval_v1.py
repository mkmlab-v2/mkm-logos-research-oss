#!/usr/bin/env python3
"""G2-c compression real-eval: v2 compress/expand roundtrip (not closed-dictionary proxy)."""

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

from scripts.compression_token_api_v2_stub import app  # noqa: E402
from scripts.report_multilens_performance_eval import _jaccard  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

DEFAULT_SPEC = ROOT / "docs/final/artifacts/g2c_compression_real_eval_spec_v1_latest.json"
DEFAULT_CORPUS = ROOT / "data/logos/verse_4pipeline_full_31102.json"
DEFAULT_JSONL = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_v1.jsonl"
DEFAULT_BASE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_PROXY = ROOT / "reports/g2a_candidate_compression_reconstruction_bench_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/g2c_compression_real_eval_v1_latest.json"

SAMPLE_INDICES = (0, 1000, 5000, 10000, 20000, 30000)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _mesh_prefix(row: dict[str, Any]) -> str:
    hints = row.get("sasang_routing_hints") or {}
    ref = row.get("gematria_path_ref") or {}
    return " ".join(
        [
            "[MESH]",
            f"VID:{row.get('verse_id')}",
            f"PID:{row.get('path_id')}",
            f"S16:{ref.get('state16')}",
            f"P:{hints.get('posture_hint')}",
            f"E:{hints.get('entropy_leg')}",
        ]
    )


def _sample_rows(*, corpus_path: Path, jsonl_path: Path, indices: tuple[int, ...]) -> list[dict[str, Any]]:
    corpus = _load_json(corpus_path)
    index = {
        str(r.get("verse_id")): str(r.get("text_preview") or "")
        for r in corpus
        if isinstance(r, dict) and r.get("verse_id")
    }
    rows: list[dict[str, Any]] = []
    with jsonl_path.open(encoding="utf-8-sig") as f:
        for i, raw in enumerate(f):
            if i not in indices:
                continue
            sidecar = json.loads(raw)
            if not isinstance(sidecar, dict):
                continue
            vid = str(sidecar.get("verse_id") or "")
            text = index.get(vid, "")
            rows.append(
                {
                    "jsonl_index": i,
                    "verse_id": vid,
                    "baseline_text": text,
                    "candidate_text": f"{_mesh_prefix(sidecar)} | {text}".strip(),
                }
            )
    return rows


def _roundtrip(
    client: TestClient,
    *,
    text: str,
    loss_profile: str,
    decode_mode: str,
) -> dict[str, Any]:
    cr = client.post(
        "/v2/compress",
        json={
            "text": text,
            "loss_profile": loss_profile,
            "client_request_id": "g2c-real-eval",
        },
    )
    if cr.status_code != 200:
        return {
            "ok": False,
            "http_status": cr.status_code,
            "error": cr.text[:500],
        }
    cj = cr.json()
    pkt = cj.get("compression_packet")
    metrics = cj.get("compression_metrics") or {}
    savings = metrics.get("savings_ratio")
    er = client.post("/v2/expand", json={"compression_packet": pkt, "decode_mode": decode_mode})
    if er.status_code != 200:
        return {
            "ok": False,
            "http_status": er.status_code,
            "error": er.text[:500],
            "savings_ratio": savings,
        }
    expanded = str(er.json().get("text") or "")
    jac = round(float(_jaccard(text, expanded)), 6)
    return {
        "ok": True,
        "char_len": len(text),
        "savings_ratio": savings,
        "roundtrip_jaccard": jac,
        "decode_mode": decode_mode,
    }


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) is not None]
    return round(sum(vals) / len(vals), 6) if vals else None


def build_report(
    *,
    spec_path: Path,
    corpus_path: Path,
    jsonl_path: Path,
    baseline_path: Path,
    proxy_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    spec = _load_json(spec_path)
    api = spec.get("api") or {}
    indices = tuple(spec.get("sample_strategy", {}).get("jsonl_line_indices") or SAMPLE_INDICES)
    samples = _sample_rows(corpus_path=corpus_path, jsonl_path=jsonl_path, indices=indices)

    client = TestClient(app)
    loss_profile = str(api.get("loss_profile") or "semantic_general")
    decode_mode = str(api.get("decode_mode") or "stub")

    per_row: list[dict[str, Any]] = []
    for sample in samples:
        base_rt = _roundtrip(client, text=sample["baseline_text"], loss_profile=loss_profile, decode_mode=decode_mode)
        cand_rt = _roundtrip(client, text=sample["candidate_text"], loss_profile=loss_profile, decode_mode=decode_mode)
        per_row.append(
            {
                "verse_id": sample["verse_id"],
                "jsonl_index": sample["jsonl_index"],
                "baseline": base_rt,
                "candidate": cand_rt,
            }
        )

    base_ok = [r["baseline"] for r in per_row if r["baseline"].get("ok")]
    cand_ok = [r["candidate"] for r in per_row if r["candidate"].get("ok")]

    base_metrics = {
        "savings_ratio_mean": _mean(base_ok, "savings_ratio"),
        "roundtrip_jaccard_mean": _mean(base_ok, "roundtrip_jaccard"),
        "sample_ok_count": len(base_ok),
    }
    cand_metrics = {
        "savings_ratio_mean": _mean(cand_ok, "savings_ratio"),
        "roundtrip_jaccard_mean": _mean(cand_ok, "roundtrip_jaccard"),
        "sample_ok_count": len(cand_ok),
    }

    multilens = _load_json(baseline_path) if baseline_path.is_file() else {}
    bm = multilens.get("compression_metrics") or {}
    proxy = _load_json(proxy_path) if proxy_path.is_file() else {}

    return {
        "schema": "g2c_compression_real_eval_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "eval_mode": spec.get("eval_mode"),
        "spec_ref": str(spec_path.relative_to(ROOT)).replace("\\", "/") if spec_path.is_file() else str(spec_path),
        "forbidden_methods": spec.get("forbidden_methods") or [],
        "sample_count": len(per_row),
        "arms": {
            "baseline": {"id": "verse_text_only", **base_metrics},
            "candidate": {"id": "mesh_sidecar_plus_verse", **cand_metrics},
        },
        "delta_candidate_minus_baseline": {
            "savings_ratio_delta": (
                round((cand_metrics["savings_ratio_mean"] or 0.0) - (base_metrics["savings_ratio_mean"] or 0.0), 6)
                if cand_metrics["savings_ratio_mean"] is not None and base_metrics["savings_ratio_mean"] is not None
                else None
            ),
            "roundtrip_jaccard_delta": (
                round((cand_metrics["roundtrip_jaccard_mean"] or 0.0) - (base_metrics["roundtrip_jaccard_mean"] or 0.0), 6)
                if cand_metrics["roundtrip_jaccard_mean"] is not None and base_metrics["roundtrip_jaccard_mean"] is not None
                else None
            ),
        },
        "contrast": {
            "multilens_active_report": {
                "global_token_saving_rate": bm.get("global_token_saving_rate"),
                "avg_reconstruction_fidelity_jaccard": bm.get("avg_reconstruction_fidelity_jaccard"),
            },
            "g2a_closed_dictionary_proxy": {
                "candidate_pointer_saving_rate_mean": proxy.get("candidate_pointer_saving_rate_mean"),
                "candidate_restore_jaccard_mean": proxy.get("candidate_restore_jaccard_mean"),
                "method": proxy.get("method"),
            },
        },
        "rows": per_row,
        "boundary_ack": "Real v2 compress/expand roundtrip — not closed-dictionary pointer proxy; Track A SLA gate remains separate.",
        "reproduce": "py scripts/run_g2c_compression_real_eval_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--baseline", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--proxy-bench", type=Path, default=DEFAULT_PROXY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.corpus.is_file():
        print(json.dumps({"ok": False, "error": f"missing corpus: {args.corpus}"}))
        return 1
    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing jsonl: {args.jsonl}"}))
        return 1
    if not args.spec.is_file():
        print(json.dumps({"ok": False, "error": f"missing spec: {args.spec}"}))
        return 1

    doc = build_report(
        spec_path=args.spec,
        corpus_path=args.corpus,
        jsonl_path=args.jsonl,
        baseline_path=args.baseline,
        proxy_path=args.proxy_bench,
        out_path=args.out,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "baseline_jaccard": doc["arms"]["baseline"]["roundtrip_jaccard_mean"],
                "candidate_jaccard": doc["arms"]["candidate"]["roundtrip_jaccard_mean"],
                "out": str(args.out),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
