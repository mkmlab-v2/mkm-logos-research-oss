#!/usr/bin/env python3
"""[HYPO] Mission C shadow ops status for perception / passive digest (reports only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "reports/mission_c_srcdir_expanded_shadow_summary_v1_latest.json"
DEFAULT_GATES = ROOT / "reports/prophecy_promotion_gates_mission_c_shadow_v1_latest.json"
DEFAULT_STREAK = ROOT / "reports/prophecy_promotion_strict_streak_mission_c_shadow_v1.json"
DEFAULT_BRIEFING = ROOT / "reports/mission_c_srcdir_expanded_briefing_v1_latest.md"
DEFAULT_OUT = ROOT / "reports/mission_c_shadow_ops_status_v1_latest.json"
SCHEMA = "mission_c_shadow_ops_status_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def build_status(
    *,
    summary: dict[str, Any],
    gates: dict[str, Any] | None,
    streak_doc: dict[str, Any] | None,
    briefing_path: Path,
) -> dict[str, Any]:
    wf = summary.get("wf_aggregate") if isinstance(summary.get("wf_aggregate"), dict) else {}
    gates_block = summary.get("gates") if isinstance(summary.get("gates"), dict) else {}
    streak = int(gates_block.get("strict_pass_streak") or 0)
    required = int(gates_block.get("strict_streak_required") or 5)
    strict = bool(gates_block.get("strict_passed"))
    outcome = str(gates_block.get("outcome_class") or "unknown")
    auto_ready = bool(gates_block.get("auto_promote_ready"))

    posture = "observe"
    if auto_ready:
        posture = "human_review_candidate"
    elif strict and streak > 0:
        posture = "streak_accumulating"
    elif not strict:
        posture = "strict_fail"

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "boundary_ack": "Perception plane only; no Track A/live merge or operational score overwrite.",
        "recipe_id": summary.get("recipe_id") or "mission_c_srcdir_expanded_v1",
        "inputs": {
            "summary_json": _rel(DEFAULT_SUMMARY),
            "gates_json": _rel(DEFAULT_GATES) if gates else None,
            "streak_history_json": _rel(DEFAULT_STREAK) if streak_doc else None,
            "briefing_md": _rel(briefing_path) if briefing_path.is_file() else None,
        },
        "wf_aggregate": wf,
        "gates": {
            "strict_passed": strict,
            "outcome_class": outcome,
            "strict_pass_streak": streak,
            "strict_streak_required": required,
            "auto_promote_ready": auto_ready,
            "combined_all_passed": gates_block.get("combined_all_passed"),
            "promotion_recommendation": gates_block.get("promotion_recommendation"),
        },
        "operator_posture": posture,
        "telegram_digest_block": {
            "enabled": True,
            "label": "미션C 연습장",
            "one_liner": (
                f"평균 {float(wf.get('mean_test_accuracy') or 0) * 100:.1f}% · "
                f"기복 {float(wf.get('stdev_test_accuracy') or 0) * 100:.2f}% · "
                f"연속합격 {streak}/{required}"
            ),
            "do_not_auto_promote": True,
        },
        "reproducible_command": "py scripts/build_mission_c_shadow_ops_status_v1.py",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--gates-json", type=Path, default=DEFAULT_GATES)
    ap.add_argument("--streak-json", type=Path, default=DEFAULT_STREAK)
    ap.add_argument("--briefing-md", type=Path, default=DEFAULT_BRIEFING)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    summary = _load(args.summary_json)
    if not summary:
        print(f"missing summary: {args.summary_json}", file=__import__("sys").stderr)
        return 2

    doc = build_status(
        summary=summary,
        gates=_load(args.gates_json),
        streak_doc=_load(args.streak_json),
        briefing_path=args.briefing_md,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} posture={doc['operator_posture']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
