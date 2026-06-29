#!/usr/bin/env python3
"""PersonaDiary native shell parity smoke — copy contract + schema + optional iOS dir."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts/verify_personadiary_native_shell_hypo_v1.py"
COPY_CONTRACT = ROOT / "docs/final/artifacts/personadiary_non_prediction_copy_contract_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/personadiary_native_shell_parity_smoke_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-bootstrap", action="store_true")
    parser.add_argument("--check-ios", action="store_true")
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    steps: list[dict] = []
    ok = True

    if not COPY_CONTRACT.is_file():
        print(f"missing: {COPY_CONTRACT}", file=sys.stderr)
        ok = False
    else:
        steps.append({"step": "copy_contract", "ok": True})

    verify_cmd = [sys.executable, str(VERIFY), "--out-json", str(ROOT / "reports/personadiary_native_shell_hypo_readiness_latest.json")]
    if args.check_bootstrap:
        verify_cmd.append("--check-bootstrap")
    if args.check_ios:
        verify_cmd.append("--check-ios")
    proc = subprocess.run(verify_cmd, cwd=ROOT)
    steps.append({"step": "verify_native_shell", "exit_code": proc.returncode})
    if proc.returncode != 0:
        ok = False

    if not args.skip_pytest:
        pytest_proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_personadiary_consumer_copy_v1.py", "-q"],
            cwd=ROOT,
        )
        steps.append({"step": "pytest_consumer_copy", "exit_code": pytest_proc.returncode})
        if pytest_proc.returncode != 0:
            ok = False

    report = {
        "schema": "personadiary_native_shell_parity_smoke_v1",
        "research_only": True,
        "hypothesis_tier": "B",
        "steps": steps,
        "ok": ok,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    import json

    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
