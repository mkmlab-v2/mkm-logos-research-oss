#!/usr/bin/env python3
"""Build conflict_surface JSON from BigSet Tier-0 CSV rows [HYPO].

Schools are NOT merged — grouped under conflict_group_id with per-school tiers.

Reproducible:
  py scripts/build_bigset_conflict_surface_v1.py --csv docs/research/raw/bigset_benei_haelohim_cross_refs_tier0_v1.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/bigset_conflict_surface_v1_latest.json"

LEXICON_BY_GROUP = {
    "MKM_CONCEPT_SONS_OF_GOD": "Benei HaElohim",
    "MKM_CONCEPT_NEPHILIM": "Nephilim / Watchers",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def build_surface(rows: list[dict[str, str]]) -> dict[str, Any]:
    groups_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        gid = str(row.get("conflict_group_id") or "UNGROUPED").strip()
        school = str(row.get("school_tier") or "unknown").strip()
        if gid not in groups_map:
            groups_map[gid] = {
                "conflict_group_id": gid,
                "lexicon_base": LEXICON_BY_GROUP.get(gid, gid),
                "schools": {},
            }
        schools = groups_map[gid]["schools"]
        if school not in schools:
            schools[school] = {
                "school_tier": school,
                "interpretations": [],
                "citation_lock_anchors": [],
                "verse_refs": [],
                "traditions": [],
                "labels": ["research_only", "send_gate: HOLD", "NON_GATING"],
            }
        bucket = schools[school]
        interp = str(row.get("interpretation_ko") or "").strip()
        anchor = str(row.get("citation_lock_anchor") or row.get("source_url") or "").strip()
        if interp and interp not in bucket["interpretations"]:
            bucket["interpretations"].append(interp)
        if anchor and anchor not in bucket["citation_lock_anchors"]:
            bucket["citation_lock_anchors"].append(anchor)
        vref = str(row.get("verse_ref") or "").strip()
        if vref and vref not in bucket["verse_refs"]:
            bucket["verse_refs"].append(vref)
        trad = str(row.get("tradition") or "").strip()
        if trad and trad not in bucket["traditions"]:
            bucket["traditions"].append(trad)

    groups: list[dict[str, Any]] = []
    for gid, g in groups_map.items():
        school_list = []
        for school_id, s in g["schools"].items():
            school_list.append(
                {
                    "school_tier": school_id,
                    "interpretation_ko": " | ".join(s["interpretations"][:3]),
                    "citation_lock_anchors": s["citation_lock_anchors"],
                    "verse_refs": s["verse_refs"],
                    "traditions": s["traditions"],
                    "labels": s["labels"],
                }
            )
        groups.append(
            {
                "conflict_group_id": gid,
                "lexicon_base": g["lexicon_base"],
                "schools": sorted(school_list, key=lambda x: x["school_tier"]),
            }
        )

    return {
        "schema": "bigset_conflict_surface_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "no_lens_supremacy": True,
        "group_count": len(groups),
        "groups": groups,
        "reproduce": "py scripts/build_bigset_conflict_surface_v1.py --csv <tier0.csv>",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument(
        "--extra-csv",
        type=Path,
        action="append",
        default=None,
        help="additional tier0 CSVs merged for multi-topic conflict_surface [HYPO]",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    csv_path = args.csv if args.csv.is_absolute() else (ROOT / args.csv)
    if not csv_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {csv_path}"}), file=sys.stderr)
        return 2
    rows = _read_rows(csv_path)
    extra_paths: list[Path] = []
    for extra_path in args.extra_csv or []:
        p = extra_path if extra_path.is_absolute() else (ROOT / extra_path)
        if not p.is_file():
            print(json.dumps({"ok": False, "error": f"missing extra csv: {p}"}), file=sys.stderr)
            return 2
        extra_paths.append(p)
        rows.extend(_read_rows(p))
    doc = build_surface(rows)
    doc["source_csvs"] = [str(csv_path.relative_to(ROOT)).replace("\\", "/")]
    doc["source_csvs"].extend(str(p.relative_to(ROOT)).replace("\\", "/") for p in extra_paths)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "groups": doc["group_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
