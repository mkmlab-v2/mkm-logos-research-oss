#!/usr/bin/env python3
"""Run policy-stage transition drill for limited/strict/monitor behavior."""

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


def _sync_policy(
    *,
    tiering_json: Path,
    promoted_json: Path,
    regression_json: Path,
    sustain_json: Path,
    out_json: Path,
    strict_threshold: int,
) -> dict[str, Any]:
    _run_py(
        [
            "scripts/sync_external_anchor_tier1_into_operating_policy_v1.py",
            "--tiering-json",
            str(tiering_json),
            "--promoted-json",
            str(promoted_json),
            "--regression-json",
            str(regression_json),
            "--sustain-json",
            str(sustain_json),
            "--strict-pass-streak-threshold",
            str(strict_threshold),
            "--output-json",
            str(out_json),
        ]
    )
    return _read_json(out_json)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tiering-json", type=Path, default=ART / "external_bible_anchor_tiering_latest.json")
    ap.add_argument("--promoted-json", type=Path, default=ART / "external_bible_anchor_tier1_promoted_latest.json")
    ap.add_argument("--regression-json", type=Path, default=ART / "external_bible_anchor_post_promotion_regression_latest.json")
    ap.add_argument("--strict-pass-streak-threshold", type=int, default=6)
    ap.add_argument("--output-json", type=Path, default=ART / "external_bible_anchor_policy_stage_drill_latest.json")
    args = ap.parse_args()

    strict_threshold = max(1, int(args.strict_pass_streak_threshold))
    sustain_base = _read_json(ART / "external_bible_anchor_promotion_sustain_gate_latest.json")

    scenarios = [
        ("limited_expected", {"status": "MATURE", "current": {"pass_streak": strict_threshold - 1, "fail_streak": 0}}),
        ("strict_expected", {"status": "MATURE", "current": {"pass_streak": strict_threshold, "fail_streak": 0}}),
        ("monitor_expected", {"status": "DOWNGRADE_TRIGGER", "current": {"pass_streak": 0, "fail_streak": 2}}),
    ]

    results: list[dict[str, Any]] = []
    for name, patch in scenarios:
        sustain_sim = dict(sustain_base)
        sustain_sim["generated_at_utc"] = _iso_now()
        sustain_sim["status"] = patch["status"]
        sustain_sim["current"] = patch["current"]
        sustain_path = ART / f"external_bible_anchor_promotion_sustain_{name}_drill_latest.json"
        policy_path = ART / f"external_bible_anchor_operating_policy_{name}_drill_latest.json"
        _write_json(sustain_path, sustain_sim)

        policy = _sync_policy(
            tiering_json=args.tiering_json,
            promoted_json=args.promoted_json,
            regression_json=args.regression_json,
            sustain_json=sustain_path,
            out_json=policy_path,
            strict_threshold=strict_threshold,
        )
        results.append(
            {
                "scenario": name,
                "sustain_status": sustain_sim.get("status"),
                "sustain_pass_streak": (sustain_sim.get("current") or {}).get("pass_streak"),
                "effective_action": policy.get("effective_action"),
                "policy_stage": policy.get("policy_stage"),
                "sustain_override": policy.get("sustain_override"),
                "policy_json": str(policy_path).replace("\\", "/"),
            }
        )

    summary = {
        "schema": "external_bible_anchor_policy_stage_drill_v1",
        "generated_at_utc": _iso_now(),
        "strict_pass_streak_threshold": strict_threshold,
        "results": results,
    }
    _write_json(args.output_json, summary)
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "scenarios": len(results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
