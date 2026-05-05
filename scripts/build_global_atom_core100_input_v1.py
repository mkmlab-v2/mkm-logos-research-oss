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
    ap = argparse.ArgumentParser(description="Build core-100 mixed event input for global atom network PoC.")
    ap.add_argument("--seed-insight-json", default="docs/final/artifacts/bible_meaning_insight_candidates_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/global_atom_core100_input_latest.json")
    ap.add_argument("--target-count", type=int, default=100)
    args = ap.parse_args()

    sp = resolve(args.seed_insight_json)
    op = resolve(args.output_json)
    if not sp.is_file():
        raise SystemExit(f"missing seed insight json: {sp}")
    seed = load(sp)
    base_candidates = seed.get("candidates") if isinstance(seed.get("candidates"), list) else []
    if not base_candidates:
        raise SystemExit("no base candidates in seed insight json")

    regimes = ["creation_fall", "exodus_transition", "gospel_kingdom", "empire_transition"]
    prefixes = ["genesis", "exodus", "gospel", "aramaic"]
    out_candidates: list[dict[str, Any]] = []
    target = max(1, int(args.target_count))
    for i in range(target):
        b = base_candidates[i % len(base_candidates)]
        hub = float(b.get("hub_score", 0.6) or 0.6)
        path = float(b.get("path_score", 0.55) or 0.55)
        cluster = int(b.get("cluster_size", 6) or 6)
        # Introduce controlled spread for PoC diversity.
        hub_adj = max(0.35, min(0.95, hub - 0.12 + (0.03 * (i % 6))))
        path_adj = max(0.30, min(0.90, path - 0.10 + (0.02 * (i % 5))))
        cluster_adj = max(3, min(14, cluster - 2 + (i % 8)))

        reg = regimes[i % len(regimes)]
        pref = prefixes[i % len(prefixes)]
        out_candidates.append(
            {
                "candidate_id": f"core100_{i+1:03d}",
                "source_node_id": f"{pref}::event.{i+1:03d}",
                "hub_score": round(hub_adj, 6),
                "path_score": round(path_adj, 6),
                "cluster_size": cluster_adj,
                "regime_tag": reg,
            }
        )

    out = {
        "schema": "bible_meaning_insight_candidates_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "candidates": out_candidates,
        "meta": {
            "profile": "core100_mixed_events_poc",
            "target_count": target,
            "source_seed_json": str(sp),
        },
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

