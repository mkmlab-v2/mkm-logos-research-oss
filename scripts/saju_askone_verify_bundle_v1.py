#!/usr/bin/env python3
"""Ask-one saju verify bundle: dual verify + myeongni lite enrich (single stdout JSON)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.saju_dual_verify import (  # noqa: E402
    VerifyInput,
    resolve_verify_input_from_utc,
    verify_dual_saju,
)


def _run_myeongni_lite(
    *,
    birth_instant_utc: str,
    iana_tz: str,
    is_male: bool,
) -> dict[str, Any] | None:
    enrich = ROOT / "scripts" / "saju_myeongni_lite_enrich_v1.py"
    if not enrich.is_file():
        return None
    py = sys.executable
    args = [
        py,
        str(enrich),
        "--birth-instant-utc",
        birth_instant_utc.strip(),
        "--iana-tz",
        iana_tz.strip(),
    ]
    if is_male:
        args.append("--is-male")
    try:
        proc = subprocess.run(
            args,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        return json.loads(proc.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return None


def build_askone_verify_response(doc: dict[str, Any], *, myeongni_lite: dict[str, Any] | None) -> dict[str, Any]:
    comparison = doc.get("comparison") or {}
    status = str(comparison.get("status") or "BLOCK")
    policy = str(comparison.get("policy_interpretation") or "review_required")
    return {
        "gate_status": status,
        "policy_interpretation": policy,
        "reasons": comparison.get("reasons") or [],
        "timezone_meta": doc.get("timezone_meta") or {},
        "primary": doc.get("primary"),
        "secondary": doc.get("secondary"),
        "myeongni_lite": myeongni_lite if status != "BLOCK" else None,
        "source": "saju_askone_verify_bundle_v1",
    }


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--birth-instant-utc", dest="birth_instant_utc", default=None)
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
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    birth_meta: dict[str, Any] | None = None
    utc_instant: str | None = None

    if args.birth_instant_utc:
        try:
            inp, birth_meta = resolve_verify_input_from_utc(
                str(args.birth_instant_utc).strip(),
                str(args.tz).strip(),
                is_solar=bool(args.solar),
                is_male=bool(args.male),
                secondary_day_rollover_policy=str(args.secondary_day_rollover_policy),
            )
            utc_instant = str(args.birth_instant_utc).strip()
        except ValueError as e:
            print(json.dumps({"error": "invalid_input", "message": str(e)}, ensure_ascii=False))
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
            json.dumps(
                {
                    "error": "invalid_input",
                    "message": "birth_instant_utc+tz or y/m/d/h+tz required",
                },
                ensure_ascii=False,
            )
        )
        return 2

    doc = verify_dual_saju(inp, birth_resolution_meta=birth_meta)
    lite: dict[str, Any] | None = None
    if utc_instant and str(doc.get("comparison", {}).get("status") or "BLOCK") != "BLOCK":
        lite = _run_myeongni_lite(
            birth_instant_utc=utc_instant,
            iana_tz=str(args.tz),
            is_male=bool(args.male),
        )

    print(json.dumps(build_askone_verify_response(doc, myeongni_lite=lite), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
