#!/usr/bin/env python3
"""10-minute open-bench onboard smoke — visitor reproduce + contributor validate only.

Uses existing SSOT commands. Does NOT run mirror push, a-codeai binding, or customer n50.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/compression_open_bench_onboard_smoke_v1_latest.json"
REQUIREMENTS = ROOT / "requirements-public-reproduce.txt"
COMPRESSION_EXAMPLE = ROOT / "data/compression/examples/compression_contributor_example_v1.jsonl"
PROPHECY_EXAMPLE = ROOT / "data/prophecy/examples/prophecy_contributor_example_v1.jsonl"
PY = sys.executable

NEXT_STEPS = [
    "Read CONTRIBUTING_OPEN_BENCH.md — contributor_provided lane only (SEND_GATE HOLD).",
    "Add masked JSONL under data/compression/contributions/ + manifest entry.",
    "Local: py scripts/validate_compression_contributor_jsonl_v1.py --jsonl <your.jsonl> --min-rows 10",
    "Optional bench: powershell -File scripts/Invoke-CompressionContributorBenchChain_v1.ps1 -ContributorJsonl <path>",
    "Open a PR (not commander mirror push). Issue templates: .github/ISSUE_TEMPLATE/compression_contributor.yml",
    "FAIL-COMP-004: never merge Track A 47.5% with contributor or customer lane metrics.",
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_step(step_id: str, cmd: list[str], *, cwd: Path = ROOT) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--pip-install", action="store_true", help="pip install -r requirements-public-reproduce.txt")
    ap.add_argument("--skip-evidence-chain", action="store_true")
    ap.add_argument("--skip-compression-validate", action="store_true")
    ap.add_argument("--skip-prophecy-validate", action="store_true")
    ap.add_argument("--compression-example-jsonl", type=Path, default=COMPRESSION_EXAMPLE)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if args.dry_run:
        report = {
            "schema": "compression_open_bench_onboard_smoke_v1",
            "generated_at_utc": _utc(),
            "dry_run": True,
            "ok": True,
            "send_gate": "HOLD",
            "boundary_ack": "No mirror push; no customer n50 in default visitor path.",
            "next_steps": NEXT_STEPS,
            "steps": [],
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True, "out": str(args.out_json)}, ensure_ascii=False))
        return 0

    if args.pip_install:
        if not REQUIREMENTS.is_file():
            print(f"requirements missing: {REQUIREMENTS}", file=sys.stderr)
            return 1
        steps.append(
            _run_step(
                "pip_install",
                [PY, "-m", "pip", "install", "-q", "-r", str(REQUIREMENTS)],
            )
        )
        if not steps[-1]["ok"]:
            return _write_and_exit(args.out_json, steps, ok=False)

    if not args.skip_evidence_chain:
        steps.append(
            _run_step(
                "evidence_lv1_chain",
                [PY, "scripts/run_compression_evidence_lv1_chain_v1.py", "--skip-handoff"],
            )
        )
        if not steps[-1]["ok"]:
            return _write_and_exit(args.out_json, steps, ok=False)

    if not args.skip_compression_validate:
        ex = args.compression_example_jsonl
        if not ex.is_file():
            steps.append(
                {
                    "id": "compression_validate",
                    "cmd": [],
                    "exit_code": 1,
                    "ok": False,
                    "stdout_tail": "",
                    "stderr_tail": f"missing example jsonl: {ex}",
                }
            )
            return _write_and_exit(args.out_json, steps, ok=False)
        steps.append(
            _run_step(
                "compression_validate",
                [
                    PY,
                    "scripts/validate_compression_contributor_jsonl_v1.py",
                    "--jsonl",
                    str(ex),
                    "--min-rows",
                    "10",
                ],
            )
        )
        if not steps[-1]["ok"]:
            return _write_and_exit(args.out_json, steps, ok=False)

    if not args.skip_prophecy_validate and PROPHECY_EXAMPLE.is_file():
        steps.append(
            _run_step(
                "prophecy_validate",
                [
                    PY,
                    "scripts/validate_prophecy_contributor_jsonl_v1.py",
                    "--jsonl",
                    str(PROPHECY_EXAMPLE),
                    "--min-rows",
                    "5",
                ],
            )
        )
        if not steps[-1]["ok"]:
            return _write_and_exit(args.out_json, steps, ok=False)

    return _write_and_exit(args.out_json, steps, ok=True)


def _write_and_exit(out_json: Path, steps: list[dict[str, Any]], *, ok: bool) -> int:
    report = {
        "schema": "compression_open_bench_onboard_smoke_v1",
        "generated_at_utc": _utc(),
        "dry_run": False,
        "ok": ok,
        "send_gate": "HOLD",
        "boundary_ack": "Visitor reproduce + contributor example validate only; no commander mirror push.",
        "next_steps": NEXT_STEPS,
        "steps": steps,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(out_json), "step_count": len(steps)}, ensure_ascii=False))
    if ok:
        print("\n--- Contribute next (PR, not mirror push) ---")
        for line in NEXT_STEPS:
            print(f"- {line}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
