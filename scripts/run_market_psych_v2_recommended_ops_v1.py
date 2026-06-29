#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B-track recommended market rail: v2 psych CSV -> per-date (dna=0, market=1) -> lens -> price 30/252."""

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

from scripts.run_market_psych_v1_vs_v2_price_ablation_v1 import (  # noqa: E402
    BTC_CSV,
    _eval_lane,
    _run,
)

DEFAULT_OUT = ROOT / "reports/market_psych_v2_recommended_ops_v1_latest.json"
ARTIFACT_OUT = ROOT / "docs/final/artifacts/market_psych_v2_recommended_ops_v1_latest.json"
PER_DATE_SSOT = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"
MANIFEST_SSOT = ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json"
PSYCH_V2 = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv"
FUSION_STUB = ROOT / "reports/independent_lens_fusion_stub_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--psych-days", type=int, default=400)
    ap.add_argument("--eval-windows", type=int, nargs="+", default=[30, 252])
    ap.add_argument("--skip-yfinance", action="store_true")
    ap.add_argument("--skip-fusion-stub", action="store_true")
    ap.add_argument("--skip-comparison", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    def step(name: str, cmd: list[str]) -> bool:
        rc = _run(cmd)
        steps.append({"step": name, "exit_code": rc})
        return rc == 0

    if not args.skip_yfinance:
        if not step(
            "psych_v2_csv",
            [
                sys.executable,
                "scripts/build_market_psychology_kospi_from_yfinance_v2.py",
                "--days",
                str(args.psych_days),
            ],
        ):
            return 2
    else:
        steps.append({"step": "psych_v2_csv", "exit_code": 0, "skipped": True})

    for name, script in (
        ("map_v2", "scripts/map_market_psych_to_sasang_axis_v2.py"),
        ("per_date_v2", "scripts/build_btrack_per_date_directions_market_psych_v2.py"),
        ("lens_v2_light", "scripts/refresh_market_sasang_lens_v2_light_v1.py"),
    ):
        if not step(name, [sys.executable, script]):
            return 2

    if not args.skip_fusion_stub:
        FUSION_STUB.parent.mkdir(parents=True, exist_ok=True)
        if not step(
            "fusion_stub_v2_primary",
            [
                sys.executable,
                "scripts/report_independent_lens_fusion_stub_v0.py",
                "--output",
                str(FUSION_STUB),
            ],
        ):
            return 2

    price_lanes: list[dict[str, Any]] = []
    for days in args.eval_windows:
        price_lanes.append(
            _eval_lane("market_psych_v2_recommended", PER_DATE_SSOT, days, f"{days}d")
        )

    if not args.skip_comparison:
        if not step(
            "comparison_board",
            [sys.executable, "scripts/build_session_myeongni_vs_agct_market_psych_comparison_v1.py"],
        ):
            return 2

    manifest = json.loads(MANIFEST_SSOT.read_text(encoding="utf-8")) if MANIFEST_SSOT.is_file() else {}
    promo = manifest.get("manifest_promotion_v1") or {}

    doc = {
        "schema": "market_psych_v2_recommended_ops_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "not_promoted_track_a": True,
        "operating_principle_ko": "인간=DNA/AGCT 별도 · 시장 per-date dna=0 market=1",
        "inputs": {
            "manifest": _rel(MANIFEST_SSOT),
            "psych_csv": _rel(PSYCH_V2),
            "per_date_ssot": _rel(PER_DATE_SSOT),
            "dna_weight": 0.0,
            "market_weight": 1.0,
        },
        "ssot_promotion": {
            "profile_id": promo.get("profile_id"),
            "version": manifest.get("version"),
        },
        "steps": steps,
        "price_hit_rate": price_lanes,
        "daily_chain_recommended": {
            "script": "scripts/run_btrack_daily_hypothesis_chain.ps1",
            "market_psych_v2_primary": "default ON (refresh_market_sasang_lens_v2_light_v1.py)",
            "parallel_score_obs_env": "MKM_BTRACK_MARKET_PSYCH_V2_SCORE_OBS=1",
            "parallel_score_artifacts": [
                "reports/btrack_prophecy_score_market_psych_v2_daily_obs_latest.json",
                "docs/final/artifacts/prophecy_hit_rate_eval_market_psych_v2_daily_obs_latest.json",
            ],
            "skip_flags": "-SkipMarketPsychV2FusionPrimary · -SkipSessionMyeongniHybridObservation",
            "panel_alerts_dev": "-SkipPanel24hAlertsCheck",
        },
        "verdict_ko": (
            "시장 레일 권장: market_psych v2 per-date SSOT 갱신 + 30/252 price eval. "
            "Track A·실매매·ALERT1 승격 금지."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out.write_text(text, encoding="utf-8")
    ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_OUT.write_text(text, encoding="utf-8")
    print(args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
