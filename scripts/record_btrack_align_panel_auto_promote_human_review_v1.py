#!/usr/bin/env python3
"""Record commander human review when align-panel B-track gates reach auto_promote_ready.

Research-only acknowledgment — does NOT enable live trading, Track A merge, or MS KPI updates.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_GATES = REPORTS / "prophecy_promotion_gates_align_panel_nbps2_v1.json"
FALLBACK_GATES = ART / "prophecy_promotion_gates_v1_latest.json"
DEFAULT_OUT = ART / "btrack_align_panel_auto_promote_human_review_v1_latest.json"
APPROVAL = ART / "btrack_align_panel_human_approval_v1_latest.json"
SIGNOFF = ART / "btrack_promotion_signoff_packet_v1_latest.json"
STREAK = REPORTS / "prophecy_promotion_strict_streak_align_panel_v1.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gates-json", type=Path, default=DEFAULT_GATES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument(
        "--decision",
        default="ACKNOWLEDGED_BTRACK_AUTO_PROMOTE_RESEARCH_ONLY",
        help="Human review decision label (research lane only).",
    )
    ap.add_argument(
        "--note-ko",
        default=(
            "auto_promote_ready=true·streak 5/5 확인 — B-track 연구 게이트 인정. "
            "live·Track A·MS KPI·FAIL-COMP-004 active report 자동 승격 없음."
        ),
    )
    args = ap.parse_args(argv)

    gates_path = args.gates_json if args.gates_json.is_file() else FALLBACK_GATES
    gates = _load(gates_path)
    if not gates.get("auto_promote_ready"):
        raise SystemExit(
            f"refusing review record: auto_promote_ready is not true in {gates_path}"
        )
    if not gates.get("strict_passed"):
        raise SystemExit(f"refusing review record: strict_passed is not true in {gates_path}")

    approval = _load(APPROVAL)
    signoff = _load(SIGNOFF) if SIGNOFF.is_file() else {}

    doc: dict[str, Any] = {
        "schema": "btrack_align_panel_auto_promote_human_review_v1",
        "reviewed_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "decision": args.decision,
        "reviewer": args.reviewer,
        "note_ko": args.note_ko,
        "gate_snapshot": {
            "combined_all_passed": gates.get("combined_all_passed"),
            "strict_passed": gates.get("strict_passed"),
            "strict_pass_streak": gates.get("strict_pass_streak"),
            "auto_promote_ready": gates.get("auto_promote_ready"),
            "outcome_class": gates.get("outcome_class"),
            "promotion_recommendation": gates.get("promotion_recommendation"),
        },
        "explicit_hold": {
            "live_trading_auto_enable": False,
            "track_a_auto_merge": False,
            "ms_headline_kpi_update": False,
            "fail_comp_004_active_report": False,
            "prophecy_live_ab_required_before_operational_promotion": True,
        },
        "evidence": {
            "gates": _rel(gates_path),
            "streak_history": _rel(STREAK) if STREAK.is_file() else None,
            "align_panel_approval": _rel(APPROVAL) if approval else None,
            "promotion_signoff_packet": _rel(SIGNOFF) if signoff else None,
        },
        "prior_operational_approval": {
            "decision": approval.get("decision"),
            "approved_at_utc": approval.get("approved_at_utc"),
            "neutral_bps": approval.get("neutral_bps"),
        },
        "signoff_track_status_prophecy": (
            (signoff.get("track_status") or {}).get("prophecy")
            if isinstance(signoff.get("track_status"), dict)
            else None
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {_rel(args.out)}")
    print(
        f"DONE decision={args.decision} streak={doc['gate_snapshot'].get('strict_pass_streak')} "
        f"live=OFF track_a=OFF"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
