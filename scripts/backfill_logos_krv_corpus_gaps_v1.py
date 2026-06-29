#!/usr/bin/env python3
"""Backfill missing KRV verses (canon gap) via bskorea chapter fetch — P1 completion.

  py scripts/backfill_logos_krv_corpus_gaps_v1.py --dry-run
  py scripts/backfill_logos_krv_corpus_gaps_v1.py --max-chapters 50
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_logos_krv_corpus_from_bskorea_v1 import (  # noqa: E402
    DEFAULT_OUT,
    LOGOS_TO_BSK,
    _fetch_chapter,
    _load_existing,
)
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref, is_canonical_verse_ref

VERSE_REF_RE = __import__("re").compile(r"^([A-Za-z0-9_]+)\.(\d+)\.(\d+)$")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canon_refs() -> set[str]:
    manifest = json.loads((ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json").read_text(encoding="utf-8-sig"))
    rel = manifest.get("input_path", "data/logos/verse_4pipeline_full_31102.json")
    data = json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8-sig"))
    return {canonical_verse_ref(str(r.get("verse_id") or "")) for r in data if r.get("verse_id")}


def _group_missing_by_chapter(missing: list[str]) -> dict[tuple[str, int], list[int]]:
    groups: dict[tuple[str, int], list[int]] = defaultdict(list)
    for ref in missing:
        m = VERSE_REF_RE.match(ref)
        if not m:
            continue
        groups[(m.group(1), int(m.group(2)))].append(int(m.group(3)))
    return groups


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sleep-ms", type=int, default=280)
    ap.add_argument("--max-chapters", type=int, default=0, help="0 = all gap chapters")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    existing = _load_existing(args.out)
    canon = _canon_refs()
    missing = sorted(canon - set(existing.keys()))
    groups = _group_missing_by_chapter(missing)
    chapter_keys = sorted(groups.keys())

    if args.dry_run:
        print(
            json.dumps(
                {
                    "gap_count": len(missing),
                    "gap_chapters": len(chapter_keys),
                    "sample_chapters": [f"{b}.{c}" for b, c in chapter_keys[:8]],
                    "sample_missing": missing[:8],
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.max_chapters > 0:
        chapter_keys = chapter_keys[: args.max_chapters]

    fetched = 0
    errors: list[str] = []
    for book, chap in chapter_keys:
        bsk = LOGOS_TO_BSK.get(book)
        if not bsk:
            errors.append(f"no_bsk:{book}.{chap}")
            continue
        try:
            chapter_verses = _fetch_chapter(bsk, chap)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{book}.{chap}:{exc}")
            continue
        for vnum in groups[(book, chap)]:
            ref = f"{book}.{chap}.{vnum}"
            text = chapter_verses.get(vnum, "")
            if not text:
                errors.append(f"empty:{ref}")
                continue
            existing[ref] = text
            fetched += 1
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for ref in sorted(existing.keys(), key=lambda r: (r.split(".")[0], int(r.split(".")[1]), int(r.split(".")[2]))):
            fh.write(json.dumps({"ref": ref, "text_ko": existing[ref]}, ensure_ascii=False) + "\n")

    remaining = len(canon - set(existing.keys()))
    coverage = round(100.0 * len(set(existing.keys()) & canon) / len(canon), 4)
    print(
        json.dumps(
            {
                "ok": remaining < 50 or coverage >= 99.0,
                "fetched": fetched,
                "total": len(existing),
                "remaining_gap": remaining,
                "canon_coverage_pct": coverage,
                "errors_sample": errors[:8],
            },
            ensure_ascii=False,
        )
    )
    return 0 if remaining < 50 or coverage >= 99.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
