#!/usr/bin/env python3
"""Build 1-hop OpenBible xref subgraph for Logos Track B themed anchors."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref
from scripts.parse_external_baseline_v1 import expand_ref, load_external_rows

THEME_PRESETS = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
DEFAULT_OPENBIBLE = ROOT / "docs/final/artifacts/external_cross_references_openbible/cross_references.txt"
DEFAULT_OUT_JSONL = ROOT / "docs/final/artifacts/logos_themed_xref_edges_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "reports/logos_themed_xref_subgraph_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _theme_anchor_ids(presets: dict[str, Any], theme_id: str) -> set[str]:
    themes = presets.get("themes") or {}
    theme = themes.get(theme_id) if isinstance(themes, dict) else None
    if not isinstance(theme, dict):
        return set()
    prefix = str(theme.get("verse_prefix") or "")
    distill_path = ROOT / f"docs/final/artifacts/logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
    distill = _load_json(distill_path)
    ids: set[str] = set()
    if distill:
        for ref in distill.get("evidence_refs") or []:
            if isinstance(ref, dict) and ref.get("verse_id"):
                vid = canonical_verse_ref(str(ref["verse_id"]))
                if vid and (not prefix or vid.startswith(prefix) or _alias_ids(vid, prefix)):
                    ids.add(vid)
    return ids


def _alias_ids(vid: str, prefix: str) -> bool:
    """Match Jhn.* anchors against John.* theme prefix."""
    if prefix.startswith("Jhn.") and vid.startswith("John."):
        return vid.replace("John.", "Jhn.", 1).startswith(prefix)
    if prefix.startswith("John.") and vid.startswith("Jhn."):
        return vid.replace("Jhn.", "John.", 1).startswith(prefix)
    return False


def _lookup_aliases(vid: str) -> set[str]:
    out = {vid, canonical_verse_ref(vid)}
    if vid.startswith("Jhn."):
        out.add("John." + vid[4:])
    elif vid.startswith("John."):
        out.add("Jhn." + vid[5:])
    return {x for x in out if x}


def build_xref_edges(
    *,
    openbible_path: Path,
    anchor_ids: set[str],
    theme_id: str,
    max_edges: int,
    min_votes: int,
) -> list[dict[str, Any]]:
    lookup: set[str] = set()
    for vid in anchor_ids:
        lookup.update(_lookup_aliases(vid))

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in load_external_rows(openbible_path):
        try:
            votes = int(str(row.get("votes") or row.get("Votes") or "0").strip() or "0")
        except ValueError:
            votes = 0
        if votes < min_votes:
            continue
        src_field = row.get("source_ref") or row.get("From Verse") or ""
        dst_field = row.get("target_ref") or row.get("To Verse") or ""
        srcs = expand_ref(str(src_field), "start")
        dsts = expand_ref(str(dst_field), "start")
        for src in srcs:
            src_c = canonical_verse_ref(src)
            for dst in dsts:
                dst_c = canonical_verse_ref(dst)
                if not src_c or not dst_c:
                    continue
                if src in lookup or src_c in lookup:
                    key = (src_c, dst_c)
                    if key in seen or src_c == dst_c:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "schema": "logos_themed_xref_edge_v1",
                            "src_verse_id": src_c,
                            "dst_verse_id": dst_c,
                            "edge_type": "XREF_1HOP_OPENBIBLE",
                            "votes": votes,
                            "direction": "outbound",
                            "theme_id": theme_id,
                            "hypothesis_tier": "B",
                            "research_only": True,
                            "source": "openbible_cross_references",
                        }
                    )
                if dst in lookup or dst_c in lookup:
                    key = (dst_c, src_c)
                    if key in seen or dst_c == src_c:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "schema": "logos_themed_xref_edge_v1",
                            "src_verse_id": dst_c,
                            "dst_verse_id": src_c,
                            "edge_type": "XREF_1HOP_OPENBIBLE",
                            "votes": votes,
                            "direction": "inbound",
                            "theme_id": theme_id,
                            "hypothesis_tier": "B",
                            "research_only": True,
                            "source": "openbible_cross_references",
                        }
                    )
                if len(rows) >= max_edges:
                    return rows
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--themes", default="dan_aramaic,john_1_logos")
    ap.add_argument("--openbible", type=Path, default=DEFAULT_OPENBIBLE)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--max-edges-per-theme", type=int, default=500)
    ap.add_argument("--min-votes", type=int, default=10)
    args = ap.parse_args()

    if not args.openbible.is_file():
        raise SystemExit(f"missing openbible: {args.openbible}")

    presets = _load_json(THEME_PRESETS)
    if not presets:
        raise SystemExit(f"missing presets: {THEME_PRESETS}")

    all_rows: list[dict[str, Any]] = []
    per_theme: dict[str, Any] = {}
    for theme_id in [t.strip() for t in args.themes.split(",") if t.strip()]:
        anchors = _theme_anchor_ids(presets, theme_id)
        edges = build_xref_edges(
            openbible_path=args.openbible,
            anchor_ids=anchors,
            theme_id=theme_id,
            max_edges=args.max_edges_per_theme,
            min_votes=args.min_votes,
        )
        all_rows.extend(edges)
        neighbor_ids = {e["dst_verse_id"] for e in edges}
        per_theme[theme_id] = {
            "anchor_count": len(anchors),
            "xref_edges": len(edges),
            "unique_neighbors": len(neighbor_ids),
        }

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_rows) + ("\n" if all_rows else ""),
        encoding="utf-8",
    )

    doc = {
        "schema": "logos_themed_xref_subgraph_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "openbible_source": str(args.openbible.relative_to(ROOT)).replace("\\", "/"),
        "themes": per_theme,
        "total_edges": len(all_rows),
        "hop": 1,
        "reproduce": "py scripts/build_logos_themed_xref_subgraph_v1.py",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = len(all_rows) >= 20
    print(json.dumps({"ok": ok, "total_edges": len(all_rows), "themes": per_theme}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
