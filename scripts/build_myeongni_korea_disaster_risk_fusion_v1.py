#!/usr/bin/env python3
"""Fuse session Myeongni panel + Korea daily weather → disaster risk grades (B-track).

Reads existing panel CSV + weather CSV (from build_korea_daily_weather_openmeteo_v1.py).
Writes wide joined CSV + fusion report JSON with myeongni-only vs fused grades.

research_only · not 擇日 · not Track A.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = ROOT / "reports/myeongni_korea_june2026_session_panel_v1.csv"
DEFAULT_WEATHER = ROOT / "reports/korea_daily_weather_openmeteo_v1.csv"
DEFAULT_WIDE = ROOT / "reports/myeongni_korea_june2026_fusion_wide_v1.csv"
DEFAULT_NEWS = ROOT / "reports/korea_disaster_news_context_v1.csv"
DEFAULT_REPORT = ROOT / "reports/myeongni_korea_june2026_disaster_risk_fusion_v2_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _myeongni_base_grade(row: dict[str, str]) -> tuple[str, float]:
    fire = _f(row.get("elem_fire"))
    wood = _f(row.get("elem_wood"))
    water = _f(row.get("elem_water"))
    metal = _f(row.get("elem_metal"))
    imb = _f(row.get("elem_imbalance"))
    wood_fire = fire >= 0.5 and wood >= 0.5
    score = fire + 0.35 * wood + 0.15 * imb
    if wood_fire and imb >= 0.55:
        return "S", score
    if fire >= 0.5 and (wood_fire or imb >= 0.55):
        return "A", score
    if metal >= 0.5:
        return "A", score * 0.9
    if water >= 0.5 or (fire >= 0.5 and water >= 0.25):
        return "B", score
    return "C", score


def _dryness(precip_mm: float, rh_pct: float) -> float:
    dry_p = max(0.0, min(1.0, 1.0 - precip_mm / 8.0))
    if rh_pct > 0:
        dry_h = max(0.0, min(1.0, (72.0 - rh_pct) / 40.0))
    else:
        dry_h = 0.5
    return 0.6 * dry_p + 0.4 * dry_h


def _weather_adjust(
    base: str,
    *,
    wildfire_idx: float,
    flood_idx: float,
    precip_mm: float,
) -> str:
    order = ["C", "B", "A", "S"]

    def _bump(g: str, n: int) -> str:
        i = min(len(order) - 1, max(0, order.index(g) + n))
        return order[i]

    def _cut(g: str, n: int) -> str:
        i = max(0, order.index(g) - n)
        return order[i]

    g = base
    if precip_mm >= 10.0:
        g = _cut(g, 2)
    elif precip_mm >= 3.0:
        g = _cut(g, 1)
    if wildfire_idx >= 0.42:
        g = _bump(g, 1)
    if wildfire_idx >= 0.55 and precip_mm < 1.0:
        g = _bump(g, 1)
    if flood_idx >= 0.45:
        g = _bump(g, 1)
    return g


def _news_adjust(
    grade: str,
    *,
    news_fire: float,
    news_flood: float,
    news_traffic: float,
    precip_mm: float,
) -> str:
    order = ["C", "B", "A", "S"]

    def _bump(g: str, n: int) -> str:
        i = min(len(order) - 1, max(0, order.index(g) + n))
        return order[i]

    def _cut(g: str, n: int) -> str:
        i = max(0, order.index(g) - n)
        return order[i]

    g = grade
    if news_fire >= 0.45 and precip_mm < 2.0:
        g = _bump(g, 1)
    if news_flood >= 0.4:
        g = _bump(g, 1)
    if news_traffic >= 0.35:
        g = _bump(g, 1)
    if news_fire >= 0.25 and news_flood >= 0.25:
        g = _cut(g, 1)  # mixed headlines -> downgrade certainty
    return g


def _load_news_by_date(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("date") or "")[:10]
            if dk:
                out[dk] = row
    return out


def _risk_indices(row: dict[str, str]) -> dict[str, float]:
    fire = _f(row.get("elem_fire"))
    wood = _f(row.get("elem_wood"))
    water = _f(row.get("elem_water"))
    metal = _f(row.get("elem_metal"))
    imb = _f(row.get("elem_imbalance"))
    sp = _f(row.get("wthr_seoul_precip_mm") or row.get("seoul_precip_mm"))
    sr = _f(row.get("wthr_seoul_rh_mean_pct") or row.get("seoul_rh_mean_pct"))
    cp = _f(row.get("wthr_chuncheon_precip_mm") or row.get("chuncheon_precip_mm"))
    cr = _f(row.get("wthr_chuncheon_rh_mean_pct") or row.get("chuncheon_rh_mean_pct"))
    dry = 0.5 * (_dryness(sp, sr) + _dryness(cp, cr))
    wildfire = min(0.95, (fire + 0.4 * wood) * (0.45 + 0.55 * dry) * (0.85 + 0.15 * imb))
    flood = min(0.95, (water + 0.2 * metal) * min(1.0, (sp + cp) / 12.0) + 0.1 * imb)
    traffic = min(0.95, metal * (0.7 + 0.3 * imb) + 0.15 * fire)
    return {
        "dryness_index": round(dry, 4),
        "wildfire_risk_index": round(wildfire, 4),
        "flood_risk_index": round(flood, 4),
        "traffic_industrial_risk_index": round(traffic, 4),
    }


def _theme_for_row(indices: dict[str, float], day_pillar: str) -> list[str]:
    themes: list[str] = []
    if indices["wildfire_risk_index"] >= 0.4:
        themes.append("산불·건조지 화재·방화")
    if indices["flood_risk_index"] >= 0.35:
        themes.append("침수·호우·누전")
    if indices["traffic_industrial_risk_index"] >= 0.38:
        themes.append("교통·산업·금속기계")
    if "오" in day_pillar or "병" in day_pillar or "정" in day_pillar:
        if "산불·건조지 화재·방화" not in themes and indices["wildfire_risk_index"] >= 0.3:
            themes.append("화기·전력·폭염")
    return themes or ["일반 관측"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--weather-csv", type=Path, default=DEFAULT_WEATHER)
    ap.add_argument("--wide-csv", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--news-csv", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--skip-join", action="store_true", help="Assume wide-csv already exists")
    ap.add_argument("--run-correlate", action="store_true")
    ap.add_argument("--refresh-weather", action="store_true", help="Re-fetch Open-Meteo weather CSV first")
    ns = ap.parse_args()

    if not ns.panel_csv.is_file():
        print(f"missing panel: {ns.panel_csv}", file=sys.stderr)
        return 2
    if ns.refresh_weather or not ns.weather_csv.is_file():
        rc_w = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_korea_daily_weather_openmeteo_v1.py"),
                "--date-from",
                "2026-06-01",
                "--date-to",
                "2026-06-30",
                "--archive-through",
                "2026-06-04",
            ],
            cwd=str(ROOT),
        ).returncode
        if rc_w != 0:
            return rc_w

    if not ns.weather_csv.is_file():
        print(f"missing weather: {ns.weather_csv}", file=sys.stderr)
        return 2

    news_by = _load_news_by_date(ns.news_csv) if ns.news_csv else {}

    if not ns.skip_join:
        cmd = [
            sys.executable,
            str(ROOT / "scripts/join_btrack_session_panel_weather_ohlcv_v1.py"),
            "--panel-csv",
            str(ns.panel_csv),
            "--weather-csv",
            str(ns.weather_csv),
            "--weather-date-col",
            "date",
            "--panel-date-col",
            "session_local_date",
            "--out-csv",
            str(ns.wide_csv),
            "--utf8-bom",
        ]
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        if rc != 0:
            return rc

    rows: list[dict[str, str]] = []
    with ns.wide_csv.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    fused_rows: list[dict[str, Any]] = []
    for row in rows:
        base_g, base_s = _myeongni_base_grade(row)
        idx = _risk_indices(row)
        precip = _f(row.get("wthr_seoul_precip_mm"))
        weather_g = _weather_adjust(
            base_g,
            wildfire_idx=idx["wildfire_risk_index"],
            flood_idx=idx["flood_risk_index"],
            precip_mm=precip,
        )
        dk = str(row.get("session_local_date") or "")[:10]
        nr = news_by.get(dk, {})
        nf = _f(nr.get("news_fire_score_7d"))
        nfl = _f(nr.get("news_flood_score_7d"))
        nt = _f(nr.get("news_traffic_score_7d"))
        fused_g = _news_adjust(
            weather_g,
            news_fire=nf,
            news_flood=nfl,
            news_traffic=nt,
            precip_mm=precip,
        )
        themes = _theme_for_row(idx, str(row.get("day_pillar") or ""))
        if nf >= 0.35 and "산불" not in " ".join(themes):
            themes.append("뉴스·7일지연:화재·산불 키워드")
        if nfl >= 0.35 and "침수" not in " ".join(themes):
            themes.append("뉴스·7일지연:호우·침수 키워드")
        fused_rows.append(
            {
                "date": row.get("session_local_date"),
                "day_pillar": row.get("day_pillar"),
                "month_pillar": row.get("month_pillar"),
                "myeongni_grade": base_g,
                "weather_grade": weather_g,
                "fused_grade": fused_g,
                "grade_delta": (["C", "B", "A", "S"].index(fused_g) - ["C", "B", "A", "S"].index(base_g)),
                "themes_ko": themes,
                "indices": idx,
                "news_context": {
                    "news_fire_score_7d": nf,
                    "news_flood_score_7d": nfl,
                    "news_traffic_score_7d": nt,
                    "article_count_lag": int(_f(nr.get("article_count_lag"))),
                    "news_source": nr.get("news_source", ""),
                },
                "elem_fire": _f(row.get("elem_fire")),
                "elem_imbalance": _f(row.get("elem_imbalance")),
                "seoul_precip_mm": precip,
                "seoul_rh_pct": _f(row.get("wthr_seoul_rh_mean_pct")),
                "chuncheon_precip_mm": _f(row.get("wthr_chuncheon_precip_mm")),
                "weather_source_seoul": row.get("wthr_seoul_weather_source", ""),
            }
        )

    corr_path = None
    if ns.run_correlate and rows:
        corr_path = ns.report_json.with_name("myeongni_korea_june2026_fusion_correlation_v1.json")
        cmd_c = [
            sys.executable,
            str(ROOT / "scripts/correlate_btrack_joined_wide_csv_v1.py"),
            "--input-csv",
            str(ns.wide_csv),
            "--y-col",
            "elem_fire",
            "--x-auto-prefixes",
            "elem_,wthr_",
            "--min-pairs",
            "8",
            "--out-json",
            str(corr_path),
        ]
        subprocess.run(cmd_c, cwd=str(ROOT))

    report = {
        "schema": "myeongni_korea_disaster_risk_fusion_v2",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "inputs": {
            "panel_csv": str(ns.panel_csv.resolve()),
            "weather_csv": str(ns.weather_csv.resolve()),
            "news_csv": str(ns.news_csv.resolve()) if ns.news_csv else None,
            "wide_csv": str(ns.wide_csv.resolve()),
        },
        "method": {
            "myeongni": "session 09:00 Seoul compute_quant_profile_v0",
            "weather": "Open-Meteo Seoul+Chuncheon (archive/forecast/climatology prior year)",
            "news": "Naver news lag7 (excludes same-day) + static calendar boost",
            "fusion": "myeongni -> weather -> news overlay; anti-lookahead on news",
        },
        "summary": {
            "n_days": len(fused_rows),
            "grade_changes": sum(1 for r in fused_rows if r["grade_delta"] != 0),
            "s_days_fused": [r["date"] for r in fused_rows if r["fused_grade"] == "S"],
            "top_wildfire": sorted(fused_rows, key=lambda r: r["indices"]["wildfire_risk_index"], reverse=True)[:5],
        },
        "days": fused_rows,
        "correlation_json": str(corr_path) if corr_path else None,
        "track_wall": "no_track_a_auto_merge",
    }
    ns.report_json.parent.mkdir(parents=True, exist_ok=True)
    ns.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(ns.report_json), "days": len(fused_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
