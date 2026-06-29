#!/usr/bin/env python3
"""Build 31k bloom chapter-shard index for Logos Studio secondary fetch (P5).

Writes chapter shards + manifest for lazy load at query time.
  py scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
PIPELINE = ROOT / "data/logos/verse_4pipeline_full_31102.json"
OUT_ART = ROOT / "docs/final/artifacts/logos_studio_31k_bloom_secondary_fetch_v1_latest.json"
OUT_PUB = ROOT / "projects/no1kmedi/public/data/logos_studio/bloom_31k_index_v1.json"
SHARD_DIR_ART = ROOT / "docs/final/artifacts/logos_studio_bloom_shards_v1"
SHARD_DIR_PUB = ROOT / "projects/no1kmedi/public/data/logos_studio/bloom_shards_v1"

SCHEMA = "logos_studio_31k_bloom_secondary_fetch_v1"
VERSE_REF_RE = re.compile(r"^([A-Za-z0-9_]+)\.(\d+)\.(\d+)$")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_canon_refs() -> list[str]:
    if PIPELINE.is_file():
        data = json.loads(PIPELINE.read_text(encoding="utf-8-sig"))
        if isinstance(data, list):
            refs = [canonical_verse_ref(str(r.get("verse_id") or "")) for r in data if r.get("verse_id")]
            return [r for r in refs if VERSE_REF_RE.match(r)]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    rel = manifest.get("input_path", "data/logos/verse_4pipeline_full_31102.json")
    path = ROOT / str(rel).replace("/", "\\")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    refs = [canonical_verse_ref(str(r.get("verse_id") or "")) for r in data if r.get("verse_id")]
    return [r for r in refs if VERSE_REF_RE.match(r)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-shards", type=int, default=0, help="0 = all chapters")
    args = ap.parse_args()

    refs = _load_canon_refs()
    by_chapter: dict[tuple[str, int], list[str]] = defaultdict(list)
    for ref in refs:
        m = VERSE_REF_RE.match(ref)
        if not m:
            continue
        by_chapter[(m.group(1), int(m.group(2)))].append(ref)

    SHARD_DIR_ART.mkdir(parents=True, exist_ok=True)
    SHARD_DIR_PUB.mkdir(parents=True, exist_ok=True)

    chapter_shards: list[dict[str, Any]] = []
    for i, ((book, chap), vrefs) in enumerate(sorted(by_chapter.items(), key=lambda x: (x[0][0], x[0][1]))):
        if args.max_shards and i >= args.max_shards:
            break
        shard_id = f"{book}.{chap}"
        vrefs = sorted(vrefs, key=lambda r: int(r.rsplit(".", 1)[-1]))
        shard_doc = {
            "schema": "logos_studio_bloom_chapter_shard_v1",
            "shard_id": shard_id,
            "book": book,
            "chapter": chap,
            "verse_count": len(vrefs),
            "verse_refs": vrefs,
            "research_only": True,
            "hypothesis_tier": "B",
        }
        payload = json.dumps(shard_doc, ensure_ascii=False) + "\n"
        (SHARD_DIR_ART / f"{shard_id}.json").write_text(payload, encoding="utf-8")
        (SHARD_DIR_PUB / f"{shard_id}.json").write_text(payload, encoding="utf-8")
        chapter_shards.append(
            {
                "shard_id": shard_id,
                "book": book,
                "chapter": chap,
                "verse_count": len(vrefs),
                "public_url": f"/data/logos_studio/bloom_shards_v1/{shard_id}.json",
            }
        )

    doc = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "canon_denominator": 31102,
        "canon_verse_count": len(refs),
        "chapter_shard_count": len(chapter_shards),
        "shard_dir_relative": "docs/final/artifacts/logos_studio_bloom_shards_v1",
        "public_shard_dir": "/data/logos_studio/bloom_shards_v1",
        "chapter_shards": chapter_shards,
        "reproduce": "py scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py",
    }

    OUT_ART.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUB.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_ART.write_text(payload, encoding="utf-8")
    OUT_PUB.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "canon_verse_count": len(refs),
                "chapter_shard_count": len(chapter_shards),
                "out": str(OUT_ART),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
