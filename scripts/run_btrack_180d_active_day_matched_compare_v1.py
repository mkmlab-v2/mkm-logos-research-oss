#!/usr/bin/env python3
"""[HYPO] 180d panel MS-active matched compare (parallel promotion research lane)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_btrack_active_day_matched_compare_v1 import build_compare

WORK = ROOT / "reports/btrack_180d_matched_work"
EXPANSION_WORK = ROOT / "reports/btrack_ms_180d_expansion_work"
OUT = ROOT / "reports/btrack_180d_active_day_matched_compare_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
SIDECAR = ROOT / "reports/btrack_prophecy_score_insight_sidecar_anchor_30d_v1.json"
SCORE_ANCHOR = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{cp.stderr or cp.stdout}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument(
        "--use-expansion-work",
        action="store_true",
        help="Skip rebuild; compare using reports/btrack_ms_180d_expansion_work artifacts.",
    )
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    n = int(args.recent_trading_days)
    py = sys.executable

    if args.use_expansion_work and (EXPANSION_WORK / "ms_per_date_180d.json").is_file():
        frozen_score = ROOT / "reports/btrack_prophecy_score_recommended_180d_v1.json"
        exp_v1 = EXPANSION_WORK / "v1_score_180d.json"
        doc = build_compare(
            anchor_score=EXPANSION_WORK / "score_180d.json",
            v1_score=exp_v1 if exp_v1.is_file() else EXPANSION_WORK / "score_180d.json",
            ms_per_date=EXPANSION_WORK / "ms_per_date_180d.json",
            frozen_score=frozen_score if frozen_score.is_file() else EXPANSION_WORK / "score_180d.json",
        )
        doc["schema"] = "btrack_180d_active_day_matched_compare_v1"
        doc["panel"]["recent_trading_days"] = n
        doc["panel"]["expansion_work"] = True
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.output.resolve()} (expansion work)")
        ms = doc["lanes"]["ms_on_ms_active"]
        v1 = doc["lanes"]["v1_per_date_on_ms_active"]
        print(
            f"180d MS-active n={doc['panel']['ms_active_days']}: "
            f"MS={ms['directional_hit_rate']} v1={v1['directional_hit_rate']} "
            f"frozen={doc['lanes']['frozen_kpi_a_on_ms_active']['directional_hit_rate']}"
        )
        return 0

    WORK.mkdir(parents=True, exist_ok=True)

    v1_per = WORK / "v1_per_date.json"
    ms_per = WORK / "ms_per_date.json"
    v1_score = WORK / "v1_score.json"
    frozen_score = ROOT / "reports/btrack_prophecy_score_recommended_180d_v1.json"
    if not frozen_score.is_file():
        frozen_score = v1_score

    _run(
        [
            py,
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            str(n),
            "--ensemble-mode",
            "v1",
            "--output",
            _rel(v1_per),
        ]
    )
    sidecar = SIDECAR if SIDECAR.is_file() else ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json"
    _run(
        [
            py,
            "scripts/build_btrack_lens_combo_myeongni_sasang_per_date_v1.py",
            "--score-json",
            _rel(SCORE_ANCHOR),
            "--sidecar-json",
            _rel(sidecar),
            "--output",
            _rel(ms_per),
        ]
    )
    _run(
        [
            py,
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--hypothesis-json",
            _rel(HYPO),
            "--btc-csv",
            _rel(BTC),
            "--kospi-csv",
            _rel(KOSPI),
            "--recent-trading-days",
            str(n),
            "--per-date-direction-json",
            _rel(v1_per),
            "--output",
            _rel(v1_score),
        ]
    )

    doc = build_compare(
        anchor_score=v1_score,
        v1_score=v1_score,
        ms_per_date=ms_per,
        frozen_score=frozen_score if frozen_score.is_file() else v1_score,
    )
    doc["schema"] = "btrack_180d_active_day_matched_compare_v1"
    doc["panel"]["recent_trading_days"] = n
    doc["operator_lines"] = [
        f"- [MKM-180D-MATCHED] Panel {n}d — MS-active subset; not comparable to 30d 56.7% headline.",
        "- [MKM-180D-MATCHED] Compare v1 vs MS on ms_active_days before MS-only narrative.",
        "- [MKM-180D-MATCHED] research_only; Track A / live unchanged.",
    ] + list(doc.get("operator_lines") or [])[1:]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    ms = doc["lanes"]["ms_on_ms_active"]
    v1 = doc["lanes"]["v1_per_date_on_ms_active"]
    print(
        f"180d MS-active n={doc['panel']['ms_active_days']}: "
        f"MS={ms['directional_hit_rate']} v1={v1['directional_hit_rate']} "
        f"frozen={doc['lanes']['frozen_kpi_a_on_ms_active']['directional_hit_rate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
