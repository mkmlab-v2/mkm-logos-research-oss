#!/usr/bin/env python3
"""Open Bench chain: public corpora + SKU PoC + dual-report (B-track, SEND_GATE HOLD)."""
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
OUT_DEFAULT = ROOT / "reports/compression_open_bench_chain_v1_latest.json"
SCHEMA = "compression_open_bench_chain_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(step_id: str, script: str, *extra: str) -> dict[str, Any]:
    cmd = [PY, str(ROOT / "scripts" / script), *extra]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return {
        "step": step_id,
        "script": script,
        "exit_code": proc.returncode,
        "output_tail": out.strip().splitlines()[-6:] if out else [],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-expand", action="store_true")
    ap.add_argument("--skip-evidence-tail", action="store_true", help="Skip reproduce pack / landing payload")
    args = ap.parse_args(argv)

    steps: list[dict[str, Any]] = []

    if not args.skip_expand:
        steps.append(_run("expand_open_corpus", "expand_compression_open_structured_corpus_v1.py", "--std-count", "128", "--long-count", "48"))

    steps.append(_run("golden40_corpus", "build_compression_golden40_public_safe_corpus_v1.py", "--max-cases", "40", "--strict"))
    steps.append(_run("industry_corpora", "build_compression_b2b_industry_poc_corpus_v1.py"))
    steps.append(_run("sku_poc_bundle", "run_compression_b2b_sku_industry_poc_bundle_v1.py", "--skip-build"))

    steps.append(
        _run(
            "poc_golden40_stateless",
            "run_customer_compression_stateless_poc_v1.py",
            "--input-jsonl",
            "data/compression/stateless_poc_golden40_public_safe_v1.jsonl",
            "--max-cases",
            "40",
            "--out-json",
            "reports/customer_compression_stateless_poc_golden40_public_safe_v1_latest.json",
            "--relax-pass-gate",
        )
    )
    steps.append(
        _run(
            "poc_golden40_routed",
            "run_customer_compression_stateless_poc_v1.py",
            "--input-jsonl",
            "data/compression/stateless_poc_golden40_public_safe_v1.jsonl",
            "--sku",
            "MKM-CHAT-D1",
            "--max-cases",
            "40",
            "--out-json",
            "reports/customer_compression_stateless_poc_golden40_public_safe_routed_v1_latest.json",
            "--relax-pass-gate",
        )
    )
    steps.append(
        _run(
            "poc_open_structured",
            "run_customer_compression_stateless_poc_v1.py",
            "--input-jsonl",
            "data/compression/stateless_poc_open_structured_v1.jsonl",
            "--max-cases",
            "128",
            "--out-json",
            "reports/customer_compression_stateless_poc_open_structured_v1_latest.json",
        )
    )
    steps.append(_run("dual_report", "build_compression_open_bench_dual_report_v1.py"))
    steps.append(_run("persuasion_deck", "build_compression_open_bench_persuasion_deck_v1.py"))

    if not args.skip_evidence_tail:
        steps.append(_run("reproduce_pack", "build_compression_public_reproduce_pack_v1.py"))
        steps.append(_run("bench_landing", "build_a_codeai_public_bench_landing_payload_v1.py"))

    exit_codes = [s["exit_code"] for s in steps]
    dual = {}
    dual_path = ROOT / "reports/compression_open_bench_dual_report_v1_latest.json"
    if dual_path.is_file():
        dual = json.loads(dual_path.read_text(encoding="utf-8"))

    bundle = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "steps": steps,
        "dual_report_summary": dual.get("summary"),
        "non_zero_corpora": [
            r.get("label")
            for r in (dual.get("corpora_and_skus") or [])
            if r.get("non_zero_saving")
        ],
        "chain_ok": all(c == 0 for c in exit_codes),
        "artifacts": {
            "dual_report": "reports/compression_open_bench_dual_report_v1_latest.json",
            "sku_bundle": "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json",
            "golden40_poc": "reports/customer_compression_stateless_poc_golden40_public_safe_v1_latest.json",
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(f"chain_ok={bundle['chain_ok']} non_zero={bundle.get('non_zero_corpora')}")
    return 0 if bundle["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
