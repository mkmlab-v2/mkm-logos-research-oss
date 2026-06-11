#!/usr/bin/env python3
"""[HYPO] Open-bench B-track research sweep — golden40 variant grid (research_only, SEND_GATE HOLD)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
POC = ROOT / "scripts/run_customer_compression_stateless_poc_v1.py"
GOLDEN40 = ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl"
OUT_DEFAULT = ROOT / "reports/compression_open_bench_research_sweep_v1_latest.json"
SCHEMA = "compression_open_bench_research_sweep_v1"

VARIANTS: list[dict[str, Any]] = [
    {
        "variant_id": "baseline_routed_economy",
        "label_ko": "현행 앵커 — CHAT-D1 routed · economy",
        "sku": "MKM-CHAT-D1",
        "compression_profile": "economy",
        "auto_b2b_overlay": False,
        "graph_wire": False,
    },
    {
        "variant_id": "routed_economy_b2b_overlay",
        "label_ko": "CHAT-D1 + B2B must_keep overlay · economy",
        "sku": "MKM-CHAT-D1",
        "compression_profile": "economy",
        "auto_b2b_overlay": True,
        "graph_wire": False,
    },
    {
        "variant_id": "routed_literal_b2b_overlay",
        "label_ko": "CHAT-D1 + overlay · literal (산업 PoC 동일 프로파일)",
        "sku": "MKM-CHAT-D1",
        "compression_profile": "literal",
        "auto_b2b_overlay": True,
        "graph_wire": False,
    },
    {
        "variant_id": "routed_economy_graph_wire",
        "label_ko": "CHAT-D1 + graph_wire_selective_bridge · economy",
        "sku": "MKM-CHAT-D1",
        "compression_profile": "economy",
        "auto_b2b_overlay": False,
        "graph_wire": True,
    },
    {
        "variant_id": "routed_literal_no_overlay",
        "label_ko": "CHAT-D1 · literal (overlay 없음)",
        "sku": "MKM-CHAT-D1",
        "compression_profile": "literal",
        "auto_b2b_overlay": False,
        "graph_wire": False,
    },
    {
        "variant_id": "fin_e1_literal_overlay",
        "label_ko": "FIN-E1 shard + overlay · literal (교차 SKU)",
        "sku": "MKM-FIN-E1",
        "compression_profile": "literal",
        "auto_b2b_overlay": True,
        "graph_wire": False,
    },
    {
        "variant_id": "routed_literal_overlay_wire",
        "label_ko": "CHAT-D1 · literal + overlay + graph_wire",
        "sku": "MKM-CHAT-D1",
        "compression_profile": "literal",
        "auto_b2b_overlay": True,
        "graph_wire": True,
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _aggregate(report_path: Path) -> dict[str, Any]:
    if not report_path.is_file():
        return {"present": False}
    doc = json.loads(report_path.read_text(encoding="utf-8"))
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    raw_rate = agg.get("mean_token_saving_rate_proxy")
    return {
        "present": True,
        "case_count": doc.get("case_count"),
        "cases_passed": doc.get("cases_passed"),
        "raw": {
            "mean_token_saving_rate_proxy": raw_rate,
            "saving_pct_display": round(float(raw_rate) * 100, 2) if isinstance(raw_rate, (int, float)) else None,
            "mean_jaccard_proxy": agg.get("mean_jaccard_proxy"),
        },
        "must_keep_overlay_applied": (doc.get("must_keep_overlay") or {}).get("applied"),
        "compression_profile": doc.get("compression_profile"),
        "graph_wire_requested": doc.get("graph_wire_selective_bridge"),
    }


def _run_variant(v: dict[str, Any], *, corpus: Path, report_dir: Path) -> dict[str, Any]:
    report = report_dir / f"customer_compression_stateless_poc_golden40_sweep_{v['variant_id']}_v1_latest.json"
    cmd = [
        PY,
        str(POC),
        "--input-jsonl",
        str(corpus),
        "--sku",
        str(v["sku"]),
        "--compression-profile",
        str(v["compression_profile"]),
        "--max-cases",
        "40",
        "--out-json",
        str(report),
        "--relax-pass-gate",
    ]
    if v.get("auto_b2b_overlay"):
        cmd.append("--auto-b2b-overlay")
    if v.get("graph_wire"):
        cmd.append("--graph-wire-selective-bridge")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    row = {
        "variant_id": v["variant_id"],
        "label_ko": v.get("label_ko"),
        "sku": v.get("sku"),
        "report_path": str(report.relative_to(ROOT)).replace("\\", "/"),
        "exit_code": proc.returncode,
        "output_tail": (proc.stdout or proc.stderr or "").strip().splitlines()[-3:],
    }
    row.update(_aggregate(report))
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-jsonl", type=Path, default=GOLDEN40)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--extract-golden40-overlay",
        action="store_true",
        help="Also run corpus-derived overlay variant (tenant golden40-research).",
    )
    args = ap.parse_args(argv)

    corpus = args.corpus_jsonl if args.corpus_jsonl.is_absolute() else ROOT / args.corpus_jsonl
    if not corpus.is_file():
        raise SystemExit(f"missing corpus: {corpus}")

    report_dir = ROOT / "reports"
    rows = [_run_variant(v, corpus=corpus, report_dir=report_dir) for v in VARIANTS]

    if args.extract_golden40_overlay:
        overlay_out = ROOT / "docs/final/artifacts/tenant_golden40_research_must_keep_overlay_v1.json"
        ext = subprocess.run(
            [
                PY,
                str(ROOT / "scripts/extract_tenant_must_keep_from_corpus_v1.py"),
                "--tenant-id",
                "golden40-research",
                "--input-jsonl",
                str(corpus),
                "--min-freq",
                "2",
                "--max-terms",
                "48",
                "--out-json",
                str(overlay_out),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if ext.returncode == 0:
            report = report_dir / "customer_compression_stateless_poc_golden40_sweep_corpus_overlay_v1_latest.json"
            cmd = [
                PY,
                str(POC),
                "--input-jsonl",
                str(corpus),
                "--sku",
                "MKM-CHAT-D1",
                "--compression-profile",
                "economy",
                "--must-keep-overlay-json",
                str(overlay_out),
                "--max-cases",
                "40",
                "--out-json",
                str(report),
                "--relax-pass-gate",
            ]
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
            agg = _aggregate(report)
            rows.append(
                {
                    "variant_id": "routed_economy_corpus_extracted_overlay",
                    "label_ko": "CHAT-D1 + golden40 코퍼스 추출 overlay · economy",
                    "sku": "MKM-CHAT-D1",
                    "overlay_path": str(overlay_out.relative_to(ROOT)).replace("\\", "/"),
                    "report_path": str(report.relative_to(ROOT)).replace("\\", "/"),
                    "exit_code": proc.returncode,
                    "output_tail": (proc.stdout or proc.stderr or "").strip().splitlines()[-3:],
                    **agg,
                }
            )

    present = [r for r in rows if r.get("present") and r.get("exit_code") == 0]
    ranked = sorted(
        present,
        key=lambda r: float((r.get("raw") or {}).get("mean_token_saving_rate_proxy") or 0),
        reverse=True,
    )
    baseline = next((r for r in present if r["variant_id"] == "baseline_routed_economy"), None)
    baseline_rate = float((baseline or {}).get("raw", {}).get("mean_token_saving_rate_proxy") or 0)
    best = ranked[0] if ranked else None
    best_rate = float((best or {}).get("raw", {}).get("mean_token_saving_rate_proxy") or 0)

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "corpus": str(corpus.relative_to(ROOT)).replace("\\", "/"),
        "baseline_variant_id": "baseline_routed_economy",
        "baseline_saving_pct": round(baseline_rate * 100, 2) if baseline else None,
        "variants": rows,
        "ranking_by_raw_saving": [
            {
                "variant_id": r["variant_id"],
                "saving_pct": (r.get("raw") or {}).get("saving_pct_display"),
                "jaccard": (r.get("raw") or {}).get("mean_jaccard_proxy"),
            }
            for r in ranked
        ],
        "best_variant": {
            "variant_id": best.get("variant_id") if best else None,
            "saving_pct": (best.get("raw") or {}).get("saving_pct_display") if best else None,
            "delta_pp_vs_baseline": round((best_rate - baseline_rate) * 100, 2) if best and baseline else None,
        },
        "verdict_ko": (
            f"최고 변형 {best['variant_id']} raw {(best.get('raw') or {}).get('saving_pct_display')}% "
            f"(baseline 대비 {(best_rate - baseline_rate) * 100:+.2f}pp) — Track A·대외 헤드라인 자동 승격 없음"
            if best
            else "측정 실패"
        ),
        "forbidden": [
            "Track A 47.5% merge",
            "ready_for_external_send without customer PoC",
            "repair-only uplift as core proof",
        ],
        "chain_ok": all(r.get("exit_code") == 0 for r in rows),
    }

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    if best:
        print(
            f"best={best['variant_id']} "
            f"{(best.get('raw') or {}).get('saving_pct_display')}% "
            f"delta_pp={doc['best_variant'].get('delta_pp_vs_baseline')}"
        )
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
