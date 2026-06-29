#!/usr/bin/env python3
"""Build 4lens batch JSON from decoded corpus rows (real verse_id, no sample-* stubs)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "data" / "logos" / "verse_decoded_v2_single_anchor_v1.jsonl"
DEFAULT_OUT = ROOT / "data" / "logos" / "4lens_batch_real_verses_v1.json"
DEFAULT_VERSE_IDS = ("Ps.89.28", "Jer.31.33", "Prov.22.3")


def _normalize_seed_verse_id(raw: str) -> str:
    s = raw.strip()
    if "::" in s:
        s = s.split("::", 1)[1]
    return s


def _load_corpus_rows(corpus: Path, want: set[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    if not corpus.is_file() or not want:
        return found
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            vid = row.get("verse_id")
            if not isinstance(vid, str) or vid not in want or vid in found:
                continue
            found[vid] = row
            if len(found) >= len(want):
                break
    return found


def _batch_item(row: dict[str, Any]) -> dict[str, Any]:
    vid = str(row["verse_id"])
    v4 = row.get("vector_4d") or row.get("unified_4d_vector")
    if not isinstance(v4, dict):
        raise ValueError(f"missing vector_4d for {vid}")
    item: dict[str, Any] = {
        "verse_id": vid,
        "source_ref": row.get("source_ref"),
        "text": row.get("text"),
        "pipeline1_simple_4d": {
            "vector_4d": {k: float(v4[k]) for k in ("S", "L", "K", "M") if k in v4},
        },
    }
    return item


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit 4lens batch from corpus verse_ids.")
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--verse-ids",
        type=str,
        default=",".join(DEFAULT_VERSE_IDS),
        help="Comma-separated MKM verse_id list (e.g. Ps.89.28,Jer.31.33).",
    )
    ap.add_argument(
        "--from-gold-q01",
        action="store_true",
        help="Use q01 gold_verse_ids from logos_gold_query_eval_v1.json (first 3 found in corpus).",
    )
    args = ap.parse_args()

    if args.from_gold_q01:
        fixture = ROOT / "docs" / "final" / "fixtures" / "logos_gold_query_eval_v1.json"
        doc = json.loads(fixture.read_text(encoding="utf-8"))
        items = doc.get("items") if isinstance(doc.get("items"), list) else []
        q01 = next((x for x in items if isinstance(x, dict) and x.get("id") == "q01"), None)
        if not q01:
            print("gold fixture missing q01")
            return 2
        gids = q01.get("gold_verse_ids")
        if not isinstance(gids, list) or not gids:
            print("q01 has no gold_verse_ids")
            return 2
        verse_ids = [str(x).strip() for x in gids[:3]]
    else:
        verse_ids = [p.strip() for p in args.verse_ids.split(",") if p.strip()]

    want = set(verse_ids)
    rows = _load_corpus_rows(args.corpus, want)
    missing = [v for v in verse_ids if v not in rows]
    if missing:
        print(f"corpus missing verse_id(s): {', '.join(missing)}")
        return 2

    batch = [_batch_item(rows[v]) for v in verse_ids]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()} ({len(batch)} verses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
