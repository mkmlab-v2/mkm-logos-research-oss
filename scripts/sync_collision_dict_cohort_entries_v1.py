# -*- coding: utf-8 -*-
"""Add or update collision-dictionary entries from ganji_mapping_validate_cohort_v1.

Copies birth_instant_utc and expected_pillars -> pillars_native; leaves pillars_external
empty and policy_resolution unresolved until Forceteller/manual sampling.

  python scripts/sync_collision_dict_cohort_entries_v1.py --case-id lichun_y1988_off+0h --dry-run
  python scripts/sync_collision_dict_cohort_entries_v1.py --case-id lichun_y1988_off+0h --write
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

_WS = Path(__file__).resolve().parent.parent
_DEFAULT_COHORT = _WS / "docs/final/artifacts/ganji_mapping_validate_cohort_v1.json"
_DEFAULT_DICT = _WS / "docs/final/artifacts/manseryeok_collision_dictionary_v1.json"


def _parse_utc(s: str) -> datetime:
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    return datetime.fromisoformat(t).astimezone(timezone.utc)


def _wall_note(case_id: str, dt_utc: datetime, iana_tz: str) -> str:
    loc = dt_utc.astimezone(ZoneInfo(iana_tz))
    return (
        f"Wall clock {iana_tz} y={loc.year} m={loc.month} d={loc.day} h={loc.hour}; "
        f"ganji_mapping_validate_cohort_v1 case_id={case_id}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge cohort cases into collision dictionary.")
    ap.add_argument("--cohort", type=Path, default=_DEFAULT_COHORT)
    ap.add_argument("--output", type=Path, default=_DEFAULT_DICT, help="Collision dictionary JSON path")
    ap.add_argument("--case-id", action="append", dest="case_ids", metavar="ID", required=True)
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    ap.add_argument("--dict-version", default="", help="Set schema version string (e.g. 1.0.4); default: keep or bump +0.0.1")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.dry_run and args.write:
        ap.error("Use either --dry-run or --write, not both.")

    if not args.cohort.exists():
        print(f"Missing {args.cohort}", file=sys.stderr)
        return 1
    if not args.output.exists():
        print(f"Missing {args.output}", file=sys.stderr)
        return 1

    cohort_doc = json.loads(args.cohort.read_text(encoding="utf-8"))
    cases = {c["case_id"]: c for c in (cohort_doc.get("cases") or []) if c.get("case_id")}
    missing = [cid for cid in args.case_ids if cid not in cases]
    if missing:
        print(f"Unknown case_id(s): {missing}", file=sys.stderr)
        return 1

    doc = json.loads(args.output.read_text(encoding="utf-8"))
    entries = doc.get("entries") or []
    by_key = {e.get("key"): i for i, e in enumerate(entries)}

    for cid in args.case_ids:
        c = cases[cid]
        bio = c["birth_instant_utc"]
        exp = c.get("expected_pillars") or {}
        dt_utc = _parse_utc(bio)
        loc = c.get("location") or {}
        tz = loc.get("iana_tz") or args.iana_tz
        note = _wall_note(cid, dt_utc, tz)
        new_ent = {
            "key": cid,
            "birth_instant_utc": bio,
            "location_note": note,
            "pillars_native": {
                "yeon": exp.get("yeon", ""),
                "wol": exp.get("wol", ""),
                "il": exp.get("il", ""),
                "si": exp.get("si", ""),
            },
            "pillars_external": {},
            "policy_resolution": "unresolved",
            "notes": "pillars_native from cohort; fill pillars_external via Forceteller UI (collection_howto).",
        }
        if cid in by_key:
            entries[by_key[cid]] = new_ent
            print(f"UPDATE {cid}")
        else:
            entries.append(new_ent)
            print(f"ADD    {cid}")

    doc["entries"] = entries
    if args.dict_version:
        doc["version"] = args.dict_version
    elif not args.dry_run and args.write:
        v = str(doc.get("version") or "1.0.0")
        parts = v.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            doc["version"] = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
        else:
            doc["version"] = v + "+cohort"

    if args.dry_run:
        print("Dry-run: use --write to persist", file=sys.stderr)
        return 0

    if args.write:
        args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {args.output} version={doc.get('version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
