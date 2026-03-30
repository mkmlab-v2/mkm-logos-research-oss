#!/usr/bin/env python3
"""Two-phase symbol pipeline: explore (off) -> binding (on)."""

from __future__ import annotations

import json
import subprocess
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports" / "constitution" / "btrack_pilot"

BENCH = ROOT / "scripts" / "report_symbol_allowlist_ab_bench.py"


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run two-phase symbol pipeline with gate-ready exit code.")
    p.add_argument("--gate-threshold", type=float, default=0.85, help="Minimum binding resonance_rate_random")
    p.add_argument(
        "--strict-exit",
        action="store_true",
        help="Return non-zero when binding gate fails (CI mode).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=REPORTS / "symbol_two_phase_mode_run_latest.json",
        help="Output JSON report path",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    _run([sys.executable, str(BENCH)])

    ab = _read_json(REPORTS / "symbol_allowlist_ab_bench_latest.json")
    off = ab.get("variants", {}).get("allowlist_off", {}).get("metrics", {})
    on = ab.get("variants", {}).get("allowlist_on", {}).get("metrics", {})

    decision = {
        "select_binding_variant": "allowlist_on",
        "reason": "binding stage prioritizes high vector coverage and resonance gate pass",
        "gate": {
            "target_resonance_rate_gte": args.gate_threshold,
            "actual_resonance_rate_random": float(on.get("resonance_rate_random", 0.0)),
            "pass": float(on.get("resonance_rate_random", 0.0)) >= args.gate_threshold,
        },
    }

    out = {
        "schema": "symbol_two_phase_mode_run_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase_explore": {
            "variant": "allowlist_off",
            "metrics": off,
            "purpose": "maximize candidate diversity before strict binding",
        },
        "phase_binding": {
            "variant": "allowlist_on",
            "metrics": on,
            "purpose": "enforce vector-connectable symbols and resonance gate",
        },
        "decision": decision,
        "artifacts": {
            "ab_bench": str(REPORTS / "symbol_allowlist_ab_bench_latest.json"),
            "explore_alignment": str(REPORTS / "symbol_gematria_alignment_test_allowlist_off.json"),
            "binding_alignment": str(REPORTS / "symbol_gematria_alignment_test_allowlist_on.json"),
        },
    }

    out_path = args.output if args.output.is_absolute() else (ROOT / args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path}")
    if args.strict_exit and not bool(decision["gate"]["pass"]):
        print("GATE_FAIL: strict-exit enabled and binding gate did not pass")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
