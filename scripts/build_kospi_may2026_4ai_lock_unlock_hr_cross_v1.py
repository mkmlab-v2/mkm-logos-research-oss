#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""May 2026 KOSPI 4AI lock vs unlock vs v2-only HR cross-table [HYPO][research_only]."""

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

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import build_calendar  # noqa: E402
from scripts.build_kospi_june2026_neutral_research_bundle_v1 import four_ai_counterfactual  # noqa: E402
from scripts.eval_kospi_june2026_daily_prophecy_v1 import eval_calendar  # noqa: E402
EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
MAY_BACKTEST = ROOT / "reports/kospi_multilens_blend_backtest_may2026_research.json"
DEFAULT_OUT = ROOT / "reports/kospi_may2026_4ai_lock_unlock_hr_cross_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _metrics_from_backtest(doc: dict[str, Any], variant_id: str) -> dict[str, Any] | None:
    for row in doc.get("variants") or []:
        if row.get("variant_id") == variant_id:
            return row.get("metrics")
    return None


def build_cross(*, year_month: str, as_of_kst: str) -> dict[str, Any]:
    rules = _read_json(EVOLUTION_RULES)
    cal = build_calendar(year_month=year_month, skip_panel=True, profile="v2_multilens")
    eval_doc = eval_calendar(cal, as_of_kst=as_of_kst)
    cf = four_ai_counterfactual(cal, evolution_path=EVOLUTION_RULES, eval_doc=eval_doc)

    may_bt = _read_json(MAY_BACKTEST)
    backtest_rows = {
        "v2_lens3_heavy_no_4ai": _metrics_from_backtest(may_bt, "v2_lens3_heavy"),
        "v2_lens3_heavy_4ai_current": _metrics_from_backtest(may_bt, "v2_lens3_heavy_4ai_current"),
        "v2_lens3_heavy_4ai_legacy": _metrics_from_backtest(may_bt, "v2_lens3_heavy_4ai_legacy_hold"),
        "v2_session_heavy_4ai_legacy": _metrics_from_backtest(may_bt, "v2_session_heavy_4ai_legacy_hold"),
    }

    proxy = None
    try:
        from scripts.run_kospi_june2026_proxy_forward_eval_v1 import run_proxy_forward_eval  # noqa: WPS433

        proxy = run_proxy_forward_eval(
            rules=rules,
            proxy_year_month=year_month,
            candidate_id="v2_lens3_heavy",
            as_of_kst=as_of_kst,
        )
    except Exception as exc:  # pragma: no cover
        proxy = {"error": str(exc)}

    return {
        "schema": "kospi_may2026_4ai_lock_unlock_hr_cross_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "gpu_used": False,
        "year_month": year_month,
        "as_of_kst": as_of_kst,
        "published_v2_eval": {
            "n_scored": eval_doc.get("n_scored"),
            "metrics": eval_doc.get("metrics"),
        },
        "four_ai_counterfactual": cf,
        "may_backtest_soft_hr": backtest_rows,
        "proxy_forward_eval": proxy,
        "comparison_ko": {
            "v2_only_soft": (backtest_rows.get("v2_lens3_heavy_no_4ai") or {}).get("soft_hit_rate"),
            "v2_4ai_current_soft": (backtest_rows.get("v2_lens3_heavy_4ai_current") or {}).get("soft_hit_rate"),
            "delta_4ai_minus_v2_only_soft": round(
                float((backtest_rows.get("v2_lens3_heavy_4ai_current") or {}).get("soft_hit_rate") or 0)
                - float((backtest_rows.get("v2_lens3_heavy_no_4ai") or {}).get("soft_hit_rate") or 0),
                4,
            )
            if backtest_rows.get("v2_lens3_heavy_4ai_current") and backtest_rows.get("v2_lens3_heavy_no_4ai")
            else None,
            "unlock_would_change_v2_days": cf.get("n_unlocked_would_change_v2"),
        },
        "verdict_ko": "May 백테스트: 4AI lock(current)이 v2-only 대비 soft HR 개선 shadow — June unlock drift와 분리 검토. apply 금지.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-05")
    ap.add_argument("--as-of-kst", default="2026-05-30")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = build_cross(year_month=args.year_month, as_of_kst=args.as_of_kst)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cmp_ko = doc.get("comparison_ko") or {}
    print(
        f"WROTE: {args.output.resolve()} "
        f"n_scored={doc['published_v2_eval'].get('n_scored')} "
        f"delta_soft={cmp_ko.get('delta_4ai_minus_v2_only_soft')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
