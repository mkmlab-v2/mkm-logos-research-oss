#!/usr/bin/env python3
"""DF-P2-03: Map regime_map fingerprints to graph node regime_tags ([HYPO], NON_GATING)."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGIME = ROOT / "data/regimes/regime_map_btc_ext.json"
DEFAULT_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_graph_regime_highlight_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_regime_ids(path: Path) -> list[str]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    regimes = doc.get("regimes") or {}
    return sorted(str(k) for k in regimes.keys())


def _norm_tag(tag: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", tag.lower()).strip("_")


def _match_regime(tag: str, regime_ids: list[str]) -> str | None:
    t = _norm_tag(tag)
    if not t:
        return None
    for rid in regime_ids:
        r = _norm_tag(rid)
        if t == r or t in r or r in t:
            return rid
    return None


def _iter_nodes(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            rows.append(json.loads(s))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="DF-P2-03 regime highlight on meaning graph nodes.")
    ap.add_argument("--regime-map-json", type=Path, default=DEFAULT_REGIME)
    ap.add_argument("--nodes-jsonl", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--top-samples", type=int, default=12)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    regime_path = args.regime_map_json if args.regime_map_json.is_absolute() else ROOT / args.regime_map_json
    nodes_path = args.nodes_jsonl if args.nodes_jsonl.is_absolute() else ROOT / args.nodes_jsonl
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not regime_path.is_file():
        print(f"error: regime map not found: {regime_path}")
        return 2

    regime_ids = _load_regime_ids(regime_path)
    nodes = _iter_nodes(nodes_path)

    by_regime: dict[str, list[str]] = {rid: [] for rid in regime_ids}
    by_regime["_unmapped_observational"] = []
    counts: dict[str, int] = defaultdict(int)
    regime_projection_nodes = 0
    verse_nodes = 0

    for row in nodes:
        nid = str(row.get("node_id") or "")
        kind = str(row.get("kind") or "").lower()
        if nid.startswith("regime::") or kind == "regime":
            regime_projection_nodes += 1
            continue
        if row.get("ref") or row.get("corpus"):
            verse_nodes += 1
        tags = list(row.get("regime_tags") or [])
        if not tags:
            continue
        matched_regimes: set[str] = set()
        for tag in tags:
            rid = _match_regime(str(tag), regime_ids)
            if rid:
                matched_regimes.add(rid)
        if matched_regimes:
            for rid in matched_regimes:
                counts[rid] += 1
                if nid and len(by_regime[rid]) < int(args.top_samples):
                    by_regime[rid].append(nid)
        elif nid:
            counts["_unmapped_observational"] += 1
            if len(by_regime["_unmapped_observational"]) < int(args.top_samples):
                by_regime["_unmapped_observational"].append(nid)

    doc = {
        "schema": "logos_graph_regime_highlight_v1",
        "df_mission_id": "DF-P2-03",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "gating_status": "NON_GATING",
        "no_trading_trigger": True,
        "primary_regime_authority": "regime_map is observational overlay only; 1차 실물 regime_map (IMF/lehman 등) is separate SSOT for Track A.",
        "inputs": {
            "regime_map_json": str(regime_path.resolve()).replace("\\", "/"),
            "nodes_jsonl": str(nodes_path.resolve()).replace("\\", "/"),
            "regime_ids": regime_ids,
        },
        "graph_stats": {
            "nodes_total": len(nodes),
            "verse_like_nodes": verse_nodes,
            "regime_projection_nodes": regime_projection_nodes,
        },
        "highlight_counts_by_regime": counts,
        "sample_node_ids_by_regime": {k: v for k, v in by_regime.items() if v},
        "track_wall": {
            "non_gating": True,
            "no_trade_signals": True,
            "not_track_a_trigger": True,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
