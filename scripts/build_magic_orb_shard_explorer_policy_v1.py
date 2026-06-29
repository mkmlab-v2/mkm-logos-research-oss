#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build magic_orb_shard_explorer_policy_v1 — Phase 6 explorer limits + slice eligibility ([HYPO])."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRILL_INDEX = ROOT / "docs/final/artifacts/magic_orb_drilldown_shards_v1_latest.json"
DEFAULT_SHARD_DIR = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_drilldown_shard"
DEFAULT_OUT = ROOT / "docs/final/artifacts/magic_orb_shard_explorer_policy_v1_latest.json"
MKMLIFE_OUT = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_shard_explorer_policy_v1.json"
DRILL_BUILDER = ROOT / "scripts/build_magic_orb_drilldown_shard_bundle_v1.py"

SCHEMA = "magic_orb_shard_explorer_policy_v1"
VERSION = "1.0.0"
MIN_EDGES = 40
MAX_NODES = 160
MAX_EDGES = 200


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_drill_builder():
    spec = importlib.util.spec_from_file_location("build_magic_orb_drilldown_shard_bundle_v1", DRILL_BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _passion_ref_to_node_id(ref: str) -> str:
    return f"synoptic::{ref.replace(' ', '').upper()}"


def _infer_ref(node_id: str) -> str | None:
    if "::" not in node_id:
        return node_id.upper() if "." in node_id else None
    tail = node_id.split("::")[-1]
    return tail if "." in tail else None


def sidecar_to_explorer_stats(sidecar: dict[str, Any]) -> dict[str, Any]:
    edges_in = sidecar.get("edges") or []
    if not edges_in:
        return {"node_count": 0, "edge_count": 0, "eligible": False}

    nodes: set[str] = set()
    edges = 0
    is_passion = bool(edges_in[0].get("src_ref"))

    for row in edges_in:
        if is_passion:
            src = _passion_ref_to_node_id(str(row.get("src_ref") or ""))
            dst = _passion_ref_to_node_id(str(row.get("dst_ref") or ""))
        else:
            src = str(row.get("src") or "")
            dst = str(row.get("dst") or "")
        if not src or not dst:
            continue
        nodes.add(src)
        nodes.add(dst)
        edges += 1

    verse_count = sum(1 for n in nodes if _infer_ref(n))
    return {
        "node_count": len(nodes),
        "edge_count": edges,
        "verse_nodes": verse_count,
        "eligible": edges >= MIN_EDGES and len(nodes) <= MAX_NODES and edges <= MAX_EDGES,
    }


def build_policy(
    *,
    drill_index_path: Path = DEFAULT_DRILL_INDEX,
    shard_dir: Path = DEFAULT_SHARD_DIR,
) -> dict[str, Any]:
    index = _load_json(drill_index_path) if drill_index_path.is_file() else {"slices": []}
    slices_out: list[dict[str, Any]] = []

    for entry in index.get("slices") or []:
        slice_id = str(entry.get("slice_id") or "")
        sidecar_path = shard_dir / f"{slice_id}.json"
        if not sidecar_path.is_file():
            alt = ROOT / "docs/final/artifacts" / f"magic_orb_drilldown_shard_{slice_id}.json"
            sidecar = _load_json(alt) if alt.is_file() else {}
        else:
            sidecar = _load_json(sidecar_path)

        stats = sidecar_to_explorer_stats(sidecar)
        summary = entry.get("summary") or {}
        slices_out.append(
            {
                "slice_id": slice_id,
                "sidecar_url": entry.get("sidecar_url"),
                "source_kind": entry.get("source_kind"),
                "explorer_eligible": stats["eligible"],
                "explorer_stats": stats,
                "drilldown_summary": summary,
            }
        )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "limits": {
            "min_edges": MIN_EDGES,
            "max_nodes": MAX_NODES,
            "max_edges": MAX_EDGES,
            "canvas_size_px": 340,
        },
        "disclaimer_ko": (
            "전체 샤드 탐색기 [HYPO][NON_GATING] — 연구용 관측 망입니다. "
            "신학·예언 확정·실매매·Track A 근거가 아닙니다."
        ),
        "slices": slices_out,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drill-index", type=Path, default=DEFAULT_DRILL_INDEX)
    ap.add_argument("--shard-dir", type=Path, default=DEFAULT_SHARD_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sync-mkmlife", action="store_true")
    args = ap.parse_args()

    if not args.drill_index.is_file():
        print(json.dumps({"ok": False, "error": f"drill_index_missing:{args.drill_index}"}))
        return 2

    doc = build_policy(drill_index_path=args.drill_index, shard_dir=args.shard_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    written = [str(args.out.relative_to(ROOT)).replace("\\", "/")]
    if args.sync_mkmlife:
        MKMLIFE_OUT.parent.mkdir(parents=True, exist_ok=True)
        MKMLIFE_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(str(MKMLIFE_OUT.relative_to(ROOT)).replace("\\", "/"))

    eligible = [s for s in doc["slices"] if s.get("explorer_eligible")]
    print(
        json.dumps(
            {
                "ok": True,
                "eligible_slices": len(eligible),
                "slices": [
                    {
                        "slice_id": s["slice_id"],
                        "nodes": s["explorer_stats"]["node_count"],
                        "edges": s["explorer_stats"]["edge_count"],
                    }
                    for s in doc["slices"]
                ],
                "written": written,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
