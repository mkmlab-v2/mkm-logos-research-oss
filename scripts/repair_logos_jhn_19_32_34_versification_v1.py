#!/usr/bin/env python3
"""Repair merged SBLGNT paragraph duplicated on Jhn.19.32–34 in verse_decoded JSONL.

Track L / B-track corpus hygiene — splits one merged Greek block into per-verse rows.
Does not change verse count or Track A promotion gates.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"

TARGETS = ("Jhn.19.32", "Jhn.19.33", "Jhn.19.34")

# Split markers on original_text (SBLGNT); v32 ends at αὐτῷ, v33 before ἀλλ', v34 is pierce+blood/water.
_SPLIT_AFTER_V32 = "αὐτῷ"
_SPLIT_BEFORE_V34 = "ἀλλ’"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _strip_greek_accents(text: str) -> str:
    import unicodedata

    out: list[str] = []
    for ch in text:
        if unicodedata.category(ch) == "Mn":
            continue
        out.append(ch)
    return "".join(out).lower()


def _split_merged_original(merged: str) -> tuple[str, str, str] | None:
    if _SPLIT_AFTER_V32 not in merged or _SPLIT_BEFORE_V34 not in merged:
        return None
    head, tail = merged.split(_SPLIT_AFTER_V32, 1)
    v32 = head + _SPLIT_AFTER_V32
    mid, v34 = tail.split(_SPLIT_BEFORE_V34, 1)
    v33 = mid.strip()
    v34 = _SPLIT_BEFORE_V34 + v34
    if not v32.strip() or not v33.strip() or not v34.strip():
        return None
    return v32.strip(), v33.strip(), v34.strip()


def _recompute_row_fields(row: dict[str, Any], original_text: str) -> None:
    from scripts.build_logos_verse_gap_staging_v1 import _gematria_fields

    row["original_text"] = original_text
    row["text"] = _strip_greek_accents(original_text)
    row["source_ref"] = row.get("source_ref") or f"Jhn 19:{row['verse_id'].split('.')[-1]}"
    gem = _gematria_fields(row["text"])
    row.update(gem)
    row["interpretation"] = f"게마트리아 값 {row.get('total_value')} (versification repair v1)"


def _needs_repair(rows: dict[str, dict[str, Any]]) -> bool:
    if not all(v in rows for v in TARGETS):
        return False
    texts = [str(rows[v].get("original_text") or "") for v in TARGETS]
    return len(set(texts)) == 1 and all(texts)


def repair_jsonl(path: Path, *, write: bool) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    by_id: dict[str, dict[str, Any]] = {}
    indices: dict[str, int] = {}
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        row = json.loads(line)
        vid = str(row.get("verse_id") or "")
        if vid in TARGETS:
            by_id[vid] = row
            indices[vid] = idx

    report: dict[str, Any] = {
        "schema": "repair_logos_jhn_19_32_34_versification_v1",
        "generated_at_utc": _utc_now(),
        "jsonl": str(path),
        "needs_repair": _needs_repair(by_id),
        "repaired": False,
        "write": write,
    }
    if not report["needs_repair"]:
        report["reason"] = "rows missing or already distinct"
        return report

    merged = str(by_id["Jhn.19.32"].get("original_text") or "")
    split = _split_merged_original(merged)
    if not split:
        report["reason"] = "split markers not found in merged paragraph"
        return report

    v32_txt, v33_txt, v34_txt = split
    preview = {
        "Jhn.19.32": {"len": len(v32_txt), "has_blood_water": "αἷμα" in v32_txt and "ὕδωρ" in v32_txt},
        "Jhn.19.33": {"len": len(v33_txt), "has_blood_water": "αἷμα" in v33_txt and "ὕδωρ" in v33_txt},
        "Jhn.19.34": {"len": len(v34_txt), "has_blood_water": "αἷμα" in v34_txt and "ὕδωρ" in v34_txt},
    }
    report["preview"] = preview

    if not write:
        report["reason"] = "dry_run_only"
        return report

    backup = path.with_suffix(path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(path, backup)
    report["backup"] = str(backup)

    for vid, orig in zip(TARGETS, (v32_txt, v33_txt, v34_txt), strict=True):
        row = dict(by_id[vid])
        _recompute_row_fields(row, orig)
        lines[indices[vid]] = json.dumps(row, ensure_ascii=False)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report["repaired"] = True
    report["reason"] = "applied_per_verse_split"
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Repair Jhn.19.32–34 versification duplicates")
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--write", action="store_true", help="Apply repair (default: dry-run report only)")
    ap.add_argument("--stdout-json", action="store_true", default=True)
    args = ap.parse_args(argv)

    path = args.jsonl if args.jsonl.is_absolute() else ROOT / args.jsonl
    if not path.is_file():
        print(f"missing jsonl: {path}", file=sys.stderr)
        return 2

    report = repair_jsonl(path, write=args.write)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report.get("needs_repair"):
        return 0
    if args.write and not report.get("repaired"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
