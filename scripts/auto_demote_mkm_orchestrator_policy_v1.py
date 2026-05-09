#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_STABILITY = ART / "mkm_global_orchestrator_go_stability_latest.json"
DEFAULT_OUT = ART / "mkm_orchestrator_auto_demotion_latest.json"
DEFAULT_POLICY = ART / "mkm_global_orchestrator_policy_v1.json"
APPLY_SCRIPT = ROOT / "scripts" / "apply_mkm_global_orchestrator_policy_profile_v1.py"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-demote orchestrator policy profile on GO down-transition.")
    ap.add_argument("--stability-json", type=Path, default=DEFAULT_STABILITY)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--target-profile", default="research")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stability_path = args.stability_json if args.stability_json.is_absolute() else ROOT / args.stability_json
    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    stability = _read_json(stability_path)
    down_transition = bool(stability.get("down_transition_detected", False))
    transition = str(stability.get("transition") or "unknown")

    demotion_applied = False
    apply_exit_code = 0
    apply_stdout = ""
    apply_stderr = ""
    action = "none"
    if down_transition:
        action = "apply_profile"
        if not args.dry_run:
            cp = subprocess.run(
                [
                    sys.executable,
                    str(APPLY_SCRIPT),
                    "--profile",
                    args.target_profile,
                    "--policy-json",
                    str(policy_path),
                    "--output-json",
                    str(policy_path),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            apply_exit_code = cp.returncode
            apply_stdout = (cp.stdout or "").strip()
            apply_stderr = (cp.stderr or "").strip()
            demotion_applied = cp.returncode == 0
        else:
            demotion_applied = True

    out = {
        "schema": "mkm_orchestrator_auto_demotion_v1",
        "generated_at_utc": _now(),
        "transition": transition,
        "down_transition_detected": down_transition,
        "target_profile": args.target_profile,
        "action": action,
        "dry_run": bool(args.dry_run),
        "demotion_applied": demotion_applied,
        "apply_exit_code": apply_exit_code,
        "apply_stdout": apply_stdout,
        "apply_stderr": apply_stderr[:500],
        "refs": {
            "stability_json": str(stability_path),
            "policy_json": str(policy_path),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "down_transition_detected": down_transition,
                "demotion_applied": demotion_applied,
                "out": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    if down_transition and not demotion_applied:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
