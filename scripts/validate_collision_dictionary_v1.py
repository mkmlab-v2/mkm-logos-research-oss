# -*- coding: utf-8 -*-
"""Verify collision dictionary pillars_native matches PerfectManseryeok (regression).

Optional: report when pillars_external is filled and differs from native (informational).

Fill workflow: see docs/final/artifacts/manseryeok_collision_dictionary_v1.json key
collection_howto.steps (Postella / manual snapshot).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.validate_ganji_mapping import _normalize_pillar, _pillars_from_full  # noqa: E402

_DEFAULT_DICT = _WS / "docs/final/artifacts/manseryeok_collision_dictionary_v1.json"


def _parse_utc(s: str) -> datetime:
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    return datetime.fromisoformat(t).astimezone(timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate collision dictionary native pillars vs engine.")
    ap.add_argument("--input", type=Path, default=_DEFAULT_DICT)
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    args = ap.parse_args()

    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        print("zoneinfo required", file=sys.stderr)
        return 1

    if not args.input.exists():
        print(f"Missing {args.input}", file=sys.stderr)
        return 1

    doc = json.loads(args.input.read_text(encoding="utf-8"))
    entries = doc.get("entries") or []
    if not entries:
        print("No entries; nothing to verify.")
        return 0

    tz = ZoneInfo(args.iana_tz)
    eng = PerfectManseryeok()
    fail = 0
    for ent in entries:
        key = ent.get("key", "?")
        native = ent.get("pillars_native")
        bio = ent.get("birth_instant_utc")
        if not native or not bio:
            print(f"SKIP {key}: missing pillars_native or birth_instant_utc")
            continue
        dt_utc = _parse_utc(bio)
        loc = dt_utc.astimezone(tz)
        full = eng.calculate_full_saju_perfect(
            loc.year,
            loc.month,
            loc.day,
            loc.hour,
            is_solar=True,
            is_male=False,
        )
        obs = _pillars_from_full(full)
        exp = {k: _normalize_pillar(native.get(k, "")) for k in ("yeon", "wol", "il", "si")}
        ok = all(obs[k] == exp[k] for k in exp)
        if not ok:
            print(f"FAIL {key}: expected_native_stored={exp} observed_engine={obs}")
            fail += 1
        else:
            print(f"OK   {key}")
        ext = ent.get("pillars_external") or {}
        if ext and any(ext.get(k) for k in ("yeon", "wol", "il", "si")):
            ext_n = {k: _normalize_pillar(ext.get(k, "")) for k in ("yeon", "wol", "il", "si")}
            diff = any(obs[k] != ext_n[k] for k in ext_n)
            print(f"     external_vs_engine_mismatch={diff} (informational)")

    if fail:
        print(f"Collision dictionary: {fail} native mismatch(es)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
