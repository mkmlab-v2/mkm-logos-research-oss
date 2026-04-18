# -*- coding: utf-8 -*-
"""Phase B-2: Mapping layer — PerfectManseryeok pillars vs optional expected (checksum).

Converts birth_instant_UTC to wall time in --iana-tz (default Asia/Seoul) before calling engine.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402

_DEFAULT_VALIDATE_INPUT = _WS / "docs/final/artifacts/ganji_mapping_validate_input_latest.json"

SCHEMA = "ganji_mapping_report_v1"
VERSION = "1.0.0"
RULE_SET_ID = "perfect_manseryeok_v1_midnight_rollover_default"
NORM_PROFILE = "hangul_two_chars_strip_ws_v1"


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_WS,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return (out.stdout or "").strip() or "unknown"
    except OSError:
        return "unknown"


def _parse_utc(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def _normalize_pillar(p: str) -> str:
    return (p or "").strip().replace(" ", "")


def _pillars_from_full(full: dict[str, Any]) -> dict[str, str]:
    inner = full.get("saju") or {}
    return {
        "yeon": _normalize_pillar(inner.get("year", "")),
        "wol": _normalize_pillar(inner.get("month", "")),
        "il": _normalize_pillar(inner.get("day", "")),
        "si": _normalize_pillar(inner.get("hour", "")),
    }


def _score(expected: dict[str, str] | None, observed: dict[str, str]) -> tuple[dict[str, bool], float, bool]:
    keys = ("yeon", "wol", "il", "si")
    if not expected:
        return {k: True for k in keys}, 1.0, True
    matches = {k: _normalize_pillar(expected.get(k, "")) == observed[k] for k in keys}
    n = sum(1 for v in matches.values() if v)
    return matches, n / 4.0, all(matches.values())


def _default_cases() -> dict[str, Any]:
    return {
        "schema": "ganji_mapping_validate_input_v1",
        "version": "1.0.0",
        "rule_set_id": RULE_SET_ID,
        "normalization_profile_id": NORM_PROFILE,
        "cases": [
            {
                "case_id": "sample_1992_03_13_02_kst",
                "birth_instant_utc": "1992-03-12T17:00:00Z",
                "expected_pillars": {
                    "yeon": "임신",
                    "wol": "계묘",
                    "il": "무자",
                    "si": "계축",
                },
            }
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate ganji mapping vs PerfectManseryeok.")
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help="ganji_mapping_validate_input_v1 JSON (default: ganji_mapping_validate_input_latest.json if present)",
    )
    ap.add_argument("--iana-tz", default="Asia/Seoul", help="Default IANA tz; per-case location.iana_tz overrides")
    ap.add_argument(
        "--output",
        type=Path,
        default=_WS / "docs/final/artifacts/ganji_mapping_report_latest.json",
    )
    ap.add_argument(
        "--fail-exact-match-rate-below",
        type=float,
        default=None,
        help="If set, exit 2 when aggregate exact_match_rate < this (e.g. 1.0 for CI)",
    )
    args = ap.parse_args()

    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        print("zoneinfo required (Python 3.9+)", file=sys.stderr)
        return 1

    inp = args.input
    if inp is None and _DEFAULT_VALIDATE_INPUT.exists():
        inp = _DEFAULT_VALIDATE_INPUT
    doc = _default_cases()
    if inp and inp.exists():
        doc = json.loads(inp.read_text(encoding="utf-8"))

    eng = PerfectManseryeok()
    rows_out: list[dict[str, Any]] = []

    for case in doc.get("cases", []):
        cid = case["case_id"]
        loc = case.get("location") or {}
        tz_name = loc.get("iana_tz") or args.iana_tz
        tz = ZoneInfo(tz_name)
        dt_utc = _parse_utc(case["birth_instant_utc"])
        local = dt_utc.astimezone(tz)
        y, m, d, h = local.year, local.month, local.day, local.hour

        full = eng.calculate_full_saju_perfect(
            y,
            m,
            d,
            h,
            is_solar=True,
            is_male=False,
        )
        observed = _pillars_from_full(full)

        exp = case.get("expected_pillars")
        if exp:
            exp_norm = {k: _normalize_pillar(exp.get(k, "")) for k in ("yeon", "wol", "il", "si")}
        else:
            exp_norm = {}

        pm, score, exact = _score(exp_norm if exp else None, observed)
        rows_out.append(
            {
                "case_id": cid,
                "observed_normalized": observed,
                "expected_normalized": exp_norm if exp else {},
                "pillar_matches": pm,
                "match_score": score,
                "string_exact_match": exact,
            }
        )

    n = len(rows_out)
    mean_score = sum(r["match_score"] for r in rows_out) / n if n else 0.0
    exact_rate = sum(1 for r in rows_out if r["string_exact_match"]) / n if n else 0.0

    report = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule_set_id": doc.get("rule_set_id", RULE_SET_ID),
        "normalization_profile_id": doc.get("normalization_profile_id", NORM_PROFILE),
        "engine": {
            "implementation": "PerfectManseryeok",
            "git_sha": _git_sha(),
        },
        "rows": rows_out,
        "aggregate": {"mean_match_score": mean_score, "exact_match_rate": exact_rate},
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote {args.output} mean_match_score={mean_score:.4f} exact_match_rate={exact_rate:.4f}"
    )
    if args.fail_exact_match_rate_below is not None:
        if exact_rate < float(args.fail_exact_match_rate_below):
            print(
                f"FAIL: exact_match_rate {exact_rate} < {args.fail_exact_match_rate_below}",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
