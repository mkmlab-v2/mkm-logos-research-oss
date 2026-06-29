#!/usr/bin/env python3
"""Merge themed GraphRAG router paths into distill graph_paths (no LLM)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

ART = ROOT / "docs/final/artifacts"
VERSE_STEP_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.\d+\.\d+$")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _verse_ids_from_steps(steps: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for step in steps:
        raw = str(step or "").strip()
        if not raw:
            continue
        if raw.startswith("vr_"):
            continue
        cand = canonical_verse_ref(raw)
        if cand and VERSE_STEP_RE.match(cand) and cand not in seen:
            seen.add(cand)
            out.append(cand)
    return out


def router_paths_to_graph_paths(router: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, path in enumerate(router.get("paths") or []):
        if not isinstance(path, dict):
            continue
        steps = path.get("steps") or []
        verse_ids = _verse_ids_from_steps(steps)
        if not verse_ids:
            continue
        pid = str(path.get("path_id") or f"gr_router_{i + 1:03d}")
        score = path.get("match_score")
        try:
            weight = min(1.0, float(score) / 10.0) if score is not None else 0.8
        except (TypeError, ValueError):
            weight = 0.8
        rows.append(
            {
                "path_id": pid,
                "edge_type": "graphrag_router_path",
                "verse_ids": verse_ids,
                "steps": steps,
                "bridge_artifact": path.get("bridge_artifact"),
                "note_ko": path.get("note_ko"),
                "weight": round(weight, 4),
                "confidence": 0.75,
                "relation_basis": ["themed_graphrag_router"],
                "hypothesis_tier": "B",
                "research_only": True,
                "source": "logos_subgraph_graphrag_router",
            }
        )
    return rows


def merge_graph_paths(existing: list[dict[str, Any]], router_paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in router_paths + existing:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("path_id") or "")
        if pid and pid in seen:
            continue
        if pid:
            seen.add(pid)
        out.append(row)
    return out


def sync_theme(theme_id: str, *, in_place_locked: bool) -> dict[str, Any]:
    router_path = ART / f"logos_subgraph_graphrag_router_{theme_id}_latest.json"
    router = _load(router_path)
    if not router:
        raise SystemExit(f"missing router: {router_path}")

    router_paths = router_paths_to_graph_paths(router)
    targets = [
        ART / f"logos_deep_research_distill_{theme_id}_latest.json",
        ART / f"logos_deep_research_distill_{theme_id}_citation_lock_latest.json",
    ]
    if not in_place_locked:
        targets = [ART / f"logos_deep_research_distill_{theme_id}_latest.json"]

    updated: list[str] = []
    for distill_path in targets:
        if not distill_path.is_file():
            continue
        distill = _load(distill_path) or {}
        merged = merge_graph_paths(list(distill.get("graph_paths") or []), router_paths)
        distill["graph_paths"] = merged
        prov = dict(distill.get("provenance") or {})
        prov["themed_router_graph_paths_sync"] = {
            "ts_utc": _utc(),
            "router_ref": str(router_path.relative_to(ROOT)).replace("\\", "/"),
            "router_path_count": len(router_paths),
            "graph_paths_total": len(merged),
        }
        distill["provenance"] = prov
        distill_path.write_text(json.dumps(distill, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        updated.append(str(distill_path.relative_to(ROOT)).replace("\\", "/"))

    return {
        "theme_id": theme_id,
        "router_paths": len(router_paths),
        "updated": updated,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--themes", default="dan_aramaic,john_1_logos")
    ap.add_argument("--locked-only", action="store_true", help="Update citation_lock distill only")
    args = ap.parse_args()

    results: list[dict[str, Any]] = []
    for theme_id in [t.strip() for t in args.themes.split(",") if t.strip()]:
        results.append(sync_theme(theme_id, in_place_locked=not args.locked_only))

    ok = all(r.get("router_paths", 0) >= 1 and r.get("updated") for r in results)
    doc = {
        "schema": "logos_themed_router_graph_paths_sync_v1",
        "generated_at_utc": _utc(),
        "themes": results,
        "ok": ok,
        "reproduce": "py scripts/sync_logos_themed_router_graph_paths_v1.py",
    }
    out = ROOT / "reports/logos_themed_router_graph_paths_sync_v1_latest.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "themes": results, "out": str(out.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
