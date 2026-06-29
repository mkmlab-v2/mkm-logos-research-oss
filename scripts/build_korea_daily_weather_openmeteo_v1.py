#!/usr/bin/env python3
"""Fetch Korea daily weather features (Open-Meteo) for B-track Myeongni join.

Zones: Seoul (capital proxy), Chuncheon (Gangwon dryness / wildfire prior).
Observed: archive API through last available day; remainder: forecast (≤16d) then
prior-year climatology for same calendar dates (labeled in meta).

research_only · no Track A / live trading.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/korea_daily_weather_openmeteo_v1.csv"
ZONES = {
    "seoul": {"label_ko": "서울", "lat": 37.5665, "lon": 126.9780},
    "chuncheon": {"label_ko": "춘천", "lat": 37.8813, "lon": 127.7298},
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _daterange(d0: date, d1: date) -> list[str]:
    out: list[str] = []
    d = d0
    while d <= d1:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _fetch_archive(lat: float, lon: float, d0: str, d1: str, *, timeout: float = 25.0) -> dict[str, list[Any]]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": d0,
        "end_date": d1,
        "daily": "precipitation_sum,relative_humidity_2m_mean,temperature_2m_max,windspeed_10m_max",
        "timezone": "Asia/Seoul",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + parse.urlencode(params)
    req = request.Request(url, headers={"User-Agent": "mkm-korea-weather/1.0"})
    with request.urlopen(req, timeout=timeout) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    daily = doc.get("daily") or {}
    return _parse_daily_series(daily)


def _num_list(vals: list[Any]) -> list[float]:
    out: list[float] = []
    for x in vals:
        if x is None:
            out.append(float("nan"))
        else:
            out.append(float(x))
    return out


def _parse_daily_series(daily: dict[str, Any]) -> dict[str, list[Any]]:
    return {
        "time": [str(x) for x in (daily.get("time") or [])],
        "precipitation_sum": _num_list(list(daily.get("precipitation_sum") or [])),
        "relative_humidity_2m_mean": _num_list(list(daily.get("relative_humidity_2m_mean") or [])),
        "temperature_2m_max": _num_list(list(daily.get("temperature_2m_max") or [])),
        "windspeed_10m_max": _num_list(list(daily.get("windspeed_10m_max") or [])),
    }


def _fetch_forecast(lat: float, lon: float, *, forecast_days: int = 16, timeout: float = 25.0) -> dict[str, list[Any]]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum,relative_humidity_2m_mean,temperature_2m_max,windspeed_10m_max",
        "timezone": "Asia/Seoul",
        "forecast_days": min(16, max(1, forecast_days)),
    }
    url = "https://api.open-meteo.com/v1/forecast?" + parse.urlencode(params)
    req = request.Request(url, headers={"User-Agent": "mkm-korea-weather/1.0"})
    with request.urlopen(req, timeout=timeout) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    daily = doc.get("daily") or {}
    return _parse_daily_series(daily)


def _series_to_by_date(series: dict[str, list[Any]], *, source: str) -> dict[str, dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    times = series.get("time") or []
    for i, t in enumerate(times):
        dk = str(t)[:10]
        def _cell(arr: list[float], idx: int) -> str:
            if idx >= len(arr):
                return ""
            v = arr[idx]
            if isinstance(v, float) and math.isnan(v):
                return ""
            return str(v)

        by[dk] = {
            "precip_mm": _cell(series["precipitation_sum"], i),
            "rh_mean_pct": _cell(series["relative_humidity_2m_mean"], i),
            "temp_max_c": _cell(series["temperature_2m_max"], i),
            "wind_max_kmh": _cell(series["windspeed_10m_max"], i),
            "weather_source": source,
        }
    return by


def build_zone_series(
    zone_key: str,
    d0: date,
    d1: date,
    *,
    archive_through: date,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    z = ZONES[zone_key]
    warns: list[str] = []
    merged: dict[str, dict[str, Any]] = {}
    want = _daterange(d0, d1)

    if archive_through >= d0:
        try:
            obs = _fetch_archive(
                z["lat"],
                z["lon"],
                d0.isoformat(),
                min(d1, archive_through).isoformat(),
            )
            merged.update(_series_to_by_date(obs, source="open_meteo_archive"))
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
            warns.append(f"{zone_key}_archive_fail:{e}")

    forecast_start = max(d0, archive_through + timedelta(days=1))
    if forecast_start <= d1:
        try:
            fc = _fetch_forecast(z["lat"], z["lon"], forecast_days=16)
            fc_by = _series_to_by_date(fc, source="open_meteo_forecast")
            for dk in _daterange(forecast_start, min(d1, forecast_start + timedelta(days=15))):
                if dk in fc_by and dk not in merged:
                    merged[dk] = fc_by[dk]
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
            warns.append(f"{zone_key}_forecast_fail:{e}")

    prior_year = d0.year - 1
    missing = [dk for dk in want if dk not in merged]
    if missing:
        try:
            p0 = date.fromisoformat(missing[0]).replace(year=prior_year).isoformat()
            p1 = date.fromisoformat(missing[-1]).replace(year=prior_year).isoformat()
            clim = _fetch_archive(z["lat"], z["lon"], p0, p1)
            clim_by = _series_to_by_date(clim, source=f"open_meteo_climatology_{prior_year}")
            for dk in missing:
                alt = date.fromisoformat(dk).replace(year=prior_year).isoformat()
                if alt in clim_by:
                    row = dict(clim_by[alt])
                    row["weather_source"] = f"climatology_{prior_year}"
                    merged[dk] = row
                else:
                    warns.append(f"{zone_key}_missing:{dk}")
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
            warns.append(f"{zone_key}_climatology_fail:{e}")

    return merged, warns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2026-06-01")
    ap.add_argument("--date-to", default="2026-06-30")
    ap.add_argument(
        "--archive-through",
        default=None,
        help="Last observed day YYYY-MM-DD (default: yesterday KST via UTC-1d approx)",
    )
    ap.add_argument("-o", "--out-csv", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-json", type=Path, default=None)
    ns = ap.parse_args()

    d0 = date.fromisoformat(ns.date_from)
    d1 = date.fromisoformat(ns.date_to)
    if ns.archive_through:
        arch_end = date.fromisoformat(ns.archive_through)
    else:
        arch_end = date.today() - timedelta(days=1)

    all_warns: list[str] = []
    zone_data: dict[str, dict[str, dict[str, Any]]] = {}
    for zk in ZONES:
        zone_data[zk], w = build_zone_series(zk, d0, d1, archive_through=arch_end)
        all_warns.extend(w)

    dates = _daterange(d0, d1)
    headers = ["date"]
    for zk in ZONES:
        for col in ("precip_mm", "rh_mean_pct", "temp_max_c", "wind_max_kmh", "weather_source"):
            headers.append(f"{zk}_{col}")

    rows_out: list[dict[str, str]] = []
    for dk in dates:
        row: dict[str, str] = {"date": dk}
        for zk in ZONES:
            zr = zone_data[zk].get(dk, {})
            for col in ("precip_mm", "rh_mean_pct", "temp_max_c", "wind_max_kmh", "weather_source"):
                v = zr.get(col, "")
                row[f"{zk}_{col}"] = "" if v is None else str(v)
        rows_out.append(row)

    ns.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows_out)

    meta_path = ns.meta_json or ns.out_csv.with_suffix(".meta.json")
    meta = {
        "schema": "korea_daily_weather_openmeteo_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "date_from": ns.date_from,
        "date_to": ns.date_to,
        "archive_through": arch_end.isoformat(),
        "zones": ZONES,
        "warnings": all_warns,
        "out_csv": str(ns.out_csv.resolve()),
        "join_hint": "join_btrack_session_panel_weather_ohlcv_v1.py --weather-date-col date",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows_out), "csv": str(ns.out_csv), "warnings": len(all_warns)}, ensure_ascii=False))
    return 0 if rows_out else 2


if __name__ == "__main__":
    raise SystemExit(main())
