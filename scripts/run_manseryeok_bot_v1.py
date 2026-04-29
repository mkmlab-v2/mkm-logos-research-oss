#!/usr/bin/env python3
"""Single-command Manseryeok bot (global birth input -> pillars + verification).

Goal:
- Avoid long manual command composition.
- Provide one consistent output with boundary-risk diagnostics.
"""
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

from scripts.saju_birth_resolver_v1 import resolve_from_local_civil, resolve_from_utc_instant
from scripts.manseryeok_perfect_final import PerfectManseryeok
from scripts.saju_dual_verify import VerifyInput, verify_dual_saju

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "manseryeok_bot_latest.json"

PLACE_TZ: dict[str, str] = {
    "ladakh": "Asia/Kolkata",
    "leh": "Asia/Kolkata",
    "india": "Asia/Kolkata",
    "seoul": "Asia/Seoul",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_tz(place: str | None, tz: str | None) -> str:
    if tz:
        return tz.strip()
    key = (place or "").strip().lower()
    if key in PLACE_TZ:
        return PLACE_TZ[key]
    raise ValueError("timezone is required when place mapping is unavailable")


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-json", type=Path, default=None, help="Single input profile JSON")
    ap.add_argument("--name", type=str, default="profile")
    ap.add_argument("--place", type=str, default="")
    ap.add_argument("--tz", type=str, default="")
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--utc-instant", type=str, default="")
    g.add_argument("--local", nargs=5, type=int, metavar=("Y", "M", "D", "h", "m"))
    ap.add_argument("--sex", choices=("female", "male"), default="female")
    ap.add_argument("--analysis-depth", choices=("basic", "pro"), default="basic")
    ap.add_argument("--dst-fold", type=int, choices=(0, 1), default=0)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--compact", action="store_true")
    return ap.parse_args()


def _load_profile(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("profile-json must contain an object")
    return payload


def _apply_profile(args: argparse.Namespace) -> argparse.Namespace:
    if not args.profile_json:
        return args
    profile = _load_profile(args.profile_json)
    args.name = str(profile.get("name") or args.name)
    args.place = str(profile.get("place") or args.place)
    args.sex = str(profile.get("sex") or args.sex)
    args.analysis_depth = str(profile.get("analysis_depth") or args.analysis_depth)
    args.tz = str(profile.get("iana_tz") or profile.get("tz") or args.tz)
    if profile.get("birth_instant_utc"):
        args.utc_instant = str(profile["birth_instant_utc"])
        args.local = None
    elif profile.get("local") and isinstance(profile.get("local"), dict):
        local = profile["local"]
        args.local = [
            int(local["year"]),
            int(local["month"]),
            int(local["day"]),
            int(local["hour"]),
            int(local.get("minute", 0)),
        ]
        args.utc_instant = ""
    else:
        raise ValueError("profile-json requires birth_instant_utc or local {year,month,day,hour[,minute]}")
    return args


def _build_analysis(depth: str, review: dict[str, Any], primary: dict[str, Any]) -> dict[str, Any]:
    status = str(review.get("status") or "UNKNOWN")
    reasons = list(review.get("reasons") or [])
    day_pillar = str(primary.get("day") or "")
    day_stem = day_pillar[:1] if day_pillar else ""
    hour_pillar = str(primary.get("hour") or "")
    note_core = (
        "경계 리스크 없음, 확정 해석 가능"
        if status == "CONFIRMED"
        else "경계/엔진 불일치 리스크가 있어 확정 단정 금지"
    )
    basic = {
        "depth": "basic",
        "summary": [
            f"일주: {day_pillar or 'N/A'}",
            f"시주(주엔진): {hour_pillar or 'N/A'}",
            f"판정: {status}",
            note_core,
        ],
    }
    if depth != "pro":
        return basic

    daewoon_text = "대운 정보 없음"
    yeonun_text = "연운 정보 없음"
    return {
        "depth": "pro",
        "summary": basic["summary"],
        "details": {
            "day_stem": day_stem,
            "policy_interpretation": review.get("policy_interpretation"),
            "risk_reasons": reasons,
            "hour_branch_check": review.get("hour_branch_check", {}),
            "daewoon_text": daewoon_text,
            "yeonun_text": yeonun_text,
            "interpretation_guard": "status=REVIEW인 경우 대안 시주 병행 검토 권장",
        },
    }


def _build_daewoon_text(daewoon: list[dict[str, Any]], birth_year: int) -> str:
    if not daewoon:
        return "대운 정보 없음"
    now_year = datetime.now(timezone.utc).year
    age = max(0, now_year - birth_year)
    current = None
    for row in daewoon:
        a0 = int(row.get("age_start", -1))
        a1 = int(row.get("age_end", -1))
        if a0 <= age < a1:
            current = row
            break
    next_row = None
    if current is not None:
        idx = daewoon.index(current)
        if idx + 1 < len(daewoon):
            next_row = daewoon[idx + 1]
    if current is None:
        current = daewoon[0]
        next_row = daewoon[1] if len(daewoon) > 1 else None
    cur_txt = f"현재 대운: {current.get('saju')} ({current.get('age_start')}~{current.get('age_end')}세)"
    if next_row is None:
        return cur_txt
    nxt_txt = f"다음 대운: {next_row.get('saju')} ({next_row.get('age_start')}~{next_row.get('age_end')}세)"
    return f"{cur_txt} / {nxt_txt}"


def _build_yeonun_text(engine: PerfectManseryeok, years: list[int]) -> str:
    rows: list[str] = []
    for y in years:
        yp = engine.calculate_year_pillar(y, 6, 15)
        rows.append(f"{y}:{yp}")
    return "연운(연주 기준): " + ", ".join(rows)


def _build_alternative_hour_option(review: dict[str, Any], primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any] | None:
    status = str(review.get("status") or "")
    if status != "REVIEW":
        return None
    hour_check = review.get("hour_branch_check") or {}
    expected_branch = str(hour_check.get("expected_hour_branch") or "")
    primary_hour = str(primary.get("hour") or "")
    secondary_hour = str(secondary.get("hour") or "")
    option = {
        "enabled": True,
        "reason": "review_mode_hour_boundary",
        "expected_hour_branch": expected_branch,
        "primary_hour_pillar": primary_hour,
        "alternative_hour_pillar": secondary_hour if secondary_hour else None,
        "note": "경계시각 REVIEW 케이스에서는 대안 시주를 병행 검토하세요.",
    }
    return option


def _build_review_interpretation_paragraph(
    review: dict[str, Any],
    primary: dict[str, Any],
    alt: dict[str, Any] | None,
) -> str | None:
    status = str(review.get("status") or "")
    if status != "REVIEW":
        return None
    day_pillar = str(primary.get("day") or "N/A")
    primary_hour = str(primary.get("hour") or "N/A")
    alt_hour = str((alt or {}).get("alternative_hour_pillar") or "N/A")
    reasons = list(review.get("reasons") or [])
    reason_txt = ", ".join(reasons[:3]) if reasons else "engine_mismatch_review"
    return (
        f"현재 케이스는 REVIEW 상태로, 일주 {day_pillar} 해석은 유지하되 시주 해석은 "
        f"주 시주({primary_hour})와 대안 시주({alt_hour})를 병행 검토하는 것이 안전합니다. "
        f"주요 사유는 {reason_txt}이며, 확정 단정 대신 보수적 해석을 권장합니다."
    )


def main() -> int:
    try:
        args = _apply_profile(_parse_args())
        if not args.utc_instant and not args.local:
            raise ValueError("provide either --utc-instant, --local, or --profile-json")
        tz_name = _normalize_tz(args.place, args.tz)
    except Exception as e:
        print(f"manseryeok_bot: {e}", file=sys.stderr)
        return 2

    if args.utc_instant:
        res = resolve_from_utc_instant(args.utc_instant, tz_name)
    else:
        y, m, d, hh, mm = args.local
        res = resolve_from_local_civil(y, m, d, hh, mm, 0, tz_name, dst_fold=args.dst_fold)

    inp = VerifyInput(
        year=res.engine_year,
        month=res.engine_month,
        day=res.engine_day,
        hour=res.engine_hour,
        minute=res.local_datetime.minute,
        tz=res.iana_tz,
        is_solar=True,
        is_male=(args.sex == "male"),
        secondary_day_rollover_policy="midnight_00",
    )
    verify = verify_dual_saju(
        inp,
        birth_resolution_meta={
            "mode": res.meta.get("mode", "unknown"),
            "birth_instant_utc": res.birth_instant_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "iana_tz": res.iana_tz,
            "local_iso": res.local_datetime.isoformat(),
            "warnings": list(res.warnings),
        },
    )

    review = verify.get("comparison", {}) or {}
    primary = (verify.get("primary", {}) or {}).get("pillars", {}) or {}
    secondary = (verify.get("secondary", {}) or {}).get("pillars", {}) or {}
    eng = PerfectManseryeok()
    full_doc = eng.calculate_full_saju_perfect(
        res.engine_year,
        res.engine_month,
        res.engine_day,
        res.engine_hour,
        is_solar=True,
        is_male=(args.sex == "male"),
    )
    daewoon = list(full_doc.get("daewoon") or [])
    now_year = datetime.now(timezone.utc).year
    yeonun_years = [now_year, now_year + 1, now_year + 2]
    daewoon_text = _build_daewoon_text(daewoon, res.engine_year)
    yeonun_text = _build_yeonun_text(eng, yeonun_years)

    payload: dict[str, Any] = {
        "schema": "manseryeok_bot_v1",
        "generated_at_utc": _now(),
        "profile": {
            "name": args.name,
            "sex": args.sex,
            "analysis_depth": args.analysis_depth,
            "place": args.place,
            "iana_tz": res.iana_tz,
            "birth_instant_utc": res.birth_instant_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "birth_local_iso": res.local_datetime.isoformat(),
        },
        "pillars": {
            "primary_engine": primary,
            "secondary_engine": secondary,
            "recommended": primary if review.get("status") == "CONFIRMED" else primary,
            "status": review.get("status"),
            "policy_interpretation": review.get("policy_interpretation"),
            "reasons": review.get("reasons", []),
            "pillar_diffs": review.get("pillar_diffs", {}),
        },
        "boundary": (verify.get("timezone_meta", {}) or {}).get("boundary_risk_check", {}),
        "hour_branch_check": (review.get("hour_branch_check", {}) if isinstance(review, dict) else {}),
        "note": "If status=REVIEW, treat output as review-required and avoid hard claims.",
        "analysis": _build_analysis(args.analysis_depth, review, primary),
        "raw_verify": verify,
    }
    alt = _build_alternative_hour_option(review, primary, secondary)
    if alt is not None:
        payload["alternative_hour_option"] = alt
    review_para = _build_review_interpretation_paragraph(review, primary, alt)
    if review_para:
        payload["review_interpretation"] = {"paragraph_ko": review_para}
    if args.analysis_depth == "pro":
        payload["analysis"]["details"]["daewoon_text"] = daewoon_text
        payload["analysis"]["details"]["yeonun_text"] = yeonun_text
        payload["luck"] = {
            "daewoon": daewoon,
            "yeonun_years": yeonun_years,
            "daewoon_text": daewoon_text,
            "yeonun_text": yeonun_text,
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=None if args.compact else 2)
    args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nWROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
