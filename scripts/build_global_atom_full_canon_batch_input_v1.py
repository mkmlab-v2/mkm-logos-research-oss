#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build staged full-canon batch input from seed insight candidates.")
    ap.add_argument("--seed-insight-json", default="docs/final/artifacts/bible_meaning_insight_candidates_latest.json")
    ap.add_argument("--stage", required=True, choices=["genesis", "torah", "prophets", "gospels", "full_canon"])
    ap.add_argument("--target-count", type=int, required=True)
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()

    sp = resolve(args.seed_insight_json)
    op = resolve(args.output_json)
    if not sp.is_file():
        raise SystemExit(f"missing seed insight json: {sp}")

    seed = load(sp)
    base_candidates = seed.get("candidates") if isinstance(seed.get("candidates"), list) else []
    if not base_candidates:
        raise SystemExit("no base candidates in seed insight json")

    stage_buckets = {
        "genesis": ["genesis"],
        "torah": ["genesis", "exodus", "leviticus", "numbers", "deuteronomy"],
        "prophets": ["isaiah", "jeremiah", "ezekiel", "daniel", "minor_prophets"],
        "gospels": ["matthew", "mark", "luke", "john"],
        "full_canon": ["genesis", "torah", "history", "wisdom", "prophets", "gospels", "acts", "epistles", "revelation", "aramaic"],
    }
    regime_map = {
        "genesis": "creation_fall",
        "torah": "covenant_transition",
        "prophets": "empire_transition",
        "gospels": "kingdom_transition",
        "full_canon": "full_canon_transition",
    }
    book_tags = stage_buckets[args.stage]
    target = max(1, int(args.target_count))

    out_candidates: list[dict[str, Any]] = []
    for i in range(target):
        b = base_candidates[i % len(base_candidates)]
        hub = float(b.get("hub_score", 0.60) or 0.60)
        path = float(b.get("path_score", 0.55) or 0.55)
        cluster = int(b.get("cluster_size", 6) or 6)

        # Deterministic spread for stage-level diversity.
        hub_adj = max(0.30, min(0.98, hub - 0.15 + (0.01 * (i % 15))))
        path_adj = max(0.25, min(0.95, path - 0.12 + (0.015 * (i % 12))))
        cluster_adj = max(2, min(24, cluster - 2 + (i % 10)))
        book = book_tags[i % len(book_tags)]
        out_candidates.append(
            {
                "candidate_id": f"{args.stage}_{i+1:05d}",
                "source_node_id": f"{book}::event.{i+1:05d}",
                "hub_score": round(hub_adj, 6),
                "path_score": round(path_adj, 6),
                "cluster_size": cluster_adj,
                "regime_tag": regime_map[args.stage],
                "stage": args.stage,
            }
        )

    out = {
        "schema": "bible_meaning_insight_candidates_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "candidates": out_candidates,
        "meta": {
            "profile": "global_atom_full_canon_batch_input_v1",
            "stage": args.stage,
            "target_count": target,
            "seed_count": len(base_candidates),
            "source_seed_json": str(sp),
            "note": "Stage bootstrap input; replace with verse-level extraction for production full-canon.",
        },
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

