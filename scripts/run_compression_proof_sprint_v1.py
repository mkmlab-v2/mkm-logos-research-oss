#!/usr/bin/env python3
"""Proof sprint — industry SKU gap + realistic corpora PoC + evidence index + readiness."""

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
OUT = ROOT / "reports/compression_proof_sprint_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-1500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-industry-bundle", action="store_true")
    ap.add_argument("--skip-evidence-lv1", action="store_true")
    ap.add_argument("--skip-handoff", action="store_true", help="Skip ops memory handoff bench in lv1 chain")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_industry_bundle:
        steps.append(
            _run(
                "industry_sku_bundle",
                [PY, "scripts/run_compression_b2b_sku_industry_poc_bundle_v1.py"],
            )
        )

    steps.append(
        _run(
            "expand_open_corpus",
            [PY, "scripts/expand_compression_open_structured_corpus_v1.py", "--std-count", "128", "--long-count", "48"],
        )
    )
    steps.append(
        _run(
            "golden40_corpus",
            [PY, "scripts/build_compression_golden40_public_safe_corpus_v1.py", "--max-cases", "40", "--strict"],
        )
    )
    steps.append(
        _run("composite_corpus", [PY, "scripts/build_compression_proof_sprint_composite_corpus_v1.py", "--max-total", "100"])
    )
    steps.append(
        _run(
            "poc_composite",
            [
                PY,
                "scripts/run_customer_compression_stateless_poc_v1.py",
                "--input-jsonl",
                "data/compression/stateless_poc_proof_sprint_composite_v1.jsonl",
                "--max-cases",
                "100",
                "--out-json",
                "reports/customer_compression_stateless_poc_proof_sprint_composite_v1_latest.json",
                "--relax-pass-gate",
            ],
        )
    )
    steps.append(
        _run(
            "poc_golden40_baseline",
            [
                PY,
                "scripts/run_customer_compression_stateless_poc_v1.py",
                "--input-jsonl",
                "data/compression/stateless_poc_golden40_public_safe_v1.jsonl",
                "--max-cases",
                "40",
                "--out-json",
                "reports/customer_compression_stateless_poc_golden40_public_safe_v1_latest.json",
                "--relax-pass-gate",
            ],
        )
    )

    if not args.skip_evidence_lv1:
        lv1_cmd = [PY, "scripts/run_compression_evidence_lv1_chain_v1.py"]
        if args.skip_handoff:
            lv1_cmd.append("--skip-handoff")
        steps.append(_run("evidence_lv1_chain", lv1_cmd))
    else:
        steps.append(_run("evidence_pack_index", [PY, "scripts/build_compression_public_evidence_pack_v0_index_v1.py"]))
        steps.append(_run("open_bench_dual_report", [PY, "scripts/build_compression_open_bench_dual_report_v1.py"]))

    steps.append(_run("readiness_gate", [PY, "scripts/check_compression_enterprise_summary_readiness_v1.py"]))
    steps.append(_run("industry_gap_report", [PY, "scripts/build_compression_b2b_industry_sku_gap_report_v1.py"]))

    failed = [s for s in steps if s.get("exit_code", 0) != 0]
    doc = {
        "schema": "compression_proof_sprint_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "research_only": True,
        "chain_ok": len(failed) == 0,
        "steps": steps,
        "artifacts": {
            "industry_bundle": "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json",
            "industry_gap": "reports/compression_b2b_industry_sku_gap_report_v1_latest.json",
            "composite_poc": "reports/customer_compression_stateless_poc_proof_sprint_composite_v1_latest.json",
            "open_bench_dual": "reports/compression_open_bench_dual_report_v1_latest.json",
            "evidence_index": "docs/final/artifacts/compression_public_evidence_pack_v0_index_latest.json",
            "readiness": "reports/compression_enterprise_summary_readiness_v1_latest.json",
        },
        "forbidden_as_headline": [
            "Do not use composite or SKU PoC as global SLA",
            "Track A ~47.5% remains internal regression only",
        ],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": doc["chain_ok"], "failed": [s["id"] for s in failed]}, ensure_ascii=False))
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
