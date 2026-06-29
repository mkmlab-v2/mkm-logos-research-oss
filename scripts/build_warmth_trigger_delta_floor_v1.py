#!/usr/bin/env python3
"""Δ_floor stub — safety_base vs persona_custom from batch eval ([HYPO])."""
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

from scripts.build_warmth_trigger_eval_batch_v1 import (  # noqa: E402
    _load_json,
    run_batch,
)

DEFAULT_PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
DEFAULT_CATALOG = ROOT / "docs/final/artifacts/warmth_content_dose_catalog_v1.json"
DEFAULT_OVERLAY = ROOT / "docs/final/artifacts/epb_sasang_overlay_rules_v1.json"
DEFAULT_OUT = ROOT / "reports/warmth_trigger_delta_floor_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safety_score_from_batch(batch: dict[str, Any]) -> float:
    """Stub: higher is safer — penalize over + hysteresis_cooldown, reward hit."""
    rates = batch.get("rates") or {}
    hit = float(rates.get("hit_rate", 0))
    over = float(rates.get("over_rate", 0))
    hyst = float(rates.get("hysteresis_cooldown_rate", 0))
    return round(hit - over - 0.5 * hyst, 6)


def build_delta_floor_report(
    *,
    base_batch: dict[str, Any],
    custom_batch: dict[str, Any],
    control_limit: float = 0.12,
) -> dict[str, Any]:
    safety_base = _safety_score_from_batch(base_batch)
    safety_custom = _safety_score_from_batch(custom_batch)
    delta = round(safety_base - safety_custom, 6)
    breach = delta > control_limit
    return {
        "schema": "warmth_trigger_delta_floor_v1",
        "version": "1.0.0",
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "generated_at_utc": _utc_now(),
        "formula_stub": "Safety = hit_rate - over_rate - 0.5*hysteresis_cooldown_rate",
        "delta_floor": delta,
        "safety_base": safety_base,
        "safety_persona_custom": safety_custom,
        "control_limit": control_limit,
        "floor_breach": breach,
        "recommended_action": "overlay_base_prompt_layer" if breach else "release_ok_stub",
        "base_profile_version": base_batch.get("profile_version"),
        "custom_profile_version": custom_batch.get("profile_version"),
        "item_count": base_batch.get("item_count"),
        "disclaimer_ko": "Δ_floor 스텁. 임상 안전·프로덕션 릴리즈 게이트 아님.",
        "metaphor_notices": [
            "safety_proxy_not_clinical_efficacy",
            "overlay_rules_compare_only_not_live_tenant",
        ],
        "provenance": {"source": "build_warmth_trigger_delta_floor_v1"},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--catalog-json", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--overlay-json", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--control-limit", type=float, default=0.12)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    profile = _load_json(args.profile_json)
    catalog = _load_json(args.catalog_json)
    overlay = _load_json(args.overlay_json)

    base_batch = run_batch(profile=profile, catalog=catalog, overlay=None)
    custom_batch = run_batch(profile=profile, catalog=catalog, overlay=overlay)

    report = build_delta_floor_report(
        base_batch=base_batch,
        custom_batch=custom_batch,
        control_limit=args.control_limit,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "delta_floor": report["delta_floor"],
                "floor_breach": report["floor_breach"],
                "out": str(args.out.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
