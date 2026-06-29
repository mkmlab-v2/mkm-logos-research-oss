#!/usr/bin/env python3
"""Commander personal daily life oracle — Myeongni-weighted [HYPO] topics for morning briefing."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "data" / "lifestyle" / "daily_life_oracle_rules_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_tags(myeongni_lines: List[str], report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    text = "\n".join(myeongni_lines)
    mo_tg = ""
    m = re.search(r"월운\s*\d*월?\s*\S+\((\S+)\)", text)
    if m:
        mo_tg = m.group(1)
    ye_tg = ""
    m = re.search(r"세운\s*\S+\((\S+)\)", text)
    if m:
        ye_tg = m.group(1)
    ilun = ""
    m = re.search(r"일운\s*(\S+)", text)
    if m:
        ilun = m.group(1)
    weak_fire = "화" in text and ("약" in text or "결핍" in text)
    dom, weak = "", ""
    m2 = re.search(r"오행 우세\s*(\S+)\s*/\s*약\s*(\S+)", text)
    if m2:
        dom, weak = m2.group(1), m2.group(2)
        weak_fire = weak_fire or weak == "화"
    ilun_reactive = "별축" in text or "외부 변수" in text
    day_master = ""
    m3 = re.search(r"일간\s*(\S)", text)
    if m3:
        day_master = m3.group(1)
    if report:
        dm = (report.get("day_master") or {}).get("stem_hangul")
        if dm:
            day_master = str(dm)
    return {
        "month_ten_god": mo_tg,
        "year_ten_god": ye_tg,
        "ilun_ganji": ilun,
        "day_master": day_master,
        "weak_fire": weak_fire,
        "dominant_element": dom,
        "weakest_element": weak,
        "ilun_reactive": ilun_reactive,
    }


def _pick(d: Dict[str, Any], key: str, fallback: str) -> str:
    v = d.get(key)
    return str(v).strip() if v else fallback


def build_life_oracle(
    *,
    myeongni_lines: List[str],
    lifestyle: Optional[Dict[str, Any]] = None,
    report: Optional[Dict[str, Any]] = None,
    rules_path: Path = RULES_PATH,
) -> Dict[str, Any]:
    rules = _read_json(rules_path)
    tags = _extract_tags(myeongni_lines, report)
    mo = tags.get("month_ten_god") or ""
    mo_rules = (rules.get("month_ten_god") or {}).get(mo) or {}
    default = rules.get("default") or {}

    lifestyle = lifestyle or {}
    weather_band = str(lifestyle.get("weather_band") or "mild")
    w_rules = (rules.get("weather_band") or {}).get(weather_band) or {}
    weak_el = tags.get("weakest_element") or ""
    el_rules = (rules.get("element_weak") or {}).get(weak_el) or {}
    ilun_rules = rules.get("ilun_overlay") or {}

    headline = ""
    for ln in myeongni_lines:
        if "오늘 한 줄" in ln:
            headline = ln.replace("▸ ", "").strip()
            break
    if not headline and myeongni_lines:
        headline = myeongni_lines[0][:120]

    wsum = "—"
    if lifestyle.get("weather_path"):
        try:
            wdoc = _read_json(Path(str(lifestyle["weather_path"])))
            wsum = str((wdoc.get("current") or {}).get("summary_ko") or wsum)
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    lunch = str((lifestyle.get("meals") or {}).get("lunch_ko") or "따뜻한 국물 한 그릇")

    money = _pick(mo_rules, "money_ko", _pick(default, "money_ko", "—"))
    contract = _pick(mo_rules, "contract_ko", _pick(default, "contract_ko", "—"))
    social = _pick(mo_rules, "social_ko", _pick(default, "social_ko", "—"))
    traffic = _pick(default, "traffic_ko", "—")

    if tags.get("ilun_reactive"):
        traffic = _pick(ilun_rules.get("reactive") or {}, "traffic_ko", traffic)
        contract = _pick(ilun_rules.get("reactive") or {}, "contract_ko", contract) or contract
    if tags.get("day_master") == "경":
        traffic = _pick(ilun_rules.get("metal_day") or {}, "traffic_ko", traffic)
    if tags.get("weak_fire"):
        traffic = _pick(el_rules, "traffic_ko", traffic)
    traffic = _pick(w_rules, "traffic_ko", traffic)
    food = _pick(w_rules, "food_ko", lunch)
    if tags.get("weak_fire"):
        food = _pick(el_rules, "food_boost_ko", food)

    topics = {
        "weather_ko": wsum,
        "food_ko": food,
        "traffic_ko": traffic,
        "contract_ko": contract,
        "social_ko": social,
        "money_ko": money,
    }

    telegram_lines = [
        "",
        "▸ 하루 예언 (명리·생활) [가설]",
        f"  명리: {headline[:140]}{'…' if len(headline) > 140 else ''}",
        f"  날씨: {wsum}",
        f"  음식: {food}",
        f"  이동·차량: {traffic}",
        f"  계약·서명: {contract}",
        f"  인연: {social}",
        f"  금전: {money}",
        "  경계: 임상·법률·보험·실매매·시장% 단정 없음",
    ]

    compact_lines = [
        "",
        "▸ 지휘관 하루 예언 [가설·명리 우선]",
        f"  {headline[:100]}{'…' if len(headline) > 100 else ''}",
        f"  날씨 {wsum} · 식사 {food}",
        f"  차·이동 {traffic[:70]}{'…' if len(traffic) > 70 else ''}",
        f"  계약 {contract[:70]}{'…' if len(contract) > 70 else ''}",
        f"  인연 {social[:60]}{'…' if len(social) > 60 else ''}",
        f"  금전 {money[:70]}{'…' if len(money) > 70 else ''}",
    ]

    return {
        "schema": "commander_daily_life_oracle_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "boundary_ack": True,
        "generated_at_utc": _utc_now(),
        "myeongni_tags": tags,
        "topics": topics,
        "telegram_append_lines": telegram_lines,
        "telegram_compact_lines": compact_lines,
    }


def append_life_oracle_telegram(
    telegram_lines: List[str],
    *,
    myeongni_lines: List[str],
    lifestyle: Optional[Dict[str, Any]] = None,
    report: Optional[Dict[str, Any]] = None,
    compact: bool = False,
) -> Dict[str, Any]:
    oracle = build_life_oracle(
        myeongni_lines=myeongni_lines, lifestyle=lifestyle, report=report
    )
    key = "telegram_compact_lines" if compact else "telegram_append_lines"
    for ln in oracle.get(key) or []:
        if ln:
            telegram_lines.append(ln)
    return oracle
