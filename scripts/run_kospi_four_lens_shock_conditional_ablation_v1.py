#!/usr/bin/env python3
"""Shock-day-only vs always-on 4-lens fusion ablation [HYPO]."""
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

from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import (  # noqa: E402
    _fusion_adjusted_direction,
    _read,
)

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_SHOCK_POLICY = ROOT / "docs/final/artifacts/kospi_shock_conditional_attach_operator_policy_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_four_lens_shock_conditional_ablation_v1_latest.json"

SHOCK_RETURN_PCT = 5.0
PRIOR_SHOCK_PCT = -6.0


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_shock_day(row: dict[str, Any], *, shock_return_pct: float, prior_shock_pct: float) -> bool:
    ret = float(row.get("daily_return_pct") or 0.0)
    if abs(ret) >= shock_return_pct:
        return True
    if ret <= prior_shock_pct:
        return True
    if str(row.get("actual_direction")) == "bear" and ret <= -shock_return_pct:
        return True
    return False


def _soft_score(outcomes: list[str]) -> float:
    if not outcomes:
        return 0.0
    total = 0.0
    for o in outcomes:
        if o == "HIT":
            total += 1.0
        elif o == "NEUTRAL_DRAW":
            total += 0.5
    return round(total / len(outcomes), 4)


def _arm_metrics(
    eval_doc: dict[str, Any],
    fusion: dict[str, Any],
    *,
    mode: str,
    shock_return_pct: float,
    prior_shock_pct: float,
) -> dict[str, Any]:
    rows = eval_doc.get("rows") if isinstance(eval_doc.get("rows"), list) else []
    outcomes: list[str] = []
    shock_days = 0
    per_date: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        actual = row.get("actual_direction")
        if actual not in ("bull", "bear", "neutral"):
            continue
        pred_active = str(row.get("predicted_direction"))
        shock = _is_shock_day(row, shock_return_pct=shock_return_pct, prior_shock_pct=prior_shock_pct)
        if shock:
            shock_days += 1
        if mode == "active":
            pred = pred_active
        elif mode == "fusion_always":
            pred = _fusion_adjusted_direction(fusion, pred_active)
        elif mode == "fusion_shock_only":
            pred = _fusion_adjusted_direction(fusion, pred_active) if shock else pred_active
        else:
            pred = pred_active
        out = _outcome(pred, str(actual))
        outcomes.append(out)
        per_date.append(
            {
                "session_date": row.get("session_date"),
                "mode": mode,
                "shock_day": shock,
                "pred": pred,
                "actual": actual,
                "outcome": out,
            }
        )
    return {
        "mode": mode,
        "n_scored": len(outcomes),
        "shock_days": shock_days,
        "soft_hit_rate": _soft_score(outcomes),
        "per_date": per_date,
    }


def run_shock_ablation(
    eval_doc: dict[str, Any],
    fusion: dict[str, Any],
    *,
    shock_return_pct: float,
    prior_shock_pct: float,
) -> dict[str, Any]:
    arms = {
        aid: _arm_metrics(
            eval_doc,
            fusion,
            mode=aid,
            shock_return_pct=shock_return_pct,
            prior_shock_pct=prior_shock_pct,
        )
        for aid in ("active", "fusion_always", "fusion_shock_only")
    }
    active_soft = arms["active"]["soft_hit_rate"]
    shock_soft = arms["fusion_shock_only"]["soft_hit_rate"]
    always_soft = arms["fusion_always"]["soft_hit_rate"]
    delta_shock = round(shock_soft - active_soft, 4)
    delta_always = round(always_soft - active_soft, 4)
    promotion_candidate = delta_shock >= 0.03 and arms["fusion_shock_only"]["n_scored"] >= 10
    return {
        "schema": "kospi_four_lens_shock_conditional_ablation_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "shock_thresholds": {
            "abs_return_pct": shock_return_pct,
            "prior_kospi_pct": prior_shock_pct,
        },
        "arms": arms,
        "comparison": {
            "delta_shock_only_minus_active": delta_shock,
            "delta_always_minus_active": delta_always,
            "shock_only_beats_always": shock_soft > always_soft,
        },
        "promotion_candidate": promotion_candidate,
        "verdict_ko": (
            "shock-day-only fusion이 active 대비 +3%p — shock attach 연구 후보"
            if promotion_candidate
            else "shock-only fusion도 승격 미달 — 충돌 리포트·Field 앵커만 운영"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--shock-return-pct", type=float, default=SHOCK_RETURN_PCT)
    ap.add_argument("--prior-shock-pct", type=float, default=PRIOR_SHOCK_PCT)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    fusion = _read(args.fusion_json)
    if not ev or not fusion:
        print("Missing eval or fusion", file=sys.stderr)
        return 2
    doc = run_shock_ablation(
        ev,
        fusion,
        shock_return_pct=args.shock_return_pct,
        prior_shock_pct=args.prior_shock_pct,
    )
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "comparison": doc["comparison"],
                "promotion_candidate": doc["promotion_candidate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
