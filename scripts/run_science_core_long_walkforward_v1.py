#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core long-window walk-forward A/B [HYPO][research_only].

Compares calendar-stub humanist vs full per-date inputs across multiple date profiles
(holdout shock window + extended pre-shock history).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
)
from scripts.btrack_logos_per_date_core_v1 import DEFAULT_LOGOS_PER_DATE_JSONL  # noqa: E402
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _ensure_science_jsonl,
)
from scripts.run_science_core_walkforward_v1 import run_walkforward  # noqa: E402
import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402

DEFAULT_MARKET_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/science_core_long_walkforward_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_long_walkforward_v1_latest.json"

PROFILES: tuple[dict[str, Any], ...] = (
    {
        "profile_id": "holdout_shock_2026",
        "date_from": "2026-01-01",
        "date_to": "2026-06-08",
        "train_days": 40,
        "test_days": 15,
        "step_days": 12,
    },
    {
        "profile_id": "extended_pre_shock_24m",
        "date_from": "2024-06-01",
        "date_to": "2026-04-30",
        "train_days": 60,
        "test_days": 20,
        "step_days": 20,
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_build(script: str, args: list[str]) -> int:
    return subprocess.call([sys.executable, str(ROOT / script), *args], cwd=str(ROOT))


def _summarize_wf(doc: dict[str, Any], label: str) -> dict[str, Any]:
    s = doc.get("summary") or {}
    return {
        "label": label,
        "n_folds": s.get("n_folds"),
        "selection_top1_hit_rate": s.get("selection_top1_hit_rate"),
        "mean_test_uplift_vs_science_alone": s.get("mean_test_uplift_vs_science_alone"),
        "recommended_prefilter_combos_top2": s.get("recommended_prefilter_combos_top2"),
        "eval_window": doc.get("eval_window"),
    }


def run_long_walkforward(
    *,
    profiles: tuple[dict[str, Any], ...],
    neutral_bps: float,
    rebuild_per_date: bool,
    rebuild_science: bool,
) -> dict[str, Any]:
    date_from = min(str(p["date_from"]) for p in profiles)
    date_to = max(str(p["date_to"]) for p in profiles)

    if rebuild_per_date:
        steps = [
            (
                "build_market_sasang",
                _run_build(
                    "scripts/build_btrack_market_sasang_per_date_jsonl_v1.py",
                    ["--date-from", date_from, "--date-to", date_to, "--refresh-market-psych-csv"],
                ),
            ),
            (
                "build_myeongni_per_date",
                _run_build(
                    "scripts/build_btrack_myeongni_per_date_jsonl_v1.py",
                    ["--date-from", date_from, "--date-to", date_to],
                ),
            ),
            (
                "build_logos_per_date",
                _run_build(
                    "scripts/build_btrack_logos_per_date_jsonl_v1.py",
                    ["--date-from", date_from, "--date-to", date_to],
                ),
            ),
        ]
        for name, rc in steps:
            if rc != 0:
                raise RuntimeError(f"{name} exit {rc}")

    if rebuild_science or not DEFAULT_SCIENCE_JSONL_KOSPI.is_file():
        _ensure_science_jsonl(
            instrument="kospi",
            csv_path=v1.KOSPI_CSV,
            out_path=DEFAULT_SCIENCE_JSONL_KOSPI,
            date_from=date_from,
            date_to=date_to,
            apply_overnight=True,
        )

    profile_results: list[dict[str, Any]] = []
    for prof in profiles:
        pid = str(prof["profile_id"])
        common_stub = dict(
            kospi_csv=v1.KOSPI_CSV,
            science_jsonl=DEFAULT_SCIENCE_JSONL_KOSPI,
            train_days=int(prof["train_days"]),
            test_days=int(prof["test_days"]),
            step_days=int(prof["step_days"]),
            max_window_days=None,
            date_from=str(prof["date_from"]),
            date_to=str(prof["date_to"]),
            neutral_bps=neutral_bps,
            myeongni_momentum_window=5,
        )
        stub_doc = run_walkforward(
            **common_stub,
            myeongni_jsonl=DEFAULT_MYEONGNI_JSONL,
            sasang_jsonl=DEFAULT_SASANG_JSONL,
            logos_lens=DEFAULT_LOGOS_LENS,
            logos_jsonl=None,
        )
        full_doc = run_walkforward(
            **common_stub,
            myeongni_jsonl=DEFAULT_MYEONGNI_PER_DATE,
            sasang_jsonl=DEFAULT_MARKET_SASANG,
            logos_lens=DEFAULT_LOGOS_LENS,
            logos_jsonl=DEFAULT_LOGOS_PER_DATE_JSONL,
        )
        stub_s = _summarize_wf(stub_doc, "calendar_stub_humanist")
        full_s = _summarize_wf(full_doc, "full_per_date_humanist_logos")
        s_u = stub_s.get("mean_test_uplift_vs_science_alone")
        f_u = full_s.get("mean_test_uplift_vs_science_alone")
        delta_u = round(float(f_u) - float(s_u), 4) if f_u is not None and s_u is not None else None
        s_t = stub_s.get("selection_top1_hit_rate")
        f_t = full_s.get("selection_top1_hit_rate")
        delta_t = round(float(f_t) - float(s_t), 4) if f_t is not None and s_t is not None else None
        profile_results.append(
            {
                "profile_id": pid,
                "config": prof,
                "arms": {"calendar_stub": stub_s, "full_per_date": full_s},
                "delta_full_minus_stub": {
                    "mean_test_uplift_vs_science_alone": delta_u,
                    "selection_top1_hit_rate": delta_t,
                },
            }
        )

    return {
        "schema": "science_core_long_walkforward_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating_logos": True,
        "aggregate_window": {"from": date_from, "to": date_to},
        "profiles": profile_results,
        "interpretation_ko": (
            "장기 walk-forward는 holdout 밖 안정성 관측용. composite attach·Track A 승격 근거 아님."
        ),
        "promotion_gate": {
            "track_a_ready": False,
            "live_trading_ready": False,
            "research_lane_status": "observe_only",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--rebuild-per-date", action="store_true")
    ap.add_argument("--rebuild-science", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    doc = run_long_walkforward(
        profiles=PROFILES,
        neutral_bps=args.neutral_bps,
        rebuild_per_date=args.rebuild_per_date,
        rebuild_science=args.rebuild_science,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    p0 = (doc.get("profiles") or [{}])[0]
    d = (p0.get("delta_full_minus_stub") or {})
    print(f"WROTE: {args.output.resolve()} profile0_uplift_delta={d.get('mean_test_uplift_vs_science_alone')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
