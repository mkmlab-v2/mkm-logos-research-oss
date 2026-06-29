#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1 vs v2 market psych -> per-date -> price hit-rate (30d + 252d, market_weight=1)."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.market_psych_sasang_axis_v2 import (  # noqa: E402
    load_manifest,
    map_row_to_sasang,
    map_v1_heuristic_row,
    validate_psych_csv_fields,
)

DEFAULT_OUT = ROOT / "reports/market_psych_v1_vs_v2_price_ablation_v1_latest.json"
ARTIFACT_OUT = ROOT / "docs/final/artifacts/market_psych_v1_vs_v2_price_ablation_v1_latest.json"
PSYCH_V1 = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_latest.csv"
PSYCH_V2 = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _hit(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"kospi": None, "btc": None, "n_evaluated": None}
    doc = json.loads(path.read_text(encoding="utf-8"))
    m = doc.get("metrics") or {}
    return {
        "kospi": m.get("price_directional_hit_rate"),
        "btc": m.get("price_directional_hit_rate"),
        "n_evaluated": m.get("n_evaluated"),
    }


def _write_per_date_v1_from_csv(
    psych_csv: Path,
    out_json: Path,
    neutral_band: float,
) -> int:
    rows_out: list[dict[str, Any]] = []
    with psych_csv.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ts = str(row.get("timestamp_utc") or "")[:10]
            if len(ts) != 10:
                continue
            m = map_v1_heuristic_row(row, neutral_band=neutral_band)
            rows_out.append(
                {
                    "eval_date": ts,
                    "instrument": "multi",
                    "predicted_direction": m["predicted_direction"],
                    "confidence": round(min(1.0, abs(m["fusion_direction_score"])), 6),
                    "ensemble_mode": "market_psych_v1_heuristic",
                    "fusion_direction_score": m["fusion_direction_score"],
                    "mapping_target": m["mapping_target"],
                    "top_axis": m["top_axis"],
                    "fused_axis": m["axis_normalized"],
                }
            )
    rows_out.sort(key=lambda r: r["eval_date"])
    doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "ensemble_mode": "market_psych_v1_heuristic",
        "rows": rows_out,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def _eval_lane(
    lane_id: str,
    per_date: Path,
    eval_days: int,
    tag: str,
) -> dict[str, Any]:
    score = ROOT / f"reports/btrack_prophecy_score_{lane_id}_{tag}.json"
    ek = ROOT / f"reports/prophecy_hit_rate_{lane_id}_{tag}_kospi.json"
    eb = ROOT / f"reports/prophecy_hit_rate_{lane_id}_{tag}_btc.json"
    cmd = [
        sys.executable,
        "scripts/build_btrack_prophecy_score_from_ohlcv.py",
        "--per-date-direction-json",
        str(per_date),
        "--recent-trading-days",
        str(eval_days),
        "--output",
        str(score),
        "--force-dual-leg-panel",
    ]
    if BTC_CSV.is_file():
        cmd.extend(["--btc-csv", str(BTC_CSV)])
    rc_score = _run(cmd)
    rc_k = _run(
        [
            sys.executable,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score),
            "--headline-instrument",
            "kospi",
            "--output",
            str(ek),
        ]
    )
    rc_b = _run(
        [
            sys.executable,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score),
            "--headline-instrument",
            "btc",
            "--output",
            str(eb),
        ]
    )
    return {
        "lane_id": lane_id,
        "eval_days": eval_days,
        "per_date_json": str(per_date.relative_to(ROOT)).replace("\\", "/"),
        "score_json": str(score.relative_to(ROOT)).replace("\\", "/"),
        "exit_codes": {"score": rc_score, "eval_kospi": rc_k, "eval_btc": rc_b},
        "price_hit_rate": {
            "kospi": _hit(ek)["kospi"],
            "btc": _hit(eb)["btc"],
            "n_evaluated": _hit(ek)["n_evaluated"],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-windows", type=int, nargs="+", default=[30, 252])
    ap.add_argument("--psych-days", type=int, default=400)
    ap.add_argument("--skip-yfinance", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.skip_yfinance:
        if _run(
            [
                sys.executable,
                "scripts/build_market_psychology_kospi_from_yfinance_v1.py",
                "--days",
                str(max(60, min(args.eval_windows) * 2)),
            ]
        ):
            return 2
        if _run(
            [
                sys.executable,
                "scripts/build_market_psychology_kospi_from_yfinance_v2.py",
                "--days",
                str(args.psych_days),
            ]
        ):
            return 2

    if not PSYCH_V1.is_file() or not PSYCH_V2.is_file():
        print("missing v1 or v2 psych csv", file=sys.stderr)
        return 2

    manifest = load_manifest()
    with PSYCH_V2.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        validate_psych_csv_fields(reader.fieldnames, manifest)

    results: list[dict[str, Any]] = []
    for days in args.eval_windows:
        tag = f"{days}d"
        per_v1 = ROOT / f"reports/btrack_per_date_directions_market_psych_v1_{tag}.json"
        per_v2 = ROOT / f"reports/btrack_per_date_directions_market_psych_v2_{tag}.json"
        _write_per_date_v1_from_csv(PSYCH_V1, per_v1, neutral_band=0.06)
        rc = _run(
            [
                sys.executable,
                "scripts/build_btrack_per_date_directions_market_psych_v2.py",
                "--market-psych-csv",
                str(PSYCH_V2),
                "--out",
                str(per_v2),
            ]
        )
        if rc != 0:
            return rc
        results.append(_eval_lane("market_psych_v1", per_v1, days, tag))
        results.append(_eval_lane("market_psych_v2", per_v2, days, tag))

    def pick(lane: str, days: int) -> dict[str, Any] | None:
        for r in results:
            if r["lane_id"] == lane and r["eval_days"] == days:
                return r
        return None

    deltas: list[dict[str, Any]] = []
    for days in args.eval_windows:
        a = pick("market_psych_v1", days)
        b = pick("market_psych_v2", days)
        if not a or not b:
            continue
        k1 = (a.get("price_hit_rate") or {}).get("kospi")
        k2 = (b.get("price_hit_rate") or {}).get("kospi")
        deltas.append(
            {
                "eval_days": days,
                "kospi_v1": k1,
                "kospi_v2": k2,
                "kospi_v2_minus_v1_pp": round((float(k2) - float(k1)) * 100, 2) if k1 is not None and k2 is not None else None,
                "btc_v1": (a.get("price_hit_rate") or {}).get("btc"),
                "btc_v2": (b.get("price_hit_rate") or {}).get("btc"),
            }
        )

    hybrid = _load_json(ROOT / "reports/session_myeongni_hybrid_holdout_252d_v1.json")
    doc = {
        "schema": "market_psych_v1_vs_v2_price_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "not_promoted_track_a": True,
        "operating_principle_v1": {
            "human_rail": "AGCT/DNA·출생 — per-date index rail excluded (dna=0)",
            "market_rail_v2": "manifest market_psych_to_sasang_axis_manifest_v2.json",
            "primary_success_metric": "vocabulary_SSOT_and_policy_alignment",
            "secondary_metric": "price_directional_hit_rate",
        },
        "inputs": {
            "psych_v1_csv": str(PSYCH_V1.relative_to(ROOT)).replace("\\", "/"),
            "psych_v2_csv": str(PSYCH_V2.relative_to(ROOT)).replace("\\", "/"),
            "manifest": "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json",
        },
        "lanes": results,
        "delta_v2_minus_v1": deltas,
        "reference_session_hybrid_kospi_252d": (hybrid or {})
        .get("eval_prophecy_hit_rate", {})
        .get("hybrid", {})
        .get("kospi"),
        "verdict_ko": _verdict(deltas),
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_OUT.write_text(text, encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _verdict(deltas: list[dict[str, Any]]) -> str:
    parts = []
    for d in deltas:
        pp = d.get("kospi_v2_minus_v1_pp")
        if pp is None:
            continue
        parts.append(f"{d['eval_days']}d 코스피 v2-v1 {pp:+.2f}pp")
    body = "; ".join(parts) if parts else "no delta"
    return (
        f"{body}. v2=확장피처+매니페스트 SSOT; 1차 목표 어휘정렬, 2차 가격. "
        "B-track only, Track A·실매매 합선 금지."
    )


if __name__ == "__main__":
    raise SystemExit(main())
