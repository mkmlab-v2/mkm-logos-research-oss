#!/usr/bin/env python3
"""Score prophecy-only OOS with prefit-frozen vs legacy mixed policy [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_field_band_small_sample_guardrails_v1 import build_small_sample_guardrails  # noqa: E402
from scripts.run_kospi_field_band_prophecy_only_oos_v1 import run_prophecy_only_oos  # noqa: E402
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_prophecy_only_panel_eval_v1_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_prophecy_only_panel_calendar_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_PREFIT_POLICY = ROOT / "docs/final/artifacts/kospi_field_band_conformal_prefit_frozen_policy_v1_latest.json"
DEFAULT_LEGACY_POLICY = ROOT / "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_prefit_frozen_oos_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_prefit_frozen_oos_v1_latest.json"

MIN_DELTA_PP = 0.03


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stack_hold(doc: dict[str, Any]) -> dict[str, Any]:
    return ((doc.get("holdout_pooled") or {}).get("stack_union") or {})


def run_prefit_frozen_oos(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    field_tier2: dict[str, Any] | None,
    prefit_policy: dict[str, Any],
    legacy_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    prefit_oos = run_prophecy_only_oos(
        eval_doc,
        calendar,
        fusion,
        field_tier2=field_tier2,
        policy=prefit_policy,
    )
    legacy_oos = (
        run_prophecy_only_oos(
            eval_doc,
            calendar,
            fusion,
            field_tier2=field_tier2,
            policy=legacy_policy,
        )
        if legacy_policy
        else None
    )

    pre_hold = _stack_hold(prefit_oos)
    leg_hold = _stack_hold(legacy_oos) if legacy_oos else {}
    pre_delta = float(prefit_oos.get("delta_stack_minus_base_holdout") or 0.0)
    leg_delta = float((legacy_oos or {}).get("delta_stack_minus_base_holdout") or 0.0)
    delta_prefit_minus_legacy = round(pre_delta - leg_delta, 4) if legacy_oos else None

    honest_ready = (
        prefit_oos.get("prophecy_only_oos_ready") is True
        and pre_delta >= MIN_DELTA_PP
        and prefit_policy.get("frozen") is True
    )
    guardrails = build_small_sample_guardrails(prefit_oos)

    return {
        "schema": "kospi_field_band_prefit_frozen_oos_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "send_gate": "HOLD",
        "track_a_go": False,
        "protocol": "prefit_tune_science_core_pre_may_freeze_score_prophecy_only",
        "train_panel_pointer": prefit_policy.get("train_panel_pointer"),
        "prefit_policy_pointer": "docs/final/artifacts/kospi_field_band_conformal_prefit_frozen_policy_v1_latest.json",
        "legacy_policy_pointer": "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json",
        "prophecy_only_oos": {
            "prefit_frozen": {
                "holdout_pooled": prefit_oos.get("holdout_pooled"),
                "delta_stack_minus_base_holdout": pre_delta,
                "policy_params": {
                    "rwc": prefit_policy.get("rwc"),
                    "cptc": prefit_policy.get("cptc"),
                },
            },
            "legacy_mixed_tuned": (
                {
                    "holdout_pooled": legacy_oos.get("holdout_pooled"),
                    "delta_stack_minus_base_holdout": leg_delta,
                }
                if legacy_oos
                else None
            ),
        },
        "comparison": {
            "prefit_stack_holdout": pre_hold.get("band_hit_rate"),
            "legacy_stack_holdout": leg_hold.get("band_hit_rate"),
            "prefit_delta_pp": pre_delta,
            "legacy_delta_pp": leg_delta,
            "delta_prefit_minus_legacy_pp": delta_prefit_minus_legacy,
            "prefit_beats_legacy_on_holdout": (
                float(pre_hold.get("band_hit_rate") or 0) > float(leg_hold.get("band_hit_rate") or 0) + 1e-6
                if legacy_oos
                else None
            ),
        },
        "prefit_honest_oos_ready": honest_ready,
        "small_sample_guardrails": guardrails,
        "verdict_ko": (
            "사전튜닝→동결→prophecy-only OOS 통과"
            if honest_ready
            else "prefit frozen OOS 미달 또는 소표본 브레이크 유지"
        ),
        "reproduce": "py scripts/run_kospi_field_band_prefit_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--field-tier2-json", type=Path, default=DEFAULT_FIELD_TIER2)
    ap.add_argument("--prefit-policy-json", type=Path, default=DEFAULT_PREFIT_POLICY)
    ap.add_argument("--legacy-policy-json", type=Path, default=DEFAULT_LEGACY_POLICY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    cal = _read(args.calendar_json)
    fusion = _read(args.fusion_json)
    prefit = _read(args.prefit_policy_json)
    if not ev or not cal or not fusion or not prefit:
        print("Missing inputs or prefit policy", file=sys.stderr)
        return 2

    doc = run_prefit_frozen_oos(
        ev,
        cal,
        fusion,
        field_tier2=_read(args.field_tier2_json),
        prefit_policy=prefit,
        legacy_policy=_read(args.legacy_policy_json),
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "prefit_honest_oos_ready": doc["prefit_honest_oos_ready"],
                "comparison": doc["comparison"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
