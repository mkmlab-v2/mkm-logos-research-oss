#!/usr/bin/env python3
"""One-shot chain: Field snapshot + Logos resonance + overlay build + eval (+ optional sweep)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHAIN_OUT = ROOT / "reports/field_logos_overlay_prophecy_chain_v1_latest.json"

BUILD_FIELD = ROOT / "scripts/build_field_regime_observational_snapshot_v1.py"
BUILD_RESONANCE = ROOT / "scripts/build_logos_regime_resonance_shadow_signal_v1.py"
BUILD_OVERLAY = ROOT / "scripts/build_field_logos_overlay_prophecy_v1.py"
EVAL_OVERLAY = ROOT / "scripts/eval_field_logos_overlay_prophecy_v1.py"
SWEEP = ROOT / "scripts/run_field_logos_overlay_evolution_sweep_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    tail = (cp.stdout or cp.stderr or "").strip().splitlines()
    return cp.returncode, tail[-1] if tail else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-field-build", action="store_true")
    ap.add_argument("--skip-resonance-build", action="store_true")
    ap.add_argument("--run-evolution-sweep", action="store_true")
    ap.add_argument("--strict-eval", action="store_true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_CHAIN_OUT)
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    all_ok = True

    if not args.skip_field_build:
        rc, tail = _run([sys.executable, str(BUILD_FIELD)])
        steps["field_snapshot"] = {"exit_code": rc, "log_tail": tail}
        all_ok = all_ok and rc == 0
    else:
        steps["field_snapshot"] = {"skipped": True}

    if not args.skip_resonance_build:
        rc, tail = _run([sys.executable, str(BUILD_RESONANCE)])
        steps["logos_resonance"] = {"exit_code": rc, "log_tail": tail}
        all_ok = all_ok and rc == 0
    else:
        steps["logos_resonance"] = {"skipped": True}

    rc, tail = _run([sys.executable, str(BUILD_OVERLAY)])
    steps["overlay_build"] = {"exit_code": rc, "log_tail": tail}
    all_ok = all_ok and rc == 0

    eval_cmd = [sys.executable, str(EVAL_OVERLAY)]
    if args.strict_eval:
        eval_cmd.append("--strict")
    rc, tail = _run(eval_cmd)
    steps["overlay_eval"] = {"exit_code": rc, "log_tail": tail}
    all_ok = all_ok and rc == 0

    if args.run_evolution_sweep:
        rc, tail = _run([sys.executable, str(SWEEP)])
        steps["evolution_sweep"] = {"exit_code": rc, "log_tail": tail}
        all_ok = all_ok and rc == 0

    doc = {
        "schema": "field_logos_overlay_prophecy_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "non_gating": True,
        "ok": all_ok,
        "steps": steps,
        "artifacts": {
            "overlay": "docs/final/artifacts/field_logos_overlay_prophecy_v1_latest.json",
            "eval": "reports/field_logos_overlay_prophecy_eval_v1_latest.json",
            "evolution_sweep": "reports/field_logos_overlay_evolution_sweep_v1_latest.json",
        },
    }
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "chain": str(out)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
