#!/usr/bin/env python3
"""Phase 3 — Truth Gating API stub (media sign-off meta, B-track [HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_phase3_truth_gating_v1_latest.json"
OUT_PUBLIC_STUB = ART / "saving_the_news_public_event_ingest_stub_v1.json"

PHASE2_STATUS = ART / "saving_the_news_phase2_poc_status_v1_latest.json"
PHASE2_MATRIX = ART / "saving_the_news_phase2_matrix_view_v1_latest.json"
NEWS_RT_RESULT = ART / "saving_the_news_news_rt_bench_result_v1_latest.json"
PROPHECY_GATES = ART / "prophecy_promotion_gates_v1_latest.json"

ALLOWED_ACTIONS = frozenset({"HOLD", "WATCH", "REDUCE"})
INTEGRITY_MIN = 0.99


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _gate(gate_id: str, passed: bool, *, reason: str | None = None, observed: dict | None = None) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "passed": passed,
        "reason": reason,
        "observed": observed or {},
    }


def evaluate(
    *,
    phase2_status: dict[str, Any] | None,
    matrix: dict[str, Any] | None,
    news_rt: dict[str, Any] | None,
    integrity_min: float = INTEGRITY_MIN,
) -> dict[str, Any]:
    p2_exit = (phase2_status or {}).get("exit_criteria") or {}
    p2_ok = bool(p2_exit.get("promote_to_phase3"))
    action = str(((matrix or {}).get("final_action") or {}).get("action", "")).upper()
    action_ok = action in ALLOWED_ACTIONS
    conflict = bool(((matrix or {}).get("conflict_resolver") or {}).get("conflict"))
    integrity = float(((news_rt or {}).get("kpi") or {}).get("integrity_score") or 0.0)
    integrity_ok = (news_rt or {}).get("measurement_status") == "COMPLETE" and integrity >= integrity_min
    news_rt_rows = int((news_rt or {}).get("observation_row_count") or 0)
    cohort_ok = news_rt_rows >= 120

    gates = [
        _gate(
            "phase2_poc_complete",
            p2_ok,
            reason=None if p2_ok else "phase2 promote_to_phase3 false",
            observed={"promote_to_phase3": p2_exit.get("promote_to_phase3")},
        ),
        _gate(
            "matrix_final_action_allowed",
            action_ok,
            reason=None if action_ok else f"disallowed action {action!r}",
            observed={"final_action": action},
        ),
        _gate(
            "news_rt_offline_cohort_complete",
            cohort_ok and integrity_ok,
            reason=None if (cohort_ok and integrity_ok) else "NEWS-RT cohort or integrity gate failed",
            observed={
                "observation_row_count": news_rt_rows,
                "integrity_score": integrity,
                "measurement_status": (news_rt or {}).get("measurement_status"),
            },
        ),
        _gate(
            "conflict_policy",
            (not conflict) or action == "WATCH",
            reason=None if ((not conflict) or action == "WATCH") else "conflict requires WATCH action",
            observed={"conflict": conflict, "final_action": action},
        ),
        _gate(
            "human_signoff_recorded",
            False,
            reason="No human sign-off artifact — publish blocked by design",
            observed={},
        ),
        _gate(
            "cryptographic_shield_implemented",
            False,
            reason="95% trust mark / cryptographic shield not implemented",
            observed={},
        ),
    ]

    auto_gates_passed = all(g["passed"] for g in gates if g["gate_id"] not in {"human_signoff_recorded", "cryptographic_shield_implemented"})
    combined = auto_gates_passed and p2_ok and action_ok and integrity_ok and cohort_ok

    if combined and conflict:
        outcome_class = "opportunistic"
        recommendation = "streaming_watch_with_conflict_review"
    elif combined:
        outcome_class = "pass_candidate"
        recommendation = "conditional_signoff_candidate"
    elif p2_ok and action_ok:
        outcome_class = "neutral_bucket"
        recommendation = "defer_pending_integrity_or_signoff"
    else:
        outcome_class = "reject"
        recommendation = "hold_publish"

    return {
        "schema": "saving_the_news_phase3_truth_gating_v1",
        "phase": "Phase 3 — Truth Gating API (stub)",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "pattern_ref": "prophecy_promotion_gates_v1 (structure only; not prophecy domain)",
        "inputs": {
            "phase2_status": str(PHASE2_STATUS.relative_to(ROOT)).replace("\\", "/"),
            "phase2_matrix": str(PHASE2_MATRIX.relative_to(ROOT)).replace("\\", "/"),
            "news_rt_result": str(NEWS_RT_RESULT.relative_to(ROOT)).replace("\\", "/"),
            "prophecy_gates_pointer": str(PROPHECY_GATES.relative_to(ROOT)).replace("\\", "/"),
        },
        "gates": gates,
        "auto_gates_passed": auto_gates_passed,
        "combined_all_passed": combined,
        "outcome_class": outcome_class,
        "promotion_recommendation": recommendation,
        "gate_taxonomy": {
            "schema": "prophecy_gate_taxonomy_v1",
            "outcome_class": outcome_class,
            "note": "Taxonomy borrowed for B-track media stub; not clinical or market truth claims.",
        },
        "human_signoff_required": True,
        "publish_signoff": {
            "cms_publish_allowed": False,
            "streaming_watch_metadata_allowed": combined,
            "public_event_ingest_allowed": combined,
            "reason": "human_signoff_required; no cryptographic shield; research_only lane",
        },
        "explicit_not_implemented": [
            "95% trust mark",
            "Cryptographic Shield product",
            "Live breaking-news stream SLA",
            "Auto-publish without human",
        ],
        "headline_anchor": (matrix or {}).get("headline_anchor"),
    }


def build_public_event_stub(gating: dict[str, Any], matrix: dict[str, Any] | None) -> dict[str, Any]:
    anchor = gating.get("headline_anchor") or (matrix or {}).get("headline_anchor") or {}
    fa = (matrix or {}).get("final_action") or {}
    cr = (matrix or {}).get("conflict_resolver") or {}
    return {
        "timestamp": gating["generated_at_utc"],
        "schema_version": "public-event.v1",
        "event_id": f"saving-the-news-stub-{gating['generated_at_utc'][:10]}",
        "source": "saving_the_news_phase3_truth_gating_stub",
        "risk_level": "INFO",
        "public_signal_direction": str(fa.get("action", "HOLD")),
        "abstract_reason": (
            f"Media observability stub — {anchor.get('headline', '')[:120]} "
            f"(conflict={cr.get('conflict')}; not investment advice)"
        )[:500],
        "direction_abstract": "flat",
        "disclaimer_ref": "PUBLIC_FACING_v1.7_saving_the_news",
        "system_status": "online",
        "showroom_display_mode": "observation",
        "research_only": True,
        "publish_signoff": gating.get("publish_signoff"),
        "outcome_class": gating.get("outcome_class"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate Phase 3 truth gating stub")
    ap.add_argument("--fail-on-gate", action="store_true", help="Exit 1 if combined_all_passed is false")
    ap.add_argument("--write-public-stub", action="store_true", default=True)
    ap.add_argument("--no-write-public-stub", action="store_false", dest="write_public_stub")
    args = ap.parse_args()

    doc = evaluate(
        phase2_status=_read(PHASE2_STATUS),
        matrix=_read(PHASE2_MATRIX),
        news_rt=_read(NEWS_RT_RESULT),
    )
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_public_stub:
        stub = build_public_event_stub(doc, _read(PHASE2_MATRIX))
        OUT_PUBLIC_STUB.write_text(json.dumps(stub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"Wrote {OUT_JSON.name} combined={doc['combined_all_passed']} "
        f"outcome={doc['outcome_class']} publish_allowed={doc['publish_signoff']['cms_publish_allowed']}"
    )
    if args.fail_on_gate and not doc["combined_all_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
