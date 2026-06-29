#!/usr/bin/env python3
"""Merge base concept_bridge registry with themed anchor bridge entries."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
BASE_REGISTRY = ART / "logos_concept_bridge_registry_v1_latest.json"
DEFAULT_OUT = ART / "logos_concept_bridge_registry_themed_v1_latest.json"
THEMES = ("dan_aramaic", "john_1_logos")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _entry_for_bridge(rel_path: str, bridge: dict[str, Any]) -> dict[str, Any]:
    q = bridge.get("query") if isinstance(bridge.get("query"), dict) else {}
    pol = bridge.get("policy") if isinstance(bridge.get("policy"), dict) else {}
    return {
        "artifact_path": rel_path,
        "present": True,
        "concept_id": str(q.get("concept_id") or ""),
        "label_ko": str(q.get("label_ko") or ""),
        "path_count": len(bridge.get("paths") or []),
        "generation_method": str(pol.get("generation_method") or "themed_distill_anchor_wiring_v1"),
        "human_reviewed": bool(pol.get("human_reviewed")),
        "theme_id": pol.get("theme_id"),
    }


def merge_registry(*, themes: tuple[str, ...] = THEMES) -> dict[str, Any]:
    base = _load(BASE_REGISTRY) or {"schema": "logos_concept_bridge_registry_v1", "entries": []}
    doc = deepcopy(base)
    entries = list(doc.get("entries") or [])
    existing = {str(e.get("artifact_path") or "") for e in entries if isinstance(e, dict)}

    themed_added = 0
    for theme_id in themes:
        rel = f"docs/final/artifacts/logos_concept_bridge_themed_{theme_id}_v1_latest.json"
        if rel in existing:
            continue
        bridge = _load(ROOT / rel.replace("/", "\\"))
        if not bridge:
            continue
        entries.append(_entry_for_bridge(rel, bridge))
        themed_added += 1

    doc["entries"] = entries
    doc["bridge_count"] = len(entries)
    doc["themed_overlay"] = {
        "schema": "logos_concept_bridge_registry_themed_overlay_v1",
        "generated_at_utc": _utc(),
        "themes": list(themes),
        "themed_entries_added": themed_added,
        "base_registry": str(BASE_REGISTRY.relative_to(ROOT)).replace("\\", "/"),
    }
    doc["generated_at_utc"] = _utc()
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--themes", default=",".join(THEMES))
    args = ap.parse_args()

    themes = tuple(t.strip() for t in args.themes.split(",") if t.strip())
    doc = merge_registry(themes=themes)
    themed_added = (doc.get("themed_overlay") or {}).get("themed_entries_added", 0)
    if themed_added < 1:
        raise SystemExit("no themed bridges merged — run build_logos_themed_anchor_concept_bridge_v1.py first")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "themed_entries_added": themed_added,
                "bridge_count": doc.get("bridge_count"),
                "out": str(args.out.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
