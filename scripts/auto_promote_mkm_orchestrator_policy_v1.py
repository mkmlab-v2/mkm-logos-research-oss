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
DEFAULT_POLICY = ART / "mkm_global_orchestrator_policy_v1.json"
DEFAULT_STREAK = ART / "mkm_orchestrator_go_streak_latest.json"
DEFAULT_OUT = ART / "mkm_orchestrator_auto_promotion_latest.json"
APPLY_SCRIPT = ROOT / "scripts" / "apply_mkm_global_orchestrator_policy_profile_v1.py"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_streak(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        doc = _read_json(path)
    except Exception:
        return 0
    return int(doc.get("go_streak", 0))


def _write_streak(path: Path, streak: int, transition: str) -> None:
    out = {
        "schema": "mkm_orchestrator_go_streak_v1",
        "generated_at_utc": _now(),
        "go_streak": int(streak),
        "last_transition": transition,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-promote policy profile after sustained GO stability.")
    ap.add_argument("--stability-json", type=Path, default=DEFAULT_STABILITY)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--streak-json", type=Path, default=DEFAULT_STREAK)
    ap.add_argument("--target-profile", default="prod_conditional_go")
    ap.add_argument("--min-go-streak", type=int, default=3)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stability_path = args.stability_json if args.stability_json.is_absolute() else ROOT / args.stability_json
    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    streak_path = args.streak_json if args.streak_json.is_absolute() else ROOT / args.streak_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    stability = _read_json(stability_path)
    transition = str(stability.get("transition") or "unknown")
    go_stable = bool(stability.get("go_stable", False))
    down_transition = bool(stability.get("down_transition_detected", False))

    prev_streak = _read_streak(streak_path)
    if down_transition:
        new_streak = 0
    elif go_stable:
        new_streak = prev_streak + 1
    else:
        new_streak = 0
    _write_streak(streak_path, new_streak, transition)

    promotion_applied = False
    action = "none"
    apply_exit_code = 0
    apply_stdout = ""
    apply_stderr = ""

    if go_stable and new_streak >= max(1, args.min_go_streak):
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
            promotion_applied = cp.returncode == 0
        else:
            promotion_applied = True

    out = {
        "schema": "mkm_orchestrator_auto_promotion_v1",
        "generated_at_utc": _now(),
        "transition": transition,
        "go_stable": go_stable,
        "down_transition_detected": down_transition,
        "previous_go_streak": prev_streak,
        "current_go_streak": new_streak,
        "min_go_streak": int(args.min_go_streak),
        "target_profile": args.target_profile,
        "action": action,
        "dry_run": bool(args.dry_run),
        "promotion_applied": promotion_applied,
        "apply_exit_code": apply_exit_code,
        "apply_stdout": apply_stdout,
        "apply_stderr": apply_stderr[:500],
        "refs": {
            "stability_json": str(stability_path),
            "streak_json": str(streak_path),
            "policy_json": str(policy_path),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "go_stable": go_stable,
                "current_go_streak": new_streak,
                "promotion_applied": promotion_applied,
                "out": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    if action == "apply_profile" and not promotion_applied:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
