#!/usr/bin/env python3
"""Report LTM concept coordinates vs MKM12 prism registry path gaps ([HYPO] / B-track).

Read-only — does not edit CONCEPT_SPECS.

  py scripts/report_ltm_prism_id_gaps_v1.py
  py scripts/report_ltm_prism_id_gaps_v1.py --out reports/ltm_prism_id_gaps_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_long_term_memory_graph_lib_v1 import (  # noqa: E402
    CONCEPT_SPECS,
    DEFAULT_PRISM_REGISTRY,
    load_prism_registry,
)


def _norm(rel: str) -> str:
    return PurePosixPath(rel.replace("\\", "/")).as_posix()


def _prism_by_path(registry: dict[str, dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pid, entry in registry.items():
        path = entry.get("path")
        if path:
            out[_norm(str(path))] = pid
    return out


def build_report(root: Path) -> dict[str, Any]:
    registry = load_prism_registry(root / DEFAULT_PRISM_REGISTRY.relative_to(SCRIPT_ROOT))
    by_path = _prism_by_path(registry)
    suggestions: list[dict[str, Any]] = []
    missing_prism: list[str] = []
    matched: list[str] = []

    for spec in CONCEPT_SPECS:
        has_prism = False
        for coord in spec.coordinates:
            rel = _norm(coord.file_path)
            if coord.prism_id:
                has_prism = True
                matched.append(spec.concept_id)
                break
            pid = by_path.get(rel)
            if pid:
                suggestions.append(
                    {
                        "concept_id": spec.concept_id,
                        "file_path": rel,
                        "suggested_prism_id": pid,
                        "prism_axis": registry[pid].get("prism_axis"),
                    }
                )
                break
        if not has_prism and not any(
            s["concept_id"] == spec.concept_id for s in suggestions
        ):
            missing_prism.append(spec.concept_id)

    return {
        "schema": "ltm_prism_id_gaps_v1",
        "track": "B",
        "research_only": True,
        "registry_path": str(DEFAULT_PRISM_REGISTRY.relative_to(SCRIPT_ROOT)).replace(
            "\\", "/"
        ),
        "concept_count": len(CONCEPT_SPECS),
        "registry_entry_count": len(registry),
        "concepts_with_explicit_prism_id": len(matched),
        "path_match_suggestions": suggestions,
        "concepts_without_prism_or_path_match": missing_prism,
        "boundary_ack": "[HYPO] suggestions only — manual CONCEPT_SPECS edit required",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument(
        "--out",
        type=Path,
        default=SCRIPT_ROOT / "reports" / "ltm_prism_id_gaps_v1_latest.json",
    )
    args = ap.parse_args()
    root = args.workspace_root.resolve()
    doc = build_report(root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"suggestions={len(doc['path_match_suggestions'])} "
        f"without_match={len(doc['concepts_without_prism_or_path_match'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
