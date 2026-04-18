#!/usr/bin/env python3
"""Same input (MULTILENS V2), same mode: bridge policy OFF vs ON — fair A/B pair.

Writes full reports plus a small summary artifact with reproduce commands.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_ultra_compression_default.py"
OUT_DIR = ROOT / "docs" / "final" / "artifacts"
OFF_PATH = OUT_DIR / "MULTILENS_BRIDGE_POLICY_AB_OFF_V1.json"
ON_PATH = OUT_DIR / "MULTILENS_BRIDGE_POLICY_AB_ON_V1.json"
SUMMARY_PATH = OUT_DIR / "MULTILENS_BRIDGE_POLICY_AB_V1.json"
BY_MODE_PATH = OUT_DIR / "MULTILENS_BRIDGE_POLICY_AB_BY_MODE_V1.json"


def _mode_slug(mode: str) -> str:
    return mode.replace("-", "_")


def _run(mode: str, bridge: bool, out: Path) -> None:
    cmd = [sys.executable, str(RUNNER), "--mode", mode, "--out", str(out)]
    if bridge:
        cmd.append("--apply-gematria-4d-bridge-policy")
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def _trim_metrics(cm: dict) -> dict:
    keys = (
        "case_count",
        "global_token_saving_rate",
        "avg_reconstruction_fidelity_jaccard",
        "avg_sensitive_integrity",
        "sensitive_violation_count",
    )
    return {k: cm[k] for k in keys if k in cm}


def _one_pair(mode: str, off_p: Path, on_p: Path) -> dict[str, Any]:
    _run(mode, False, off_p)
    _run(mode, True, on_p)
    off_doc = json.loads(off_p.read_text(encoding="utf-8"))
    on_doc = json.loads(on_p.read_text(encoding="utf-8"))
    off_cm = off_doc.get("compression_metrics") or {}
    on_cm = on_doc.get("compression_metrics") or {}
    return {
        "bridge_off": {
            "artifact": str(off_p.relative_to(ROOT)).replace("\\", "/"),
            "active_profile": off_doc.get("active_profile"),
            "compression_metrics_summary": _trim_metrics(off_cm),
        },
        "bridge_on": {
            "artifact": str(on_p.relative_to(ROOT)).replace("\\", "/"),
            "active_profile": on_doc.get("active_profile"),
            "compression_metrics_summary": _trim_metrics(on_cm),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Multilens bridge policy A/B (same V2 input).")
    ap.add_argument(
        "--mode",
        choices=("universal", "literal", "ultra-literal"),
        default="ultra-literal",
        help="Profile for both runs (default: ultra-literal — strongest bridge overhead signal).",
    )
    ap.add_argument(
        "--all-modes",
        action="store_true",
        help="Run OFF/ON for universal, literal, ultra-literal; write per-mode artifacts + BY_MODE summary.",
    )
    args = ap.parse_args()
    mode = str(args.mode)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.all_modes:
        modes = ("universal", "literal", "ultra-literal")
        modes_out: dict[str, Any] = {}
        for m in modes:
            slug = _mode_slug(m)
            off_p = OUT_DIR / f"MULTILENS_BRIDGE_POLICY_AB_OFF_{slug}_V1.json"
            on_p = OUT_DIR / f"MULTILENS_BRIDGE_POLICY_AB_ON_{slug}_V1.json"
            modes_out[slug] = _one_pair(m, off_p, on_p)

        combined = {
            "schema": "multilens_bridge_policy_ab_by_mode_v1",
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "input_unchanged": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
            "modes": modes_out,
            "reproduce_commands": {
                "all_modes": "py scripts/run_multilens_bridge_policy_ab.py --all-modes",
                "per_mode": (
                    "py scripts/run_multilens_bridge_policy_ab.py --mode <universal|literal|ultra-literal>"
                ),
            },
        }
        BY_MODE_PATH.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {BY_MODE_PATH}")
        return 0

    _run(mode, False, OFF_PATH)
    _run(mode, True, ON_PATH)

    off_doc = json.loads(OFF_PATH.read_text(encoding="utf-8"))
    on_doc = json.loads(ON_PATH.read_text(encoding="utf-8"))

    off_cm = off_doc.get("compression_metrics") or {}
    on_cm = on_doc.get("compression_metrics") or {}

    summary = {
        "schema": "multilens_bridge_policy_ab_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_unchanged": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        "mode": mode,
        "reproduce_commands": {
            "bridge_off": (
                f"py scripts/run_ultra_compression_default.py --mode {mode} "
                f"--out docs/final/artifacts/MULTILENS_BRIDGE_POLICY_AB_OFF_V1.json"
            ),
            "bridge_on": (
                f"py scripts/run_ultra_compression_default.py --mode {mode} "
                f"--apply-gematria-4d-bridge-policy "
                f"--out docs/final/artifacts/MULTILENS_BRIDGE_POLICY_AB_ON_V1.json"
            ),
            "full_ab_chain": "py scripts/run_multilens_bridge_policy_ab.py",
        },
        "bridge_off": {
            "artifact": "docs/final/artifacts/MULTILENS_BRIDGE_POLICY_AB_OFF_V1.json",
            "active_profile": off_doc.get("active_profile"),
            "compression_metrics_summary": _trim_metrics(off_cm),
        },
        "bridge_on": {
            "artifact": "docs/final/artifacts/MULTILENS_BRIDGE_POLICY_AB_ON_V1.json",
            "active_profile": on_doc.get("active_profile"),
            "compression_metrics_summary": _trim_metrics(on_cm),
        },
    }

    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # OFF/ON은 서브프로세스(run_ultra_compression_default)가 이미 WROTE 출력 — 여기서 중복 출력하지 않음
    print(f"WROTE: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
