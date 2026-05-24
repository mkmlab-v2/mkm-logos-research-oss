# -*- coding: utf-8 -*-
"""Engine-only manseryeok lookup (no LLM). Thin API over run_saju_global_birth stack.

B-track / Fact-Lock: four pillars come from PerfectManseryeok + IANA resolver only.
Track A live trading and external "AI computes saju" claims must not use this alone.

Example::

  py scripts/manseryeok_engine_lookup_v1.py --utc-instant 1992-03-12T17:00:00Z --iana-tz Asia/Seoul
  py scripts/manseryeok_engine_lookup_v1.py --request-json path/to/request.json --out reports/tmp_lookup.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.myeongri_deterministic_lora_golden_views_v1 import pillars_view  # noqa: E402
from scripts.saju_birth_resolver_v1 import (  # noqa: E402
    resolve_from_local_civil,
    resolve_from_utc_instant,
)

SCHEMA = "manseryeok_engine_lookup_v1"
VERSION = "1.0.0"
ENGINE_ID = "PerfectManseryeok_via_saju_global_birth_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_request(body: dict[str, Any]) -> None:
    if body.get("schema") not in (None, "saju_global_birth_request_v1"):
        raise ValueError(f"unsupported request schema: {body.get('schema')}")
    iana = str(body.get("iana_tz") or "").strip()
    if not iana:
        raise ValueError("iana_tz required")
    has_utc = bool(str(body.get("birth_instant_utc") or "").strip())
    has_local = isinstance(body.get("local_civil"), dict)
    if has_utc == has_local:
        raise ValueError("exactly one of birth_instant_utc or local_civil required")


def _build_saju_global_result(
    *,
    birth_instant_utc: str | None = None,
    local_civil: dict[str, int] | None = None,
    iana_tz: str,
    dst_fold: int = 0,
    is_male: bool = False,
) -> dict[str, Any]:
    if birth_instant_utc:
        res = resolve_from_utc_instant(birth_instant_utc, iana_tz)
    else:
        assert local_civil is not None
        res = resolve_from_local_civil(
            int(local_civil["year"]),
            int(local_civil["month"]),
            int(local_civil["day"]),
            int(local_civil["hour"]),
            int(local_civil["minute"]),
            int(local_civil.get("second", 0)),
            iana_tz,
            dst_fold=int(dst_fold),
        )
    eng = PerfectManseryeok()
    full = eng.calculate_full_saju_perfect(
        res.engine_year,
        res.engine_month,
        res.engine_day,
        res.engine_hour,
        is_solar=True,
        is_male=is_male,
    )
    return {
        "schema": "saju_global_birth_result_v1",
        "version": "1.0.0",
        "resolution": {
            "birth_instant_utc": res.birth_instant_utc.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            "iana_tz": res.iana_tz,
            "local_iso": res.local_datetime.isoformat(),
            "engine_inputs": {
                "year": res.engine_year,
                "month": res.engine_month,
                "day": res.engine_day,
                "hour": res.engine_hour,
            },
            "warnings": list(res.warnings),
            "meta": res.meta,
        },
        "full_saju": full,
    }


def lookup_from_request(body: dict[str, Any], *, include_full_saju: bool = True) -> dict[str, Any]:
    """Resolve birth → engine pillars. Returns manseryeok_engine_lookup_v1 envelope."""
    _validate_request(body)
    iana_tz = str(body["iana_tz"]).strip()
    is_male = bool(body.get("is_male", False))
    dst_fold = int(body.get("dst_fold", 0))

    birth_utc = str(body.get("birth_instant_utc") or "").strip() or None
    local = body.get("local_civil") if isinstance(body.get("local_civil"), dict) else None

    saju_result = _build_saju_global_result(
        birth_instant_utc=birth_utc,
        local_civil=local,  # type: ignore[arg-type]
        iana_tz=iana_tz,
        dst_fold=dst_fold,
        is_male=is_male,
    )
    pillars = pillars_view(saju_result)
    fs = saju_result.get("full_saju") if isinstance(saju_result.get("full_saju"), dict) else {}
    saju = fs.get("saju") if isinstance(fs.get("saju"), dict) else {}
    four = {
        "year": saju.get("year"),
        "month": saju.get("month"),
        "day": saju.get("day"),
        "hour": saju.get("hour") if saju.get("hour") is not None else saju.get("time"),
    }

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mode": "engine_lookup_only_no_llm",
        "engine_id": ENGINE_ID,
        "resolution": saju_result.get("resolution"),
        "four_pillars": four,
        "ilgan": fs.get("ilgan"),
        "pillars_view": pillars,
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
            "llm_computes_pillars": False,
        },
    }
    if include_full_saju:
        out["full_saju"] = fs
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--utc-instant", type=str, metavar="ISO")
    g.add_argument("--local", nargs=6, type=int, metavar=("Y", "M", "D", "h", "m", "s"))
    ap.add_argument("--iana-tz", type=str, default="")
    ap.add_argument("--dst-fold", type=int, default=0, choices=(0, 1))
    ap.add_argument("--is-male", action="store_true", default=False)
    ap.add_argument("--request-json", type=Path, help="saju_global_birth_request_v1 JSON file")
    ap.add_argument("--out", type=Path, default="", help="Write JSON result (default stdout)")
    ap.add_argument("--compact", action="store_true", help="Omit full_saju blob from output")
    ap.add_argument("--compact-json", action="store_true", help="Single-line JSON to stdout/file")
    args = ap.parse_args()

    if args.request_json:
        body = json.loads(args.request_json.read_text(encoding="utf-8"))
    elif args.utc_instant or args.local:
        if not args.iana_tz.strip():
            print("--iana-tz required with --utc-instant or --local", file=sys.stderr)
            return 2
        body = {
            "schema": "saju_global_birth_request_v1",
            "version": "1.0.0",
            "iana_tz": args.iana_tz.strip(),
            "is_male": args.is_male,
        }
        if args.utc_instant:
            body["birth_instant_utc"] = args.utc_instant
        else:
            y, m, d, h, mi, s = args.local
            body["local_civil"] = {
                "year": y,
                "month": m,
                "day": d,
                "hour": h,
                "minute": mi,
                "second": s,
            }
            body["dst_fold"] = args.dst_fold
    else:
        ap.print_help()
        return 2

    try:
        result = lookup_from_request(body, include_full_saju=not args.compact)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    if args.compact_json:
        text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "out": str(args.out)}, ensure_ascii=False))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
