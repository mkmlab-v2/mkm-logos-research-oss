# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.9, K:0.4, M:0.6}
# Balance: 92
# Purpose: Run dual-engine saju verification with timezone-aware metadata.
# Keywords: saju, manseryeok, dual-verify, timezone, dst
"""Dual verification for four-pillar outputs.

Primary engine:
- scripts.manseryeok_perfect_final.PerfectManseryeok

Secondary engine:
- scripts.final_saju_verification.calculate_saju_manual
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.final_saju_verification import calculate_saju_manual
from scripts.core.boundary_risk_guard import BoundaryInput, evaluate_boundary_risks
from scripts.manseryeok_perfect_final import PerfectManseryeok
from scripts.saju_birth_resolver_v1 import resolve_from_utc_instant

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "saju_dual_verify_latest.json"
PILLARS = ("year", "month", "day", "hour")
BOUNDARY_ONLY_REASONS = {
    "near_zi_boundary_window",
    "near_branch_boundary_window",
    "near_solar_term_anchor_day",
}


def _hour_branch(local_dt: datetime) -> str:
    minute_of_day = local_dt.hour * 60 + local_dt.minute
    # Conventional 2-hour buckets with zi crossing midnight.
    buckets = [
        ("자", 23 * 60, 24 * 60),
        ("자", 0, 60),
        ("축", 60, 3 * 60),
        ("인", 3 * 60, 5 * 60),
        ("묘", 5 * 60, 7 * 60),
        ("진", 7 * 60, 9 * 60),
        ("사", 9 * 60, 11 * 60),
        ("오", 11 * 60, 13 * 60),
        ("미", 13 * 60, 15 * 60),
        ("신", 15 * 60, 17 * 60),
        ("유", 17 * 60, 19 * 60),
        ("술", 19 * 60, 21 * 60),
        ("해", 21 * 60, 23 * 60),
    ]
    for branch, start, end in buckets:
        if start <= minute_of_day < end:
            return branch
    return "자"


def _pillar_map_from_manual(doc: dict[str, Any]) -> dict[str, str]:
    return {
        "year": str(doc.get("year_pillar", "")),
        "month": str(doc.get("month_pillar", "")),
        "day": str(doc.get("day_pillar", "")),
        "hour": str(doc.get("hour_pillar", "")),
    }


def _pillar_diffs(primary: dict[str, str], secondary: dict[str, str]) -> dict[str, dict[str, str]]:
    diffs: dict[str, dict[str, str]] = {}
    for key in PILLARS:
        if primary.get(key) != secondary.get(key):
            diffs[key] = {
                "primary": str(primary.get(key, "")),
                "secondary": str(secondary.get(key, "")),
            }
    return diffs


def _policy_interpretation(
    *,
    is_confirmed: bool,
    reasons: list[str],
    pillar_diffs: dict[str, dict[str, str]],
    hour_branch_expected_match: bool,
) -> str:
    if is_confirmed:
        return "confirmed"
    reason_set = set(reasons)
    if (
        reason_set
        and reason_set.issubset(BOUNDARY_ONLY_REASONS)
        and not pillar_diffs
        and hour_branch_expected_match
    ):
        return "boundary_warning_only"
    if "pillar_mismatch_between_engines" in reason_set:
        return "engine_mismatch_review"
    if "hour_branch_mismatch_vs_input_time" in reason_set:
        return "hour_branch_review"
    if {
        "ambiguous_local_time_due_to_dst",
        "nonexistent_local_time_due_to_dst",
    } & reason_set:
        return "dst_review"
    return "review_required"


def _dst_transition_flags(year: int, month: int, day: int, hour: int, minute: int, tz: ZoneInfo) -> dict[str, Any]:
    naive = datetime(year, month, day, hour, minute)
    aware_fold0 = naive.replace(tzinfo=tz, fold=0)
    aware_fold1 = naive.replace(tzinfo=tz, fold=1)
    offset0 = aware_fold0.utcoffset()
    offset1 = aware_fold1.utcoffset()
    is_ambiguous = offset0 != offset1

    # Nonexistent local time detector via UTC roundtrip mismatch.
    aware = aware_fold0
    rt = aware.astimezone(ZoneInfo("UTC")).astimezone(tz)
    is_nonexistent = (
        rt.year != year
        or rt.month != month
        or rt.day != day
        or rt.hour != hour
        or rt.minute != minute
    )

    return {
        "is_ambiguous_local_time": bool(is_ambiguous),
        "is_nonexistent_local_time": bool(is_nonexistent),
        "fold0_offset_seconds": int(offset0.total_seconds()) if offset0 else 0,
        "fold1_offset_seconds": int(offset1.total_seconds()) if offset1 else 0,
    }


@dataclass
class VerifyInput:
    year: int
    month: int
    day: int
    hour: int
    minute: int
    tz: str
    is_solar: bool
    is_male: bool
    secondary_day_rollover_policy: str


def resolve_verify_input_from_utc(
    birth_instant_utc_iso: str,
    tz_iana: str,
    *,
    is_solar: bool,
    is_male: bool,
    secondary_day_rollover_policy: str,
) -> tuple[VerifyInput, dict[str, Any]]:
    """Build VerifyInput from absolute instant + IANA zone (same contract as saju_birth_resolver_v1)."""
    res = resolve_from_utc_instant(birth_instant_utc_iso, tz_iana)
    ld = res.local_datetime
    inp = VerifyInput(
        year=ld.year,
        month=ld.month,
        day=ld.day,
        hour=ld.hour,
        minute=ld.minute,
        tz=res.iana_tz,
        is_solar=is_solar,
        is_male=is_male,
        secondary_day_rollover_policy=secondary_day_rollover_policy,
    )
    meta = {
        "mode": "utc_instant",
        "birth_instant_utc": res.birth_instant_utc.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
        "iana_tz": res.iana_tz,
        "local_iso": ld.isoformat(),
        "warnings": list(res.warnings),
        "resolver_meta": res.meta,
    }
    return inp, meta


def verify_dual_saju(inp: VerifyInput, *, birth_resolution_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    tz = ZoneInfo(inp.tz)
    local_dt = datetime(inp.year, inp.month, inp.day, inp.hour, inp.minute, tzinfo=tz)
    dst_flags = _dst_transition_flags(inp.year, inp.month, inp.day, inp.hour, inp.minute, tz)
    boundary_risk = evaluate_boundary_risks(
        BoundaryInput(
            year=inp.year,
            month=inp.month,
            day=inp.day,
            hour=inp.hour,
            minute=inp.minute,
        )
    )
    primary_engine = PerfectManseryeok()
    primary_doc = primary_engine.calculate_full_saju_perfect(
        year=inp.year,
        month=inp.month,
        day=inp.day,
        hour=inp.hour,
        is_solar=inp.is_solar,
        is_male=inp.is_male,
        day_rollover_policy=inp.secondary_day_rollover_policy,
    )
    primary_pillars = dict(primary_doc.get("saju") or {})
    secondary_raw = calculate_saju_manual(
        year=inp.year,
        month=inp.month,
        day=inp.day,
        hour=inp.hour,
        minute=inp.minute,
        day_rollover_policy=inp.secondary_day_rollover_policy,
    )
    secondary_pillars = _pillar_map_from_manual(secondary_raw)

    expected_hour_branch = _hour_branch(local_dt)
    primary_hour_branch = primary_pillars.get("hour", "")[-1:] if primary_pillars.get("hour") else ""
    secondary_hour_branch = secondary_pillars.get("hour", "")[-1:] if secondary_pillars.get("hour") else ""

    pillar_diffs = _pillar_diffs(primary_pillars, secondary_pillars)
    hour_branch_expected_match = (
        expected_hour_branch == primary_hour_branch == secondary_hour_branch
    )
    has_dst_risk = bool(dst_flags["is_ambiguous_local_time"]) or bool(dst_flags["is_nonexistent_local_time"])
    has_boundary_risk = bool(boundary_risk["is_boundary_risk"])
    is_confirmed = (
        len(pillar_diffs) == 0
        and hour_branch_expected_match
        and not has_dst_risk
        and not has_boundary_risk
    )

    reasons: list[str] = []
    if pillar_diffs:
        reasons.append("pillar_mismatch_between_engines")
    if not hour_branch_expected_match:
        reasons.append("hour_branch_mismatch_vs_input_time")
    if dst_flags["is_ambiguous_local_time"]:
        reasons.append("ambiguous_local_time_due_to_dst")
    if dst_flags["is_nonexistent_local_time"]:
        reasons.append("nonexistent_local_time_due_to_dst")
    for r in boundary_risk["reasons"]:
        reasons.append(r)
    policy_interpretation = _policy_interpretation(
        is_confirmed=is_confirmed,
        reasons=reasons,
        pillar_diffs=pillar_diffs,
        hour_branch_expected_match=hour_branch_expected_match,
    )

    return {
        "schema": "saju_dual_verify_v1",
        "verified_at_local": local_dt.isoformat(),
        "verified_at_utc": local_dt.astimezone(ZoneInfo("UTC")).isoformat(),
        "input": asdict(inp),
        "timezone_meta": {
            "offset_seconds": int(local_dt.utcoffset().total_seconds()) if local_dt.utcoffset() else 0,
            "dst_seconds": int(local_dt.dst().total_seconds()) if local_dt.dst() else 0,
            "expected_hour_branch": expected_hour_branch,
            "dst_transition_check": dst_flags,
            "boundary_risk_check": boundary_risk,
            **({"birth_resolution": birth_resolution_meta} if birth_resolution_meta else {}),
        },
        "primary": {
            "engine": "PerfectManseryeok",
            "pillars": primary_pillars,
            "calculation_method": primary_doc.get("calculation_method"),
            "verification_meta": primary_doc.get("verification"),
        },
        "secondary": {
            "engine": "manual_verified",
            "pillars": secondary_pillars,
            "calculation_method": secondary_raw.get("calculation_method"),
            "ground_truth_source": secondary_raw.get("ground_truth_source"),
            "effective_target_date": secondary_raw.get("effective_target_date"),
            "day_rollover_policy": secondary_raw.get("day_rollover_policy"),
        },
        "comparison": {
            "status": "CONFIRMED" if is_confirmed else "REVIEW",
            "is_confirmed": is_confirmed,
            "policy_interpretation": policy_interpretation,
            "reasons": reasons,
            "pillar_diffs": pillar_diffs,
            "hour_branch_check": {
                "primary_hour_branch": primary_hour_branch,
                "secondary_hour_branch": secondary_hour_branch,
                "expected_hour_branch": expected_hour_branch,
                "matches_expected": hour_branch_expected_match,
            },
        },
    }


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--birth-instant-utc",
        dest="birth_instant_utc",
        default=None,
        metavar="ISO",
        help="Absolute birth instant (ISO Z or offset); use with --tz IANA. Preferred for global/DST-safe input.",
    )
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--month", type=int, default=None)
    ap.add_argument("--day", type=int, default=None)
    ap.add_argument("--hour", type=int, default=None)
    ap.add_argument("--minute", type=int, default=0)
    ap.add_argument("--tz", type=str, default="Asia/Seoul")
    ap.add_argument("--solar", action="store_true", default=True)
    ap.add_argument("--no-solar", action="store_false", dest="solar")
    ap.add_argument("--male", action="store_true", default=True)
    ap.add_argument("--female", action="store_false", dest="male")
    ap.add_argument(
        "--secondary-day-rollover-policy",
        type=str,
        default="midnight_00",
        choices=("midnight_00", "zi_23"),
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--fail-on-review", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    birth_meta: dict[str, Any] | None = None
    if args.birth_instant_utc:
        try:
            inp, birth_meta = resolve_verify_input_from_utc(
                str(args.birth_instant_utc).strip(),
                str(args.tz).strip(),
                is_solar=bool(args.solar),
                is_male=bool(args.male),
                secondary_day_rollover_policy=str(args.secondary_day_rollover_policy),
            )
        except ValueError as e:
            print(f"saju_dual_verify: {e}", file=sys.stderr)
            return 1
    elif None not in (args.year, args.month, args.day, args.hour):
        inp = VerifyInput(
            year=int(args.year),
            month=int(args.month),
            day=int(args.day),
            hour=int(args.hour),
            minute=int(args.minute),
            tz=str(args.tz),
            is_solar=bool(args.solar),
            is_male=bool(args.male),
            secondary_day_rollover_policy=str(args.secondary_day_rollover_policy),
        )
    else:
        print(
            "saju_dual_verify: provide either --birth-instant-utc ISO + --tz IANA, "
            "or --year/--month/--day/--hour (+ optional --minute) + --tz.",
            file=sys.stderr,
        )
        return 2

    doc = verify_dual_saju(inp, birth_resolution_meta=birth_meta)
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    print(text)
    if not args.stdout_only:
        out_path = args.out if args.out.is_absolute() else ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
        print(f"\nWrote {out_path}")
    if bool(args.fail_on_review) and not bool(doc["comparison"]["is_confirmed"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
