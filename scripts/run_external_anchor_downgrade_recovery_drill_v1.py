#!/usr/bin/env python3
"""Run one-shot downgrade->recovery drill without touching live policy artifacts."""

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


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_py(args: list[str]) -> None:
    cp = subprocess.run([sys.executable, *args], cwd=str(ROOT), text=True, capture_output=True)
    if cp.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--sustain-json",
        type=Path,
        default=ART / "external_bible_anchor_promotion_sustain_gate_latest.json",
    )
    ap.add_argument(
        "--shadow-json",
        type=Path,
        default=ART / "external_bible_anchor_shadow_rehearsal_latest.json",
    )
    ap.add_argument(
        "--current-candidates-json",
        type=Path,
        default=ART / "external_bible_anchor_tier1_promotion_candidates_latest.json",
    )
    ap.add_argument(
        "--tiering-json",
        type=Path,
        default=ART / "external_bible_anchor_tiering_latest.json",
    )
    ap.add_argument(
        "--promoted-json",
        type=Path,
        default=ART / "external_bible_anchor_tier1_promoted_latest.json",
    )
    ap.add_argument(
        "--regression-json",
        type=Path,
        default=ART / "external_bible_anchor_post_promotion_regression_latest.json",
    )
    ap.add_argument(
        "--output-summary-json",
        type=Path,
        default=ART / "external_bible_anchor_downgrade_recovery_drill_latest.json",
    )
    args = ap.parse_args()

    simulated_sustain_path = ART / "external_bible_anchor_promotion_sustain_gate_drill_latest.json"
    recovery_out = ART / "external_bible_anchor_recovery_candidates_drill_latest.json"
    policy_out = ART / "external_bible_anchor_operating_policy_drill_latest.json"

    sustain_live = _read_json(args.sustain_json)
    sustain_drill = dict(sustain_live)
    sustain_drill["generated_at_utc"] = _iso_now()
    sustain_drill["status"] = "DOWNGRADE_TRIGGER"
    sustain_drill["current"] = {
        "history_rows": int(((sustain_live.get("current") or {}).get("history_rows")) or 0),
        "pass_streak": 0,
        "fail_streak": 2,
    }
    _write_json(simulated_sustain_path, sustain_drill)

    _run_py(
        [
            "scripts/build_external_anchor_recovery_candidates_v1.py",
            "--sustain-json",
            str(simulated_sustain_path),
            "--shadow-json",
            str(args.shadow_json),
            "--current-candidates-json",
            str(args.current_candidates_json),
            "--target-candidates",
            "3",
            "--output-json",
            str(recovery_out),
        ]
    )

    _run_py(
        [
            "scripts/sync_external_anchor_tier1_into_operating_policy_v1.py",
            "--tiering-json",
            str(args.tiering_json),
            "--promoted-json",
            str(args.promoted_json),
            "--regression-json",
            str(args.regression_json),
            "--sustain-json",
            str(simulated_sustain_path),
            "--output-json",
            str(policy_out),
        ]
    )

    recovery = _read_json(recovery_out)
    policy = _read_json(policy_out)
    summary = {
        "schema": "external_bible_anchor_downgrade_recovery_drill_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "simulated_sustain_json": str(simulated_sustain_path).replace("\\", "/"),
            "shadow_json": str(args.shadow_json).replace("\\", "/"),
            "current_candidates_json": str(args.current_candidates_json).replace("\\", "/"),
        },
        "results": {
            "recovery_status": recovery.get("status"),
            "recovery_candidate_count": len(recovery.get("recovery_candidates") or []),
            "policy_effective_action": policy.get("effective_action"),
            "policy_sustain_override": policy.get("sustain_override"),
        },
        "expectations": {
            "recovery_status_should_be": "RECOVERY_READY_FOR_REVIEW",
            "policy_effective_action_should_be": "monitor_only",
        },
        "pass": (
            str(recovery.get("status") or "") == "RECOVERY_READY_FOR_REVIEW"
            and str(policy.get("effective_action") or "") == "monitor_only"
        ),
    }
    _write_json(args.output_summary_json, summary)
    print(json.dumps({"ok": True, "pass": summary["pass"], "output_json": str(args.output_summary_json).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
