#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build magic_orb_chronology_shard_highlight_v1 — era verse_refs → display/shard node ids (Phase 7)."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HERO = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"
DEFAULT_SHARD_DIR = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_drilldown_shard"
DEFAULT_OUT = ROOT / "docs/final/artifacts/magic_orb_chronology_shard_highlight_v1_latest.json"
MKMLIFE_OUT = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_chronology_shard_highlight_v1.json"
EXPLORER_POLICY = ROOT / "scripts/build_magic_orb_shard_explorer_policy_v1.py"

SCHEMA = "magic_orb_chronology_shard_highlight_v1"
VERSION = "1.0.0"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _normalize_ref(raw: str) -> str:
    t = str(raw or "").strip()
    if "::" in t:
        t = t.split("::")[-1]
    return t.replace(" ", "").upper()


def _node_matches(node: dict[str, Any], verse_ref: str) -> bool:
    target = _normalize_ref(verse_ref)
    ref = str(node.get("ref") or "")
    if ref and _normalize_ref(ref) == target:
        return True
    nid = str(node.get("id") or "")
    if nid and _normalize_ref(nid) == target:
        return True
    if "::" in nid:
        tail = _normalize_ref(nid.split("::")[-1])
        if tail == target:
            return True
    return False


def _sidecar_nodes(sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    edges_in = sidecar.get("edges") or []
    if not edges_in:
        return []
    nodes: dict[str, dict[str, Any]] = {}
    is_passion = bool(edges_in[0].get("src_ref"))

    def _add(node_id: str, ref: str | None = None) -> None:
        if not node_id or node_id in nodes:
            return
        kind = "query" if node_id == "query::center" else "verse"
        if node_id.startswith("theme::"):
            kind = "theme"
        elif node_id.startswith("regime::"):
            kind = "regime"
        elif "::" in node_id or (ref and "." in ref):
            kind = "verse"
        nodes[node_id] = {
            "id": node_id,
            "ref": ref or (node_id.split("::")[-1] if "::" in node_id else None),
            "kind": kind,
        }

    for row in edges_in:
        if is_passion:
            src_ref = str(row.get("src_ref") or "")
            dst_ref = str(row.get("dst_ref") or "")
            src = f"synoptic::{src_ref.replace(' ', '').upper()}"
            dst = f"synoptic::{dst_ref.replace(' ', '').upper()}"
            _add(src, src_ref.upper())
            _add(dst, dst_ref.upper())
        else:
            src = str(row.get("src") or "")
            dst = str(row.get("dst") or "")
            _add(src)
            _add(dst)
    return list(nodes.values())


def _match_refs(verse_refs: list[str], nodes: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    hits: list[str] = []
    missed: list[str] = []
    for ref in verse_refs:
        matched = [n["id"] for n in nodes if _node_matches(n, ref)]
        if matched:
            hits.extend(matched)
        else:
            missed.append(ref)
    return sorted(set(hits)), missed


def build_highlight_map(
    *,
    hero_path: Path = DEFAULT_HERO,
    shard_dir: Path = DEFAULT_SHARD_DIR,
) -> dict[str, Any]:
    hero = _load_json(hero_path)
    eras = hero.get("chronology", {}).get("eras") or []
    slices = hero.get("slices") or []
    entries: list[dict[str, Any]] = []

    for era in eras:
        if not isinstance(era, dict):
            continue
        era_id = str(era.get("era_id") or "")
        if not era_id:
            continue
        verse_refs = list(era.get("verse_refs") or [])

        for sl in slices:
            slice_id = str(sl.get("slice_id") or "")
            if not slice_id:
                continue
            display_nodes = list((sl.get("graph_bloom") or {}).get("nodes") or [])
            display_hits, display_missed = _match_refs(verse_refs, display_nodes)

            shard_path = shard_dir / f"{slice_id}.json"
            shard_hits: list[str] = []
            shard_missed = list(verse_refs)
            shard_edge_count = 0
            if shard_path.is_file():
                sidecar = _load_json(shard_path)
                shard_nodes = _sidecar_nodes(sidecar)
                shard_hits, shard_missed = _match_refs(verse_refs, shard_nodes)
                shard_edge_count = len(sidecar.get("edges") or [])

            entries.append(
                {
                    "era_id": era_id,
                    "slice_id": slice_id,
                    "hint_slice_id": era.get("hint_slice_id"),
                    "verse_ref_count": len(verse_refs),
                    "display_node_ids": display_hits,
                    "shard_node_ids": shard_hits,
                    "display_hit_count": len(display_hits),
                    "shard_hit_count": len(shard_hits),
                    "verse_refs_missed_display": display_missed,
                    "verse_refs_missed_shard": shard_missed,
                    "shard_only_extra_hits": max(0, len(shard_hits) - len(display_hits)),
                    "shard_edge_count": shard_edge_count,
                }
            )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "disclaimer_ko": (
            "연대기→샤드 하이라이트 [HYPO][NON_GATING] — Logos Observatory 연구용 오버레이입니다. "
            "신학·예언 확정·실매매·Track A 근거가 아닙니다."
        ),
        "entries": entries,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hero", type=Path, default=DEFAULT_HERO)
    ap.add_argument("--shard-dir", type=Path, default=DEFAULT_SHARD_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sync-mkmlife", action="store_true")
    args = ap.parse_args()

    if not args.hero.is_file():
        print(json.dumps({"ok": False, "error": f"hero_missing:{args.hero}"}))
        return 2

    doc = build_highlight_map(hero_path=args.hero, shard_dir=args.shard_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    written = [str(args.out.relative_to(ROOT)).replace("\\", "/")]
    if args.sync_mkmlife:
        MKMLIFE_OUT.parent.mkdir(parents=True, exist_ok=True)
        MKMLIFE_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(str(MKMLIFE_OUT.relative_to(ROOT)).replace("\\", "/"))

    sample = [
        {
            "era_id": e["era_id"],
            "slice_id": e["slice_id"],
            "display_hits": e["display_hit_count"],
            "shard_hits": e["shard_hit_count"],
        }
        for e in doc["entries"]
        if e["display_hit_count"] or e["shard_hit_count"]
    ][:6]
    print(json.dumps({"ok": True, "entries": len(doc["entries"]), "sample": sample, "written": written}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
