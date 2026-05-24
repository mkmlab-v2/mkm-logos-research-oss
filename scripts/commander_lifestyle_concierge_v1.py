#!/usr/bin/env python3
"""Commander lifestyle concierge v1 — Seoul default, rules + Open-Meteo weather [HYPO]."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, parse, request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
CITY_REGISTRY = ROOT / "data" / "lifestyle" / "city_registry_v1.json"
RULES_PATH = ROOT / "data" / "lifestyle" / "lifestyle_rules_v1.json"
SPOTS_PATH = ROOT / "data" / "lifestyle" / "seoul_warm_soup_spots_v1.json"
DEFAULT_WEATHER_OUT = ROOT / "reports" / "commander_weather_seoul_latest.json"
DEFAULT_LIFESTYLE_OUT = ROOT / "reports" / "commander_lifestyle_concierge_latest.json"

# WMO weather_code (Open-Meteo) → band
_RAIN_CODES = frozenset({51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99})
_SNOW_CODES = frozenset({71, 73, 75, 77, 85, 86})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _truthy(name: str, *, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def resolve_city_key() -> str:
    return (os.environ.get("MKM_COMMANDER_CITY") or "Seoul").strip() or "Seoul"


def load_city(city_key: Optional[str] = None) -> Dict[str, Any]:
    reg = _read_json(CITY_REGISTRY)
    key = city_key or resolve_city_key()
    cities = reg.get("cities") or {}
    if key not in cities:
        default = reg.get("default_city") or "Seoul"
        key = default if default in cities else next(iter(cities))
    return {"key": key, **cities[key]}


def fetch_open_meteo_current(city: Dict[str, Any], *, timeout: float = 12.0) -> Dict[str, Any]:
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code",
        "timezone": city.get("timezone") or "Asia/Seoul",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + parse.urlencode(params)
    req = request.Request(url, headers={"User-Agent": "mkm-commander-lifestyle/1.0"})
    with request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    cur = body.get("current") or {}
    temp = float(cur.get("temperature_2m") or 0)
    precip = float(cur.get("precipitation") or 0)
    code = int(cur.get("weather_code") or 0)
    humidity = cur.get("relative_humidity_2m")
    band = _weather_band(code, precip, temp)
    return {
        "schema": "commander_weather_snapshot_v1",
        "generated_at_utc": _utc_now(),
        "city_key": city.get("key", "Seoul"),
        "city_label_ko": city.get("label_ko", "서울"),
        "source": "open-meteo",
        "current": {
            "temperature_c": temp,
            "precipitation_mm": precip,
            "weather_code": code,
            "relative_humidity_pct": humidity,
            "band": band,
            "summary_ko": _weather_summary_ko(band, temp, precip, code),
        },
        "status": "ok",
    }


def _weather_band(code: int, precip: float, temp_c: float) -> str:
    if code in _SNOW_CODES:
        return "snow"
    if code in _RAIN_CODES or precip >= 0.2:
        return "rain"
    if temp_c < 10.0:
        return "cold"
    if temp_c >= 28.0:
        return "hot"
    return "mild"


def _weather_summary_ko(band: str, temp: float, precip: float, code: int) -> str:
    parts = [f"{temp:.0f}°C"]
    if band == "rain":
        parts.append("비·습기")
    elif band == "snow":
        parts.append("눈·한기")
    elif band == "cold":
        parts.append("쌀쌀")
    elif band == "hot":
        parts.append("무더위")
    else:
        parts.append("양호")
    if precip >= 0.2:
        parts.append(f"강수 {precip:.1f}mm")
    return " · ".join(parts)


def fetch_or_cache_weather(
    *,
    city_key: Optional[str] = None,
    out_path: Path = DEFAULT_WEATHER_OUT,
    allow_stale_hours: float = 6.0,
) -> Dict[str, Any]:
    city = load_city(city_key)
    city["key"] = city.get("key") or resolve_city_key()
    try:
        snap = fetch_open_meteo_current(city)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return snap
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        if out_path.is_file():
            cached = _read_json(out_path)
            cached["fetch_error"] = str(exc)[:200]
            cached["status"] = "stale_cache"
            return cached
        return {
            "schema": "commander_weather_snapshot_v1",
            "generated_at_utc": _utc_now(),
            "city_label_ko": city.get("label_ko", "서울"),
            "status": "error",
            "error": str(exc)[:200],
            "current": {"band": "mild", "summary_ko": "날씨 미수집 — 실내·온식 기본"},
        }


def _find_month_row(report: Dict[str, Any], year: int, month: int) -> Optional[Dict[str, Any]]:
    for row in (report.get("monthly_fortune") or {}).get("rows") or []:
        if int(row.get("year", 0)) == year and int(row.get("month", 0)) == month:
            return row
    return None


def _pick_spots(weather_band: str, sasang: str, *, max_n: int = 2) -> List[Dict[str, Any]]:
    if not SPOTS_PATH.is_file():
        return []
    doc = _read_json(SPOTS_PATH)
    want = {"warm_soup", "indoor"}
    if weather_band == "rain":
        want.add("rain_friendly")
    if sasang == "소음인":
        want.add("samgyetang")
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for spot in doc.get("spots") or []:
        tags = set(spot.get("tags") or [])
        score = len(tags & want)
        if score > 0:
            scored.append((score, spot))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:max_n]]


def build_lifestyle_payload(
    *,
    profile: Dict[str, Any],
    report: Dict[str, Any],
    weather: Dict[str, Any],
    rules_path: Path = RULES_PATH,
) -> Dict[str, Any]:
    rules = _read_json(rules_path)
    sasang = ((profile.get("sasang_reference") or {}).get("label")) or "태양인"
    fact = profile.get("myeongni_fact_ref") or {}
    ec = fact.get("element_counts_visible") or (
        ((report.get("structure_analysis") or {}).get("element_profile") or {}).get(
            "element_counts_visible"
        )
        or {}
    )
    dom = ((report.get("structure_analysis") or {}).get("element_profile") or {}).get(
        "dominant_element_visible"
    )
    weak = ((report.get("structure_analysis") or {}).get("element_profile") or {}).get(
        "weakest_element_visible"
    )
    dm = (report.get("day_master") or {}).get("stem_hangul") or fact.get("day_master_stem") or ""
    now_kst = datetime.now(KST)
    mo = _find_month_row(report, now_kst.year, now_kst.month) or {}
    mo_tg = str(mo.get("wolwoon_stem_ten_god") or "")

    cur = weather.get("current") or {}
    band = str(cur.get("band") or "mild")
    wsum = str(cur.get("summary_ko") or "—")

    sasang_rules = (rules.get("sasang") or {}).get(sasang) or {}
    w_overlay = (rules.get("weather_overlay") or {}).get(band) or {}
    ohang_rules = (rules.get("ohang_color") or {}).get(str(dom or "토")) or {}
    dm_accent = ((rules.get("day_master_accent") or {}).get(str(dm)) or {}).get("accent_ko") or ""
    tg_style = ((rules.get("month_ten_god_overlay") or {}).get(mo_tg) or {}).get("style_ko") or ""

    base_color = ohang_rules.get("base_ko", "—")
    accent = " · ".join(x for x in [ohang_rules.get("accent_ko"), dm_accent] if x)

    def _as_list(val: Any) -> List[str]:
        if val is None:
            return []
        if isinstance(val, str):
            return [val] if val.strip() else []
        return [str(x) for x in val if str(x).strip()]

    meals = _as_list(sasang_rules.get("meal_warm_ko"))
    for m in _as_list(w_overlay.get("meal_boost_ko")):
        if m not in meals:
            meals.append(m)
    avoid = _as_list(sasang_rules.get("meal_avoid_ko"))
    outfit = _as_list(sasang_rules.get("outfit_note_ko"))
    for o in _as_list(w_overlay.get("outfit_ko")):
        if o not in outfit:
            outfit.append(o)

    lunch = meals[0] if meals else "따뜻한 국물 한 그릇"
    lunch_alt = meals[1] if len(meals) > 1 else None

    spots = _pick_spots(band, sasang)
    spot_lines = [f"{s['name_ko']} ({s.get('area_ko', '서울')})" for s in spots]

    telegram_lines: List[str] = [
        "",
        "▸ 오늘 라이프 (명리×날씨×체질) [가설]",
        f"  날씨·{weather.get('city_label_ko', '서울')}: {wsum}",
        f"  퍼스널 컬러: {base_color}" + (f" / 포인트 {accent}" if accent else ""),
        f"  스타일: {' · '.join(outfit[:3])}",
    ]
    if tg_style:
        telegram_lines.append(f"  월운 톤: {tg_style}")
    telegram_lines.append(f"  점심 추천: {lunch}" + (f" 또는 {lunch_alt}" if lunch_alt else ""))
    if avoid:
        telegram_lines.append(f"  피하기: {', '.join(avoid[:2])}")
    if spot_lines:
        telegram_lines.append(f"  맛집(큐레이션): {' / '.join(spot_lines)}")
    telegram_lines.append("  웰니스 [가설] · 임상·실매매·예언% 무관")

    return {
        "schema": "commander_lifestyle_concierge_v1",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "generated_at_utc": _utc_now(),
        "calendar_kst": now_kst.strftime("%Y-%m-%d"),
        "city_key": weather.get("city_key") or resolve_city_key(),
        "weather_path": str(DEFAULT_WEATHER_OUT),
        "sasang_label": sasang,
        "weather_band": band,
        "dominant_element": dom,
        "weakest_element": weak,
        "personal_color": {"base_ko": base_color, "accent_ko": accent},
        "outfit_notes_ko": outfit,
        "meals": {"lunch_ko": lunch, "lunch_alt_ko": lunch_alt, "avoid_ko": avoid},
        "spots": spots,
        "telegram_append_lines": telegram_lines,
    }


def build_from_profile_report(
    profile: Dict[str, Any],
    report: Dict[str, Any],
    *,
    skip_weather_fetch: bool = False,
    city_key: Optional[str] = None,
) -> Dict[str, Any]:
    if skip_weather_fetch and DEFAULT_WEATHER_OUT.is_file():
        weather = _read_json(DEFAULT_WEATHER_OUT)
    else:
        weather = fetch_or_cache_weather(city_key=city_key)
    return build_lifestyle_payload(profile=profile, report=report, weather=weather)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-json", type=Path, default=ROOT / "docs/final/artifacts/commander_profile_v1.example.json")
    ap.add_argument("--report-json", type=Path, default=ROOT / "reports/commander_myeongni_full_daily_latest.json")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_LIFESTYLE_OUT)
    ap.add_argument("--weather-only", action="store_true")
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--city", type=str, default=None)
    args = ap.parse_args()

    city_key = args.city or resolve_city_key()
    if args.weather_only:
        snap = fetch_or_cache_weather(city_key=city_key) if not args.skip_fetch else _read_json(DEFAULT_WEATHER_OUT)
        print(json.dumps(snap, ensure_ascii=False, indent=2))
        return 0 if snap.get("status") in ("ok", "stale_cache") else 1

    profile = _read_json(args.profile_json)
    report = _read_json(args.report_json)
    payload = build_from_profile_report(
        profile, report, skip_weather_fetch=args.skip_fetch, city_key=city_key
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    for ln in payload.get("telegram_append_lines") or []:
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
