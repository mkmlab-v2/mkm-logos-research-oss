# -*- coding: utf-8 -*-
"""Recompute pillars_native from PerfectManseryeok for each collision-dict entry (idempotent).

Use after manseryeok_perfect_final.py changes. Does not touch pillars_external.

  python scripts/collision_dict_refresh_native_v1.py --dry-run
  python scripts/collision_dict_refresh_native_v1.py --write
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.validate_ganji_mapping import _pillars_from_full  # noqa: E402

_DEFAULT = _WS / "docs/final/artifacts/manseryeok_collision_dictionary_v1.json"


def _parse_utc(s: str) -> datetime:
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    return datetime.fromisoformat(t).astimezone(timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Refresh pillars_native in collision dictionary from engine.")
    ap.add_argument("--input", type=Path, default=_DEFAULT)
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    ap.add_argument("--dry-run", action="store_true", help="Print only; do not write (default if --write omitted)")
    ap.add_argument("--write", action="store_true", help="Write JSON back if changed")
    args = ap.parse_args()
    if args.dry_run and args.write:
        ap.error("Use either --dry-run or --write, not both.")

    if not args.input.exists():
        print(f"Missing {args.input}", file=sys.stderr)
        return 1

    doc = json.loads(args.input.read_text(encoding="utf-8"))
    entries = doc.get("entries") or []
    tz = ZoneInfo(args.iana_tz)
    eng = PerfectManseryeok()
    changed = False

    for ent in entries:
        bio = ent.get("birth_instant_utc")
        if not bio:
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
        prev = ent.get("pillars_native") or {}
        if prev != obs:
            print(f"UPDATE {ent.get('key')}: {prev} -> {obs}")
            ent["pillars_native"] = obs
            changed = True
        else:
            print(f"OK     {ent.get('key')}")

    if changed and args.write:
        args.input.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {args.input}")
    elif changed and not args.write:
        print("Dry-run: use --write to persist", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
