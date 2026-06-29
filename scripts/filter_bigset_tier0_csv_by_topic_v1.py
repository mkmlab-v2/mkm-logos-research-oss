#!/usr/bin/env python3
"""Filter Tier-0 CSV rows by topic slug (in-place or --out). B-track · send_gate HOLD.

Reproducible:
  py scripts/filter_bigset_tier0_csv_by_topic_v1.py --csv docs/research/raw/bigset_nephilim_watcher_cross_refs_tier0_v1.csv --topic-slug nephilim_watcher_cross_refs --strict
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.merge_bigset_live_rows_v1 import (  # noqa: E402
    TOPIC_CONFLICT_GROUPS,
    _is_fixture,
    _row_matches_topic,
    write_csv,
)

DEFAULT_ART = ROOT / "docs/final/artifacts/bigset_tier0_topic_filter_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _strict_row_matches(row: dict[str, Any], topic_slug: str) -> bool:
    if _is_fixture(str(row.get("source_url") or "")):
        return topic_slug == "benei_haelohim_cross_refs"
    gid = str(row.get("conflict_group_id") or "").strip()
    allowed = TOPIC_CONFLICT_GROUPS.get(topic_slug, set())
    if topic_slug == "nephilim_watcher_cross_refs":
        if gid == "MKM_CONCEPT_NEPHILIM":
            return True
        blob = " ".join(
            str(row.get(k) or "")
            for k in ("excerpt", "interpretation_ko", "verse_ref", "tradition", "source_url")
        ).lower()
        if any(k in blob for k in ("nephilim", "watcher", "1 enoch", "jubilees")) and gid != "MKM_CONCEPT_SONS_OF_GOD":
            return True
        return False
    if topic_slug == "benei_haelohim_cross_refs":
        return gid in allowed or not gid
    return _row_matches_topic(row, topic_slug)


def filter_rows(
    rows: list[dict[str, str]],
    *,
    topic_slug: str,
    strict: bool,
) -> tuple[list[dict[str, str]], int]:
    kept: list[dict[str, str]] = []
    dropped = 0
    for row in rows:
        ok = _strict_row_matches(row, topic_slug) if strict else _row_matches_topic(row, topic_slug)
        if ok:
            kept.append(row)
        else:
            dropped += 1
    return kept, dropped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--topic-slug", required=True)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--out", type=Path, default=None, help="default: overwrite --csv")
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    args = ap.parse_args()

    csv_path = args.csv if args.csv.is_absolute() else (ROOT / args.csv)
    if not csv_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {csv_path}"}), file=sys.stderr)
        return 2

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = [dict(r) for r in csv.DictReader(f)]
    kept, dropped = filter_rows(rows, topic_slug=args.topic_slug, strict=args.strict)
    out_path = args.out if args.out else csv_path
    if args.out and not args.out.is_absolute():
        out_path = ROOT / args.out

    write_csv([dict(r) for r in kept], out_path)

    try:
        out_rel = str(out_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        out_rel = str(out_path.resolve())

    try:
        csv_rel = str(csv_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        csv_rel = str(csv_path.resolve())

    doc = {
        "schema": "bigset_tier0_topic_filter_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "send_gate": "HOLD",
        "topic_slug": args.topic_slug,
        "strict": args.strict,
        "rows_before": len(rows),
        "rows_after": len(kept),
        "rows_dropped": dropped,
        "out_csv": out_rel,
        "reproduce": (
            f"py scripts/filter_bigset_tier0_csv_by_topic_v1.py --csv {csv_rel} "
            f"--topic-slug {args.topic_slug}" + (" --strict" if args.strict else "")
        ),
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows_after": len(kept), "dropped": dropped}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
