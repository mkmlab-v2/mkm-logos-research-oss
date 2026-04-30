#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.5}
# Balance: 89
# Purpose: Autofill unresolved core100 node->verse refs using top-voted OpenBible references as provisional mapping.
# Keywords: core100, mapping, openbible, autofill, provisional
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def normalize_ref(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    if "-" in s:
        s = s.split("-", 1)[0].strip()
    return s.replace(":", ".")


def main() -> int:
    ap = argparse.ArgumentParser(description="Autofill unresolved core100 node mapping from OpenBible top-voted refs.")
    ap.add_argument("--map-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    ap.add_argument(
        "--openbible-txt",
        default="docs/final/artifacts/external_cross_references_openbible/cross_references.txt",
    )
    args = ap.parse_args()

    map_path = resolve(args.map_json)
    txt_path = resolve(args.openbible_txt)
    if not map_path.is_file():
        raise SystemExit(f"missing map json: {map_path}")
    if not txt_path.is_file():
        raise SystemExit(f"missing openbible txt: {txt_path}")

    data = json.loads(map_path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("invalid map json: rows must be list")

    # Build a stable pool of high-vote source refs.
    candidates: list[tuple[str, int]] = []
    with txt_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            src = normalize_ref(str(row.get("From Verse", "")))
            if not src:
                continue
            try:
                votes = int(str(row.get("Votes", "0")).strip() or 0)
            except ValueError:
                votes = 0
            candidates.append((src, votes))
    candidates.sort(key=lambda x: x[1], reverse=True)
    ordered_unique_refs: list[str] = []
    seen: set[str] = set()
    for ref, _ in candidates:
        if ref in seen:
            continue
        seen.add(ref)
        ordered_unique_refs.append(ref)

    if not ordered_unique_refs:
        raise SystemExit("no candidate refs found from openbible txt")

    fill_index = 0
    filled_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("verse_ref", "")).strip():
            continue
        ref = ordered_unique_refs[fill_index % len(ordered_unique_refs)]
        fill_index += 1
        row["verse_ref"] = ref
        row["status"] = "provisional_autofill_openbible"
        row["note"] = "Auto-filled from top-voted OpenBible source references; review before promotion."
        filled_count += 1

    data["autofill_meta"] = {
        "method": "openbible_top_voted_source_ref_cycle",
        "filled_count": filled_count,
        "candidate_pool_size": len(ordered_unique_refs),
    }
    map_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(map_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
