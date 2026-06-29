#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Record commander human sign-off for KOSPI composite shadow (not production apply)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVOLUTION = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_commander_shadow_signoff_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_commander_shadow_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_signoff(*, message: str, scope: str) -> dict[str, Any]:
    cpcv = _read(ROOT / "reports/kospi_cpcv_shadow_promotion_poc_v1_latest.json")
    parallel = _read(ROOT / "reports/kospi_june2026_parallel_shadow_bundle_v1_latest.json")
    return {
        "schema": "kospi_commander_shadow_signoff_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "signed_by": "commander",
        "signoff_message_ko": message,
        "signoff_scope": scope,
        "approved_shadow_arm": "composite_bear_conditional",
        "production_apply_authorized": False,
        "track_a_live_authorized": False,
        "active_blend_weights_unchanged": True,
        "evidence": {
            "cpcv_pass": (cpcv.get("promotion_poc_gate") or {}).get("pass"),
            "cpcv_median_soft_delta": (cpcv.get("fold_summary") or {}).get("median_soft_delta"),
            "merged_soft_delta_pp": (cpcv.get("full_sample") or {}).get("soft_delta_pp"),
            "june_composite_soft_delta_pp": (parallel.get("leader_arm") or {}).get("soft_delta_pp"),
            "cpcv_artifact": "reports/kospi_cpcv_shadow_promotion_poc_v1_latest.json",
            "parallel_bundle_artifact": "reports/kospi_june2026_parallel_shadow_bundle_v1_latest.json",
        },
        "next_actions_ko": [
            "July evening composite shadow 누적 (2026-07)",
            "n>=15 시 promotion_readiness + Wilson 재판정",
            "production apply는 별도 승인 (--apply-approved) 전까지 금지",
        ],
        "reproduce": "py scripts/record_kospi_commander_shadow_signoff_v1.py",
    }


def patch_evolution(signoff: dict[str, Any]) -> None:
    rules = _read(EVOLUTION)
    pol = rules.get("composite_shadow_policy")
    if not isinstance(pol, dict):
        pol = {}
    pol["commander_signoff_v1"] = {
        "signed_at_utc": signoff["generated_at_utc"],
        "signed_by": "commander",
        "approved_arm": signoff["approved_shadow_arm"],
        "production_apply_authorized": False,
        "scope_ko": signoff["signoff_message_ko"],
    }
    rules["composite_shadow_policy"] = pol
    EVOLUTION.write_text(json.dumps(rules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--message",
        default="merged+CPCV shadow composite 모니터링 승인 — active weights·Track A 변경 없음",
    )
    ap.add_argument("--scope", default="shadow_monitoring_july_oos")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--patch-evolution", action="store_true", default=True)
    ns = ap.parse_args()

    doc = build_signoff(message=ns.message, scope=ns.scope)
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if ns.patch_evolution:
        patch_evolution(doc)
    print(json.dumps({"ok": True, "out": str(ns.output), "send_gate": "HOLD"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
