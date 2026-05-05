# -*- coding: utf-8 -*-
"""
Build 12 시진 hour-pillar candidates for a **date-only** (unknown hour) profile.

Uses PerfectManseryeok + saju_birth_resolver_v1 local civil times — one representative
local wall hour per 시지, matching calculate_hour_pillar() boundaries in
scripts/manseryeok_perfect_final.py.

Output: saju_hour_uncertainty_v1 JSON (see docs/final/schemas/saju_hour_uncertainty_v1.schema.json).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.saju_birth_resolver_v1 import resolve_from_local_civil  # noqa: E402

# Order matches hour_ji_idx 0..11 in PerfectManseryeok.calculate_hour_pillar
JIJI_BRANCHES = list(PerfectManseryeok.JIJI)

# One stable local hour per branch that maps to that hour_ji_idx in the engine
REPRESENTATIVE_LOCAL_HOUR: list[int] = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]

# Display windows (civil clock; 자시는 23시 전후 경계 이슈 있음 — 대표 시각은 00:00 국면 샘플)
CLOCK_WINDOW_LOCAL: list[str] = [
    "23:00–01:00 (자시; 대표 샘플 local hour=0)",
    "01:00–03:00",
    "03:00–05:00",
    "05:00–07:00",
    "07:00–09:00",
    "09:00–11:00",
    "11:00–13:00",
    "13:00–15:00",
    "15:00–17:00",
    "17:00–19:00",
    "19:00–21:00",
    "21:00–23:00",
]

BRANCH_LABEL: list[str] = [
    "자시(子時)",
    "축시(丑時)",
    "인시(寅時)",
    "묘시(卯時)",
    "진시(辰時)",
    "사시(巳時)",
    "오시(午時)",
    "미시(未時)",
    "신시(申時)",
    "유시(酉時)",
    "술시(戌時)",
    "해시(亥時)",
]

DISCLAIMER_REF = "MKM-POL-003: Hour uncertainty prior applied; hour_pillar is conditional on representative sample times — not asserted as ground truth without recorded birth hour."


def _parse_branches_filter(s: str | None) -> set[int] | None:
    if not s or not s.strip():
        return None
    out: set[int] = set()
    for part in s.replace(" ", "").split(","):
        if not part:
            continue
        if part not in JIJI_BRANCHES:
            raise ValueError(f"unknown branch token {part!r}; expected one of {JIJI_BRANCHES}")
        out.add(JIJI_BRANCHES.index(part))
    if not out:
        return None
    return out


def build_bundle(
    year: int,
    month: int,
    day: int,
    iana_tz: str,
    *,
    is_male: bool = False,
    day_rollover_policy: str = "midnight_00",
    branches_filter: set[int] | None = None,
    dst_fold: int = 0,
) -> dict[str, Any]:
    eng = PerfectManseryeok()
    rows: list[dict[str, Any]] = []
    warnings_acc: list[str] = []

    fixed_saju: dict[str, str] | None = None
    anchor_local_iso = ""

    for idx, h in enumerate(REPRESENTATIVE_LOCAL_HOUR):
        res = resolve_from_local_civil(year, month, day, h, 0, 0, iana_tz, dst_fold=dst_fold)
        warnings_acc.extend(list(res.warnings))
        full = eng.calculate_full_saju_perfect(
            res.engine_year,
            res.engine_month,
            res.engine_day,
            res.engine_hour,
            is_solar=True,
            is_male=is_male,
            day_rollover_policy=day_rollover_policy,
        )
        if fixed_saju is None:
            fixed_saju = {
                "year": full["saju"]["year"],
                "month": full["saju"]["month"],
                "day": full["saju"]["day"],
            }
            anchor_local_iso = res.local_datetime.isoformat()

        hp = full["saju"]["hour"]
        branch = hp[1] if len(hp) >= 2 else ""
        rows.append(
            {
                "hour_pillar": hp,
                "hour_branch": branch,
                "clock_window_local": CLOCK_WINDOW_LOCAL[idx],
                "representative_local_hour": h,
                "probability": 0.0,
                "source_prior": "uniform",
                "labels": [BRANCH_LABEL[idx], JIJI_BRANCHES[idx]],
                "candidate_slot_index": idx,
            }
        )

    allowed = branches_filter if branches_filter is not None else set(range(12))
    n_allowed = len(allowed)
    if n_allowed == 0:
        raise ValueError("branches_filter produced zero candidates")

    prior_label = "window_filter" if branches_filter is not None else "uniform"
    for i, row in enumerate(rows):
        if i in allowed:
            row["probability"] = 1.0 / n_allowed
            row["source_prior"] = prior_label
        else:
            row["probability"] = 0.0
            row["source_prior"] = prior_label

    total_p = sum(r["probability"] for r in rows)
    if abs(total_p - 1.0) > 1e-9:
        raise RuntimeError("internal: probabilities do not sum to 1")

    local_date = f"{year:04d}-{month:02d}-{day:02d}"

    return {
        "schema": "saju_hour_uncertainty_v1",
        "version": "1.0.0",
        "hour_mode": "candidate_set",
        "iana_tz": iana_tz,
        "local_calendar_date": local_date,
        "is_male": is_male,
        "day_rollover_policy": day_rollover_policy,
        "fixed_saju": fixed_saju or {},
        "hour_distribution": rows,
        "disclaimer_ref": DISCLAIMER_REF,
        "meta": {
            "bundle_builder": "run_saju_hour_candidate_bundle_v1.py",
            "anchor_resolution_sample_local": anchor_local_iso,
            "probabilities_sum": round(total_p, 10),
            "filtered_branches": sorted(branches_filter) if branches_filter else None,
            "resolution_warnings": sorted(set(warnings_acc)),
            "note": "대운·격국 등은 시 샘플별로 변동 가능; 본 번들은 시주 후보 분포용 최소 필드만 포함.",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="12 시진 hour-pillar candidate bundle (probabilistic saju v1).")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--month", type=int, required=True)
    ap.add_argument("--day", type=int, required=True)
    ap.add_argument("--iana-tz", type=str, required=True, help="e.g. Asia/Seoul")
    ap.add_argument("--is-male", action="store_true")
    ap.add_argument(
        "--day-rollover-policy",
        type=str,
        default="midnight_00",
        choices=("midnight_00", "zi_23"),
    )
    ap.add_argument(
        "--branches-filter",
        type=str,
        default="",
        help="Comma-separated 시지 (자,축,인,...) — renormalize probability on this subset.",
    )
    ap.add_argument("--dst-fold", type=int, default=0, choices=(0, 1))
    ap.add_argument(
        "--out",
        type=str,
        default="",
        help="Output JSON path (default: docs/final/artifacts/saju_hour_candidate_bundle_v1_latest.json)",
    )
    ap.add_argument("--stdout", action="store_true", help="Print JSON to stdout instead of writing file.")
    args = ap.parse_args()

    filt = _parse_branches_filter(args.branches_filter)

    try:
        bundle = build_bundle(
            args.year,
            args.month,
            args.day,
            args.iana_tz.strip(),
            is_male=args.is_male,
            day_rollover_policy=args.day_rollover_policy,
            branches_filter=filt,
            dst_fold=args.dst_fold,
        )
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    text = json.dumps(bundle, ensure_ascii=False, indent=2)
    if args.stdout:
        print(text)
        return 0

    out = Path(args.out) if args.out else _WS / "docs/final/artifacts/saju_hour_candidate_bundle_v1_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
