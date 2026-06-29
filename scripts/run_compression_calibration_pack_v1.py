#!/usr/bin/env python3
"""Corpus Calibration Pack — overlay extract → hydrate compare → optional dollar ROI."""

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


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1200:],
        "stderr_tail": (proc.stderr or "")[-1200:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", default="prospect-rehearsal-01")
    ap.add_argument("--input-jsonl", type=Path, help="default: data/compression/stateless_poc_prospect_<tenant>_v1.jsonl")
    ap.add_argument("--max-cases", type=int, default=25)
    ap.add_argument("--skip-dollar-roi", action="store_true", help="NL default: rehearsal keeps ROI null")
    ap.add_argument(
        "--allow-illustrative-rehearsal",
        action="store_true",
        help="Fill illustrative dollar/KRW for pipeline smoke only",
    )
    ap.add_argument("--input-usd-per-1m", type=float, default=2.5)
    ap.add_argument("--output-usd-per-1m", type=float, default=10.0)
    ap.add_argument("--krw-per-usd", type=float, default=1350.0)
    args = ap.parse_args()

    corpus = args.input_jsonl or (
        ROOT / f"data/compression/stateless_poc_prospect_{args.tenant_id}_v1.jsonl"
    )
    corpus = (ROOT / corpus).resolve() if not corpus.is_absolute() else corpus.resolve()
    if not corpus.is_file():
        steps = [
            _run(
                "bootstrap_pilot_roi",
                [
                    PY,
                    "scripts/run_compression_pilot_roi_chain_v1.py",
                    "--tenant-id",
                    args.tenant_id,
                    "--max-cases",
                    str(args.max_cases),
                ],
            )
        ]
        corpus = ROOT / f"data/compression/stateless_poc_prospect_{args.tenant_id}_v1.jsonl"
    else:
        steps = []

    overlay_out = ROOT / f"docs/final/artifacts/tenant_{args.tenant_id}_must_keep_overlay_v1.json"
    steps.append(
        _run(
            "extract_must_keep_overlay",
            [
                PY,
                "scripts/extract_tenant_must_keep_from_corpus_v1.py",
                "--tenant-id",
                args.tenant_id,
                "--input-jsonl",
                corpus.relative_to(ROOT).as_posix(),
                "--out-json",
                overlay_out.relative_to(ROOT).as_posix(),
            ],
        )
    )

    hydrate_out = ROOT / f"reports/compression_pilot_hydrate_compare_{args.tenant_id}_v1_latest.json"
    steps.append(
        _run(
            "hydrate_compare",
            [
                PY,
                "scripts/run_compression_pilot_hydrate_compare_v1.py",
                "--tenant-id",
                args.tenant_id,
                "--input-jsonl",
                corpus.relative_to(ROOT).as_posix(),
                "--overlay-json",
                overlay_out.relative_to(ROOT).as_posix(),
                "--max-cases",
                str(args.max_cases),
                "--out-json",
                hydrate_out.relative_to(ROOT).as_posix(),
            ],
        )
    )

    poc_out = ROOT / f"reports/customer_compression_stateless_poc_{args.tenant_id}_v1_latest.json"
    if not poc_out.is_file():
        steps.append(
            _run(
                "prospect_poc",
                [
                    PY,
                    "scripts/run_customer_compression_stateless_poc_v1.py",
                    "--input-jsonl",
                    corpus.relative_to(ROOT).as_posix(),
                    "--max-cases",
                    str(args.max_cases),
                    "--out-json",
                    poc_out.relative_to(ROOT).as_posix(),
                    "--relax-pass-gate",
                ],
            )
        )

    if not args.skip_dollar_roi:
        dollar_cmd = [
            PY,
            "scripts/build_compression_pilot_dollar_roi_v1.py",
            "--tenant-id",
            args.tenant_id,
            "--poc-json",
            poc_out.relative_to(ROOT).as_posix(),
            "--intake-json",
            f"reports/compression_b2b_prospect_poc_corpus_{args.tenant_id}_v1.json",
            "--metering-appendix-json",
            f"docs/final/artifacts/compression_b2b_pilot_metering_appendix_{args.tenant_id}_latest.json",
            "--input-usd-per-1m",
            str(args.input_usd_per_1m),
            "--output-usd-per-1m",
            str(args.output_usd_per_1m),
            "--krw-per-usd",
            str(args.krw_per_usd),
        ]
        if args.allow_illustrative_rehearsal:
            dollar_cmd.append("--allow-illustrative-rehearsal")
        steps.append(_run("dollar_krw_roi", dollar_cmd))

    steps.append(
        _run("refresh_recommended_workflow", [PY, "scripts/build_compression_b2b_recommended_workflow_v1.py"])
    )

    failed = [s for s in steps if s.get("exit_code", 0) != 0]
    chain_doc = {
        "schema": "compression_calibration_pack_v1",
        "generated_at_utc": _utc(),
        "chain_ok": len(failed) == 0,
        "tenant_id": args.tenant_id,
        "corpus_path": corpus.relative_to(ROOT).as_posix() if corpus.is_file() else None,
        "overlay_path": overlay_out.relative_to(ROOT).as_posix(),
        "hydrate_compare_path": hydrate_out.relative_to(ROOT).as_posix(),
        "steps": steps,
        "labels": ["research_only", "corpus_calibration_pack"],
        "send_gate": "HOLD",
    }
    out_chain = ROOT / f"reports/compression_calibration_pack_{args.tenant_id}_v1_latest.json"
    out_chain.write_text(json.dumps(chain_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": chain_doc["chain_ok"], "failed": [s["id"] for s in failed]}, ensure_ascii=False))
    return 0 if chain_doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
