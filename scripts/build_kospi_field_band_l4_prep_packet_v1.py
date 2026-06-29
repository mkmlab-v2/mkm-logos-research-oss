#!/usr/bin/env python3
"""L4 Track A discussion prep packet — post L3 ack, no auto-promotion [HYPO]."""
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

DEFAULT_ACK = ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_v1_latest.json"
DEFAULT_STACK = ROOT / "reports/kospi_field_band_stack_ensemble_v1_latest.json"
DEFAULT_NESTED = ROOT / "reports/kospi_field_band_nested_tune_revalidate_v1_latest.json"
DEFAULT_PROPHECY_OOS = ROOT / "reports/kospi_field_band_prophecy_only_oos_v1_latest.json"
DEFAULT_PREFIT_OOS = ROOT / "reports/kospi_field_band_prefit_frozen_oos_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/kospi_field_band_l4_prep_packet_v1_latest.json"
REPORT_OUT = ROOT / "reports/kospi_field_band_l4_prep_packet_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_l4_prep_packet(
    *,
    ack: dict[str, Any],
    stack: dict[str, Any] | None,
    nested: dict[str, Any] | None,
    prophecy_oos: dict[str, Any] | None = None,
    prefit_oos: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hold_stack = (
        ((stack or {}).get("summary") or {}).get("holdout_pooled") or {}
    ).get("stack") or {}
    june_nested = ((nested or {}).get("june_holdout_metrics") or {}).get("nested_tune") or {}
    po_hold = ((prophecy_oos or {}).get("holdout_pooled") or {}).get("stack_union") or {}
    po_ready = (prophecy_oos or {}).get("prophecy_only_oos_ready") is True

    required = [
        "ECC via py scripts/athena_run_v1.py on gated child if prod touch",
        "CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md new row + pytest",
        "raw vs repair_v2 dual report if repair layer involved",
        "Explicit commander L4 scope sign-off separate from L3",
    ]
    if not po_ready:
        required.insert(3, "Prophecy-only extended panel without science_core backfill")

    guardrails = build_small_sample_guardrails(prophecy_oos)
    pre_comp = (prefit_oos or {}).get("comparison") or {}
    pre_hold = (
        ((prefit_oos or {}).get("prophecy_only_oos") or {}).get("prefit_frozen") or {}
    ).get("holdout_pooled", {}).get("stack_union") or {}

    return {
        "schema": "kospi_field_band_l4_prep_packet_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "ladder_stage": "L4_track_a_discussion_prep",
        "l3_ack_reference": ack.get("ack_reference"),
        "l3_ack_utc": ack.get("ack_utc"),
        "promotion_ready": False,
        "track_a_go": False,
        "track_a_discussion_eligible": guardrails["track_a_discussion_eligible"],
        "small_sample_guardrails": guardrails,
        "summary_metrics": {
            "pooled_holdout_stack_union": hold_stack.get("band_hit_rate"),
            "pooled_delta_stack_minus_base": (stack or {}).get("summary", {}).get("delta_stack_minus_base_holdout"),
            "june_prophecy_nested_delta": june_nested.get("delta_stack_minus_base"),
            "nested_revalidation_pass": (nested or {}).get("revalidation_pass"),
            "prophecy_only_holdout_stack_union": po_hold.get("band_hit_rate"),
            "prophecy_only_delta_stack_minus_base": (prophecy_oos or {}).get(
                "delta_stack_minus_base_holdout"
            ),
            "prophecy_only_oos_ready": po_ready,
            "mixed_vs_prophecy_only_note": (
                "mixed panel includes science_core backfill; prophecy-only is primary OOS"
                if po_ready
                else None
            ),
            "prefit_frozen_stack_holdout": pre_hold.get("band_hit_rate"),
            "prefit_frozen_delta_pp": pre_comp.get("prefit_delta_pp"),
            "prefit_honest_oos_ready": (prefit_oos or {}).get("prefit_honest_oos_ready"),
            "prefit_vs_legacy_delta_pp": pre_comp.get("delta_prefit_minus_legacy_pp"),
            "extended_prophecy_n_scored": (prophecy_oos or {}).get("n_scored_total"),
            "primary_may_june_stack_holdout": (
                (prophecy_oos or {}).get("primary_may_june_holdout") or {}
            ).get("stack_union", {}).get("band_hit_rate"),
            "primary_may_june_delta_pp": (
                (prophecy_oos or {}).get("primary_may_june_holdout") or {}
            ).get("delta_stack_minus_base"),
        },
        "required_before_track_a_discussion": required,
        "forbidden_until_l4_signed": [
            "start_live_trading.py patch",
            "VPS auto-apply",
            "send_gate OPEN",
            "direction fusion promotion",
            "Track A compression KPI merge",
        ],
        "recommended_next_research": [
            "May-only train / June-only holdout frozen policy re-run monthly",
            "Premium report band section refresh on new prophecy days",
            "FinStressTS diagnostic on new shock windows",
        ],
        "reproduce": "py scripts/build_kospi_field_band_l4_prep_packet_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ack-json", type=Path, default=DEFAULT_ACK)
    ap.add_argument("--stack-json", type=Path, default=DEFAULT_STACK)
    ap.add_argument("--nested-json", type=Path, default=DEFAULT_NESTED)
    ap.add_argument("--prophecy-oos-json", type=Path, default=DEFAULT_PROPHECY_OOS)
    ap.add_argument("--prefit-oos-json", type=Path, default=DEFAULT_PREFIT_OOS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ack = _read(args.ack_json)
    if not ack or not ack.get("acknowledged"):
        print("L3 ack artifact missing or not acknowledged", file=sys.stderr)
        return 2

    doc = build_l4_prep_packet(
        ack=ack,
        stack=_read(args.stack_json),
        nested=_read(args.nested_json),
        prophecy_oos=_read(args.prophecy_oos_json),
        prefit_oos=_read(args.prefit_oos_json),
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "ladder_stage": doc["ladder_stage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
