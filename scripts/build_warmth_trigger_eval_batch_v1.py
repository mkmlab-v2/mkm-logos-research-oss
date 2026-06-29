#!/usr/bin/env python3
"""Batch WTT eval over content dose catalog with synthetic pilot sessions ([HYPO])."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_warmth_trigger_eval_v1 import (  # noqa: E402
    build_eval_report,
    _load_json,
)

DEFAULT_PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
DEFAULT_CATALOG = ROOT / "docs/final/artifacts/warmth_content_dose_catalog_v1.json"
DEFAULT_OVERLAY = ROOT / "docs/final/artifacts/epb_sasang_overlay_rules_v1.json"
DEFAULT_OUT = ROOT / "reports/warmth_trigger_eval_batch_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def synthetic_session_from_dose(dose_item: dict[str, Any], index: int) -> dict[str, Any]:
    """Deterministic pilot stub — not human subject data."""
    d = dose_item["dose"]
    intensity = float(d["intensity_0_1"])
    warmth = float(d["warmth_0_1"])
    recovery = bool(d.get("recovery_arc_present", False))
    risks = set(d.get("risk_tags") or [])

    pre_valence = -0.12 - 0.18 * intensity
    pre_arousal = -0.22 + 0.08 * (index % 3)
    pre_surprisal = 0.45 + 0.4 * intensity

    if "trauma_heavy" in risks or (intensity > 0.72 and not recovery):
        post_valence = pre_valence - 0.28
        post_arousal = 0.58 + 0.05 * intensity
        post_surprisal = pre_surprisal + 0.05
        prior_overload = intensity > 0.75
    elif warmth >= 0.7 and recovery and intensity <= 0.55:
        post_valence = pre_valence + 0.28 + 0.15 * warmth
        post_arousal = -0.05 + 0.12 * intensity
        post_surprisal = pre_surprisal - 0.22
        prior_overload = False
    elif warmth < 0.5 or not recovery:
        post_valence = pre_valence + 0.06
        post_arousal = 0.08
        post_surprisal = pre_surprisal - 0.04
        prior_overload = False
    else:
        post_valence = pre_valence + 0.18
        post_arousal = 0.02
        post_surprisal = pre_surprisal - 0.15
        prior_overload = False

    return {
        "session_id": f"synthetic_{dose_item['content_id']}",
        "pre": {"valence": round(pre_valence, 4), "arousal": round(pre_arousal, 4)},
        "post": {"valence": round(post_valence, 4), "arousal": round(post_arousal, 4)},
        "pre_surprisal_0_1": round(pre_surprisal, 4),
        "post_surprisal_0_1": round(max(0.0, post_surprisal), 4),
        "prior_overload": prior_overload,
        "synthetic_pilot": True,
    }


def run_batch(
    *,
    profile: dict[str, Any],
    catalog: dict[str, Any],
    overlay: dict[str, Any] | None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    outcomes: Counter[str] = Counter()

    for i, dose_item in enumerate(catalog.get("items") or []):
        session = synthetic_session_from_dose(dose_item, i)
        report = build_eval_report(
            profile=profile,
            dose=dose_item,
            session=session,
            overlay=overlay,
        )
        outcomes[report["outcome"]] += 1
        rows.append(
            {
                "content_id": dose_item.get("content_id"),
                "medium": dose_item.get("medium"),
                "outcome": report["outcome"],
                "recommended_arm": report["recommended_arm"],
                "dose_warnings": report.get("dose_warnings") or [],
                "valence_delta": report.get("outcome_details", {}).get("valence_delta"),
            }
        )

    n = len(rows)
    hit = int(outcomes.get("hit", 0))
    over = int(outcomes.get("over", 0))

    return {
        "schema": "warmth_trigger_eval_batch_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "research_only": True,
        "hypothesis_class": "HYPO",
        "disclaimer_ko": (
            "합성 파일럿 세션 기반 배치 평가입니다. 인간 피험·임상 효능 주장이 아닙니다."
        ),
        "profile_version": profile.get("profile_version"),
        "catalog_schema": catalog.get("schema"),
        "item_count": n,
        "synthetic_pilot": True,
        "outcome_counts": dict(outcomes),
        "rates": {
            "hit_rate": round(hit / n, 6) if n else 0.0,
            "over_rate": round(over / n, 6) if n else 0.0,
            "under_rate": round(int(outcomes.get("under", 0)) / n, 6) if n else 0.0,
            "miss_rate": round(int(outcomes.get("miss", 0)) / n, 6) if n else 0.0,
            "hysteresis_cooldown_rate": round(
                int(outcomes.get("hysteresis_cooldown", 0)) / n, 6
            )
            if n
            else 0.0,
        },
        "rows": rows,
        "pilot_gate_note": "human_pilot_n30_not_met_synthetic_only",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--catalog-json", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--overlay-json", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--no-overlay", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    profile = _load_json(args.profile_json)
    catalog = _load_json(args.catalog_json)
    overlay = None if args.no_overlay else _load_json(args.overlay_json)

    report = run_batch(profile=profile, catalog=catalog, overlay=overlay)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "item_count": report["item_count"],
                "hit_rate": report["rates"]["hit_rate"],
                "out": str(args.out.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
