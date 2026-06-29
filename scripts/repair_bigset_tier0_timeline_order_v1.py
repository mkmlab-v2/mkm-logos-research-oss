#!/usr/bin/env python3
"""BigSet Tier-0 timeline repair — reorder rows within conflict_group_id [HYPO] shadow only.

Does not overwrite source CSV unless --in-place. Default writes repaired CSV + manifest.

Reproducible:
  py scripts/repair_bigset_tier0_timeline_order_v1.py --csv tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_bigset_tier0_timeline_order_v1 import evaluate, parse_verse_sort_key

DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/bigset_tier0_timeline_repair_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def _write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def repair_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    before = evaluate(rows)
    fieldnames = list(rows[0].keys()) if rows else []
    groups: OrderedDict[str, list[tuple[int, dict[str, str]]]] = OrderedDict()
    for i, row in enumerate(rows):
        gid = str(row.get("conflict_group_id") or "").strip() or "__ungrouped__"
        groups.setdefault(gid, []).append((i, row))

    repaired: list[dict[str, str]] = []
    moved = 0
    for gid, items in groups.items():
        if len(items) <= 1:
            repaired.extend(row for _, row in items)
            continue

        def sort_key(item: tuple[int, dict[str, str]]) -> tuple:
            idx, row = item
            vk = parse_verse_sort_key(str(row.get("verse_ref") or ""))
            return (vk if vk is not None else (9_999, 9_999, 9_999), idx)

        sorted_items = sorted(items, key=sort_key)
        original_order = [idx for idx, _ in items]
        new_order = [idx for idx, _ in sorted_items]
        if original_order != new_order:
            moved += 1
        repaired.extend(row for _, row in sorted_items)

    after = evaluate(repaired)
    meta = {
        "groups_reordered": moved,
        "inversions_before": before["inversion_count"],
        "inversions_after": after["inversion_count"],
        "row_count": len(rows),
        "gate_ok_before": before["gate_ok"],
        "gate_ok_after": after["gate_ok"],
    }
    return repaired, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument(
        "--out-csv",
        type=Path,
        default=None,
        help="repaired output (default: artifacts/bigset_tier0_timeline_repair_v1_latest.csv)",
    )
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--in-place", action="store_true", help="overwrite --csv (writes .bak alongside)")
    args = ap.parse_args()

    if not args.csv.is_file():
        print(json.dumps({"ok": False, "error": f"missing csv: {args.csv}"}), file=sys.stderr)
        return 2

    rows = _read_rows(args.csv)
    if not rows:
        print(json.dumps({"ok": False, "error": "empty csv"}), file=sys.stderr)
        return 2

    repaired, meta = repair_rows(rows)
    fieldnames = list(rows[0].keys())
    out_csv = args.out_csv
    if args.in_place:
        backup = args.csv.with_suffix(args.csv.suffix + ".bak")
        backup.write_bytes(args.csv.read_bytes())
        out_csv = args.csv
    elif out_csv is None:
        out_csv = ROOT / "docs/final/artifacts/bigset_tier0_timeline_repair_v1_latest.csv"

    _write_rows(out_csv, repaired, fieldnames)

    manifest = {
        "schema": "bigset_tier0_timeline_repair_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "source_csv": str(args.csv.relative_to(ROOT)) if args.csv.is_relative_to(ROOT) else str(args.csv),
        "repaired_csv": str(out_csv.relative_to(ROOT)) if out_csv.is_relative_to(ROOT) else str(out_csv),
        "in_place": bool(args.in_place),
        **meta,
        "reproduce": "py scripts/repair_bigset_tier0_timeline_order_v1.py --csv <tier0.csv>",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "gate_ok_after": meta["gate_ok_after"],
                "inversions_before": meta["inversions_before"],
                "inversions_after": meta["inversions_after"],
                "repaired_csv": str(out_csv),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
