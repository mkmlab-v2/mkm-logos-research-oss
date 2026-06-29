#!/usr/bin/env python3
"""Commander wellness advisory — anthropometrics + sasang lifestyle hints [HYPO]."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "data" / "lifestyle" / "wellness_bmi_sasang_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _bmi(height_cm: float, weight_kg: float) -> float:
    h_m = height_cm / 100.0
    if h_m <= 0:
        return 0.0
    return round(weight_kg / (h_m * h_m), 1)


def _bmi_band(bmi: float, rules: Dict[str, Any]) -> Tuple[str, str]:
    bands = rules.get("bmi_bands") or {}
    ordered = [
        ("under", bands.get("under") or {}),
        ("normal", bands.get("normal") or {}),
        ("over", bands.get("over") or {}),
        ("obese1", bands.get("obese1") or {}),
        ("obese2", bands.get("obese2") or {}),
    ]
    for _key, band in ordered:
        try:
            if bmi <= float(band.get("max", 0)):
                return str(band.get("label_ko") or "—"), _key
        except (TypeError, ValueError):
            continue
    return "—", "unknown"


def _anthropometrics(profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = profile.get("anthropometrics") or {}
    try:
        h = float(raw.get("height_cm"))
        w = float(raw.get("weight_kg"))
    except (TypeError, ValueError):
        return None
    if h <= 0 or w <= 0:
        return None
    bmi_val = _bmi(h, w)
    rules = _read_json(RULES_PATH) if RULES_PATH.is_file() else {}
    label, band_key = _bmi_band(bmi_val, rules)
    return {
        "height_cm": h,
        "weight_kg": w,
        "bmi": bmi_val,
        "bmi_band_ko": label,
        "bmi_band_key": band_key,
        "measured_at": raw.get("measured_at"),
    }


def build_wellness_advisory(
    profile: Dict[str, Any],
    *,
    lifestyle: Optional[Dict[str, Any]] = None,
    rules_path: Path = RULES_PATH,
) -> Dict[str, Any]:
    rules = _read_json(rules_path) if rules_path.is_file() else {}
    sasang = str(
        (lifestyle or {}).get("sasang_label")
        or ((profile.get("sasang_reference") or {}).get("label"))
        or "태양인"
    )
    anthro = _anthropometrics(profile)
    meals = (lifestyle or {}).get("meals") or {}
    lunch = meals.get("lunch_ko") or "따뜻한 국물 한 그릇"
    avoid = meals.get("avoid_ko") or []

    ex_rules = (rules.get("sasang_exercise") or {}).get(sasang) or {}
    diet_over = (rules.get("sasang_diet_over") or {}).get(sasang) or {}
    is_over = bool(anthro and anthro.get("bmi_band_key") in ("over", "obese1", "obese2"))

    exercise = list(ex_rules.get("over_ko" if is_over else "default_ko") or [])
    diet_focus = list(diet_over.get("focus_ko") or [])
    if lunch and lunch not in diet_focus:
        diet_focus.insert(0, f"오늘 식사 힌트: {lunch}")
    if avoid:
        diet_focus.append(f"피하기: {', '.join(avoid[:2])}")

    pace = str(diet_over.get("pace_ko") or "규칙적 리듬·수면 우선 [가설]")

    telegram_lines: List[str] = []
    if anthro:
        telegram_lines.extend(
            [
                "",
                "▸ 건강·라이프스타일 [가설]",
                (
                    f"  체형 {int(anthro['height_cm'])}cm/{anthro['weight_kg']:.0f}kg"
                    f" · BMI {anthro['bmi']} ({anthro['bmi_band_ko']}) · 체질 {sasang}"
                ),
                f"  식이: {' · '.join(diet_focus[:3])}",
                f"  운동: {' · '.join(exercise[:3])}",
                f"  페이스: {pace}",
                "  경계: 임상·처방·체중 보장 아님 · 실매매 무관",
            ]
        )

    return {
        "schema": "commander_wellness_advisory_v1",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "generated_at_utc": _utc_now(),
        "sasang_label": sasang,
        "anthropometrics": anthro,
        "diet_focus_ko": diet_focus,
        "exercise_ko": exercise,
        "pace_ko": pace,
        "telegram_append_lines": telegram_lines,
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--profile-json",
        type=Path,
        default=ROOT / "docs/final/artifacts/commander_profile_v1.example.json",
    )
    ap.add_argument("--lifestyle-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports/commander_wellness_advisory_latest.json")
    args = ap.parse_args()
    profile = _read_json(args.profile_json)
    lifestyle = _read_json(args.lifestyle_json) if args.lifestyle_json and args.lifestyle_json.is_file() else {}
    payload = build_wellness_advisory(profile, lifestyle=lifestyle)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    for ln in payload.get("telegram_append_lines") or []:
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
