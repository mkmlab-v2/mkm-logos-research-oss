#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare science_plus_logos holdout: global snapshot vs per-date macro gate [HYPO][NON_GATING]."""
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

from scripts.btrack_logos_per_date_core_v1 import DEFAULT_LOGOS_PER_DATE_JSONL  # noqa: E402
from scripts.btrack_multilens_per_date_core_v1 import DEFAULT_LOGOS_LENS  # noqa: E402

DEFAULT_MARKET_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"
from scripts.run_science_core_holdout_combo_v1 import run_holdout_bundle  # noqa: E402

DEFAULT_MARKET_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/science_core_logos_source_ab_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_logos_source_ab_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _logos_combo_summary(doc: dict[str, Any], label: str) -> dict[str, Any]:
    k_holdout = (doc.get("kospi") or {}).get("horizon_holdout") or {}
    matrix = k_holdout.get("rate_matrix") or {}
    logos_soft = ((matrix.get("science_plus_logos") or {}).get("macro_21d") or {}).get("soft_hit_rate")
    if logos_soft is None:
        logos_soft = ((matrix.get("science_plus_logos") or {}).get("short_1d") or {}).get("soft_hit_rate")
    science_soft = ((matrix.get("science_core") or {}).get("short_1d") or {}).get("soft_hit_rate")
    attach = (doc.get("kospi") or {}).get("attach_recommendation") or {}
    return {
        "label": label,
        "science_plus_logos_macro_21d_soft": logos_soft,
        "science_core_short_1d_soft": science_soft,
        "holdout_best_combo": (attach.get("holdout_best_combo") or {}).get("best_lens_id"),
        "holdout_uplift_soft": (attach.get("holdout_best_combo") or {}).get("uplift_vs_science_alone"),
        "n_eval_dates": k_holdout.get("n_eval_dates"),
    }


def run_ab(
    *,
    train_from: str,
    train_to: str,
    holdout_from: str,
    holdout_to: str,
    neutral_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_per_date_jsonl: Path,
) -> dict[str, Any]:
    common = dict(
        train_from=train_from,
        train_to=train_to,
        holdout_from=holdout_from,
        holdout_to=holdout_to,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=DEFAULT_LOGOS_LENS,
        rebuild_science=False,
    )
    global_doc = run_holdout_bundle(**common, logos_jsonl=None)
    per_date_doc = run_holdout_bundle(**common, logos_jsonl=logos_per_date_jsonl)

    global_sum = _logos_combo_summary(global_doc, "logos_global_snapshot")
    per_date_sum = _logos_combo_summary(per_date_doc, "logos_per_date_macro_gate")

    g_u = global_sum.get("holdout_uplift_soft")
    p_u = per_date_sum.get("holdout_uplift_soft")
    delta = round(float(p_u) - float(g_u), 4) if p_u is not None and g_u is not None else None

    g_logos = global_sum.get("science_plus_logos_macro_21d_soft")
    p_logos = per_date_sum.get("science_plus_logos_macro_21d_soft")
    delta_logos_combo = (
        round(float(p_logos) - float(g_logos), 4) if p_logos is not None and g_logos is not None else None
    )

    return {
        "schema": "science_core_logos_source_ab_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "windows": {
            "train": {"from": train_from, "to": train_to},
            "holdout": {"from": holdout_from, "to": holdout_to},
        },
        "humanist_paths": {
            "myeongni_jsonl": str(myeongni_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "sasang_jsonl": str(sasang_jsonl.relative_to(ROOT)).replace("\\", "/"),
        },
        "logos_per_date_jsonl": str(logos_per_date_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "arms": {
            "logos_global_snapshot": global_sum,
            "logos_per_date_macro_gate": per_date_sum,
        },
        "delta_per_date_minus_global": {
            "holdout_uplift_soft": delta,
            "science_plus_logos_macro_21d_soft": delta_logos_combo,
        },
        "interpretation_ko": (
            "성경(Logos) per-date macro gate는 [NON_GATING] advisory blend 전용. "
            "science_core 정량 스코어 구성에는 미포함. Track A·실매매 승격 없음."
        ),
        "promotion_gate": {
            "track_a_ready": False,
            "live_trading_ready": False,
            "research_lane_status": "observe_only",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-from", default="2026-01-01")
    ap.add_argument("--train-to", default="2026-04-30")
    ap.add_argument("--holdout-from", default="2026-05-01")
    ap.add_argument("--holdout-to", default="2026-06-08")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_PER_DATE)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_MARKET_SASANG)
    ap.add_argument("--logos-per-date-jsonl", type=Path, default=DEFAULT_LOGOS_PER_DATE_JSONL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    doc = run_ab(
        train_from=args.train_from,
        train_to=args.train_to,
        holdout_from=args.holdout_from,
        holdout_to=args.holdout_to,
        neutral_bps=args.neutral_bps,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        logos_per_date_jsonl=args.logos_per_date_jsonl,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    d = doc.get("delta_per_date_minus_global") or {}
    print(f"WROTE: {args.output.resolve()} logos_combo_delta={d.get('science_plus_logos_macro_21d_soft')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
