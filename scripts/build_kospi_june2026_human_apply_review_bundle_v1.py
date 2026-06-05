#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Human apply-review bundle for June KOSPI weight candidate [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
READINESS_DEFAULT = ROOT / "reports/kospi_june2026_promotion_readiness_latest.json"
COMPARE_DEFAULT = ROOT / "reports/kospi_june2026_weight_candidate_compare_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_human_apply_review_bundle_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_bundle(*, readiness: dict[str, Any], compare: dict[str, Any]) -> dict[str, Any]:
    promo = compare.get("promotion_recommendation") if isinstance(compare.get("promotion_recommendation"), dict) else {}
    har = readiness.get("human_apply_review") if isinstance(readiness.get("human_apply_review"), dict) else {}
    already_applied = bool(
        readiness.get("candidate_already_applied")
        or promo.get("candidate_already_applied")
        or (compare.get("weight_apply_status") or {}).get("candidate_already_applied")
    )
    return {
        "schema": "kospi_june2026_human_apply_review_bundle_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "candidate_id": compare.get("candidate_id") or readiness.get("candidate_id"),
        "candidate_status": compare.get("candidate_status"),
        "policy_tier": readiness.get("policy_tier"),
        "gate_relaxation_active": readiness.get("gate_relaxation_active"),
        "forward_gate_via": compare.get("forward_gate_via"),
        "candidate_already_applied": already_applied,
        "weight_apply_status": compare.get("weight_apply_status") or readiness.get("weight_apply_status"),
        "auto_gates_pass_pending_human": readiness.get("auto_gates_pass_pending_human"),
        "ready_for_apply_review": False if already_applied else promo.get("ready_for_apply_review", False),
        "blockers": [] if already_applied else (promo.get("blockers") or readiness.get("blockers") or []),
        "gates": readiness.get("gates"),
        "apply_command": har.get("apply_command") or promo.get("apply_command"),
        "checklist_ko": har.get("checklist_ko") or [],
        "verdict_ko": readiness.get("verdict_ko"),
        "note_ko": (
            "가중치 적용 완료 — June lane 포워드 모니터링. Track A·실매매 자동 합선 없음."
            if already_applied
            else "인간 sign-off 전 apply 금지. June lane only."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=READINESS_DEFAULT)
    ap.add_argument("--compare-json", type=Path, default=COMPARE_DEFAULT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = build_bundle(readiness=_read_json(args.readiness_json), compare=_read_json(args.compare_json))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} ready={doc['ready_for_apply_review']} "
        f"auto_pending_human={doc['auto_gates_pass_pending_human']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
