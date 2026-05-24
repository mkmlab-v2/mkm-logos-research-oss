#!/usr/bin/env python3
"""Human-readable blockers for auto_promote_ready (research_only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATES = ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
DEFAULT_HIT = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_promotion_readiness_report_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def build_report(*, gates: dict[str, Any], hit: dict[str, Any]) -> dict[str, Any]:
    metrics = hit.get("metrics") if isinstance(hit.get("metrics"), dict) else {}
    inputs = gates.get("inputs") if isinstance(gates.get("inputs"), dict) else {}
    streak_req = int(inputs.get("strict_streak_required") or 5)
    streak = int(gates.get("strict_pass_streak") or 0)
    blockers: list[dict[str, Any]] = []

    if not gates.get("strict_passed"):
        blockers.append(
            {
                "code": "STRICT_GATES_FAILED",
                "detail_ko": "strict_passed=false — WF/공유 score 게이트 미통과",
            }
        )
    elif streak < streak_req:
        blockers.append(
            {
                "code": "STRICT_STREAK_INSUFFICIENT",
                "detail_ko": f"strict_pass_streak={streak} < required={streak_req}",
                "observed": {"strict_pass_streak": streak, "strict_streak_required": streak_req},
            }
        )

    if not gates.get("auto_promote_ready"):
        if not blockers:
            blockers.append({"code": "AUTO_PROMOTE_FALSE", "detail_ko": "원인 미분류 — gates JSON 재확인"})

    return {
        "schema": "prophecy_promotion_readiness_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "auto_promote_ready": bool(gates.get("auto_promote_ready")),
        "all_gates_passed": bool(gates.get("all_gates_passed")),
        "strict_passed": bool(gates.get("strict_passed")),
        "strict_pass_streak": streak,
        "strict_streak_required": streak_req,
        "promotion_recommendation": gates.get("promotion_recommendation"),
        "outcome_class": (gates.get("gate_taxonomy") or {}).get("outcome_class")
        if isinstance(gates.get("gate_taxonomy"), dict)
        else gates.get("outcome_class"),
        "headline_hit_rate": metrics.get("price_directional_hit_rate"),
        "n_evaluated": metrics.get("n_evaluated"),
        "scoring_mode": metrics.get("scoring_mode"),
        "blockers": blockers,
        "next_human_action_ko": (
            "휴먼 검토(manual_review_candidate) — strict streak 누적 대기 또는 승격 게이트 재실행"
            if gates.get("strict_passed") and streak < streak_req
            else "게이트 실패 항목 수정 후 eval_prophecy_promotion_gates_v1 재실행"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gates-json", type=Path, default=DEFAULT_GATES)
    ap.add_argument("--hit-rate-json", type=Path, default=DEFAULT_HIT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_report(gates=_load(args.gates_json), hit=_load(args.hit_rate_json))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"auto_promote_ready={doc['auto_promote_ready']} blockers={len(doc['blockers'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
