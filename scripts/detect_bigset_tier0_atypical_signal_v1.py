#!/usr/bin/env python3
"""BigSet Tier-0 atypical signal detector — timeline bends on school/verse gaps [HYPO].

Observability only (always exit 0). Persly analog: flag non-linear timeline features
for human review — not diagnosis, not Track A trigger.

Reproducible:
  py scripts/detect_bigset_tier0_atypical_signal_v1.py --csv tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_bigset_tier0_timeline_order_v1 import parse_verse_sort_key

DEFAULT_OUT = ROOT / "docs/final/artifacts/bigset_tier0_atypical_signal_v1_latest.json"
LARGE_VERSE_GAP = 5


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_rows(path: Path) -> list[dict[str, str]]:
    import csv

    with path.open(encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def _verse_ordinal(key: tuple[int, int, int] | None) -> int | None:
    if key is None:
        return None
    book, chapter, verse = key
    return book * 1_000_000 + chapter * 1_000 + verse


def detect(rows: list[dict[str, str]]) -> dict[str, Any]:
    groups: OrderedDict[str, list[tuple[int, dict[str, str]]]] = OrderedDict()
    for i, row in enumerate(rows):
        gid = str(row.get("conflict_group_id") or "").strip() or "__ungrouped__"
        groups.setdefault(gid, []).append((i, row))

    signals: list[dict[str, Any]] = []
    for gid, items in groups.items():
        for j in range(len(items)):
            idx, row = items[j]
            tier = str(row.get("school_tier") or "")
            if 0 < j < len(items) - 1:
                prev_tier = str(items[j - 1][1].get("school_tier") or "")
                next_tier = str(items[j + 1][1].get("school_tier") or "")
                if tier and tier != prev_tier and tier != next_tier:
                    signals.append(
                        {
                            "signal_type": "school_tier_island",
                            "conflict_group_id": gid,
                            "row_index": idx,
                            "school_tier": tier,
                            "neighbors": [prev_tier, next_tier],
                        }
                    )

            if j > 0:
                prev_key = parse_verse_sort_key(str(items[j - 1][1].get("verse_ref") or ""))
                cur_key = parse_verse_sort_key(str(row.get("verse_ref") or ""))
                prev_ord = _verse_ordinal(prev_key)
                cur_ord = _verse_ordinal(cur_key)
                if prev_ord is not None and cur_ord is not None:
                    gap = cur_ord - prev_ord
                    if gap > LARGE_VERSE_GAP * 1_000:
                        signals.append(
                            {
                                "signal_type": "large_verse_gap",
                                "conflict_group_id": gid,
                                "row_index": idx,
                                "verse_ref": row.get("verse_ref"),
                                "prior_verse_ref": items[j - 1][1].get("verse_ref"),
                                "ordinal_gap": gap,
                            }
                        )

    return {
        "schema": "bigset_tier0_atypical_signal_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "row_count": len(rows),
        "signal_count": len(signals),
        "signals": signals,
        "thresholds": {"large_verse_gap_verses": LARGE_VERSE_GAP},
        "reproduce": "py scripts/detect_bigset_tier0_atypical_signal_v1.py --csv <tier0.csv>",
        "note_ko": "관측 전용 — 임상·Track A·SEND 트리거 아님",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.csv.is_file():
        print(json.dumps({"ok": False, "error": f"missing csv: {args.csv}"}), file=sys.stderr)
        return 2

    result = detect(_read_rows(args.csv))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "signal_count": result["signal_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
