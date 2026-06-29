#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI prophecy neutral-band fee sensitivity sweep [HYPO][research_only]."""

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

from scripts.eval_kospi_june2026_daily_prophecy_v1 import eval_calendar  # noqa: E402
from scripts.kospi_oos_significance_lib_v1 import metrics_from_eval_rows, significance_block  # noqa: E402

DEFAULT_BPS_GRID = (5.0, 10.0, 15.0, 20.0, 25.0)
DEFAULT_OUT = ROOT / "reports/kospi_prophecy_neutral_band_fee_sensitivity_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_prophecy_neutral_band_fee_sensitivity_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_fee_sensitivity_report(
    calendar: dict[str, Any],
    *,
    calendar_path: Path,
    as_of_kst: str | None,
    bps_grid: tuple[float, ...],
    year_month: str,
    model_id: str = "v2_lens3_heavy",
) -> dict[str, Any]:
    baseline_bps = float(bps_grid[0]) if bps_grid else 5.0
    baseline_eval = eval_calendar(
        calendar,
        calendar_path=calendar_path,
        as_of_kst=as_of_kst,
        neutral_bps_override=baseline_bps,
    )
    baseline_m = metrics_from_eval_rows(baseline_eval.get("rows") or [])

    rows: list[dict[str, Any]] = []
    for bps in bps_grid:
        ev = eval_calendar(
            calendar,
            calendar_path=calendar_path,
            as_of_kst=as_of_kst,
            neutral_bps_override=bps,
        )
        m = metrics_from_eval_rows(ev.get("rows") or [])
        rows.append(
            {
                "neutral_bps": bps,
                "metrics": m,
                "directional_significance": significance_block(
                    label=f"directional_neutral_bps_{bps:g}",
                    successes=float(m["hit"]),
                    n=int(m["n_directional_bets"]),
                ),
                "soft_significance": significance_block(
                    label=f"soft_neutral_bps_{bps:g}",
                    successes=float(m["soft_successes"]),
                    n=int(m["n_scored"]),
                ),
            }
        )

    base_soft = baseline_m.get("soft_hit_rate")
    deltas: list[dict[str, Any]] = []
    for row in rows:
        soft = (row.get("metrics") or {}).get("soft_hit_rate")
        deltas.append(
            {
                "neutral_bps": row["neutral_bps"],
                "soft_hit_rate_delta_vs_baseline": round((soft or 0) - (base_soft or 0), 4)
                if soft is not None and base_soft is not None
                else None,
            }
        )

    return {
        "schema": "kospi_prophecy_neutral_band_fee_sensitivity_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "prophecy_lane_role": "scoring_shadow",
        "model_id": model_id,
        "year_month": year_month,
        "as_of_kst": as_of_kst or baseline_eval.get("as_of_kst"),
        "calendar_path": str(calendar_path.relative_to(ROOT)).replace("\\", "/"),
        "interpretation_ko": (
            "neutral_bps 확대 = 왕복 수수료·슬리피지를 neutral 밴드로 흡수한 민감도 프록시. "
            "실매매 비용 모델 아님 · Track A 승격 금지."
        ),
        "baseline_neutral_bps": baseline_bps,
        "bps_grid": list(bps_grid),
        "baseline_metrics": baseline_m,
        "sweep": rows,
        "soft_delta_vs_baseline": deltas,
        "reproduce": (
            f"py scripts/build_kospi_prophecy_neutral_band_fee_sensitivity_v1.py "
            f"--year-month {year_month}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument(
        "--bps-grid",
        default=",".join(str(x) for x in DEFAULT_BPS_GRID),
        help="Comma-separated neutral bps grid",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    ns = ap.parse_args()

    tag = ns.year_month.replace("-", "")
    cal_path = ns.calendar_json or (ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json")
    if ns.year_month == "2026-06" and not cal_path.is_file():
        cal_path = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    if not cal_path.is_absolute():
        cal_path = ROOT / cal_path
    calendar = _read(cal_path)
    grid = tuple(float(x.strip()) for x in ns.bps_grid.split(",") if x.strip())

    doc = build_fee_sensitivity_report(
        calendar,
        calendar_path=cal_path,
        as_of_kst=ns.as_of_kst,
        bps_grid=grid,
        year_month=ns.year_month,
    )

    for p in (ns.out, ns.artifact):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sweep = doc.get("sweep") or []
    print(
        json.dumps(
            {
                "ok": True,
                "year_month": ns.year_month,
                "n_grid": len(sweep),
                "baseline_soft": doc.get("baseline_metrics", {}).get("soft_hit_rate"),
                "out": str(ns.out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
