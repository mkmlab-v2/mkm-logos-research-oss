#!/usr/bin/env python3
"""Logos Studio preset expansion chain: 17 → 50 + BigSet anchors (Phase A).

Reproduce:
  py scripts/run_logos_studio_preset_expansion_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
TARGET = 50


def _run(label: str, cmd: list[str]) -> int:
    print(f"[chain] {label}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        print(f"[chain] FAIL {label} exit={proc.returncode}", file=sys.stderr)
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-count", type=int, default=TARGET)
    ap.add_argument("--skip-build-base", action="store_true")
    ap.add_argument("--skip-sync-public", action="store_true")
    args = ap.parse_args()

    steps: list[tuple[str, list[str]]] = []
    if not args.skip_build_base:
        steps.append(
            (
                "build_base_presets",
                [PY, "scripts/build_showroom_meaning_topology_qa_presets_v1.py"],
            )
        )
    steps.extend(
        [
            (
                "merge_bigset_topics",
                [PY, "scripts/merge_logos_studio_bigset_topic_presets_v1.py"],
            ),
            (
                "merge_graph_chapters",
                [
                    PY,
                    "scripts/merge_logos_studio_graph_chapter_presets_v1.py",
                    "--target-count",
                    str(args.target_count),
                ],
            ),
            (
                "attach_reasoning_paths",
                [
                    PY,
                    "scripts/compute_logos_reasoning_path_v1.py",
                    "--presets-json",
                    "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json",
                    "--graph-json",
                    "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json",
                ],
            ),
            (
                "export_router_sidecar",
                [PY, "scripts/export_showroom_qa_router_paths_v1.py"],
            ),
            (
                "build_taxonomy",
                [PY, "scripts/build_logos_studio_preset_taxonomy_v1.py"],
            ),
            (
                "build_semantic_lexical_index",
                [PY, "scripts/build_logos_studio_semantic_router_lexical_index_v1.py"],
            ),
            (
                "build_semantic_embedding_index",
                [PY, "scripts/build_logos_studio_semantic_router_embedding_index_v1.py"],
            ),
        ]
    )

    for label, cmd in steps:
        if _run(label, cmd) != 0:
            return 1

    if not args.skip_sync_public:
        sync = subprocess.run(
            ["node", "projects/no1kmedi/scripts/sync-logos-studio-data.mjs"],
            cwd=ROOT,
        )
        if sync.returncode != 0:
            return sync.returncode

    presets_path = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
    tax_path = ROOT / "docs/final/artifacts/logos_studio_preset_taxonomy_v1_latest.json"
    presets_doc = json.loads(presets_path.read_text(encoding="utf-8-sig"))
    tax_doc = json.loads(tax_path.read_text(encoding="utf-8-sig"))
    count = len(presets_doc.get("presets") or [])
    bigset_ids = [
        p["id"]
        for p in presets_doc.get("presets") or []
        if str(p.get("id", "")).startswith("bigset_topic_")
    ]
    summary = {
        "ok": count >= args.target_count,
        "preset_count": count,
        "target_count": args.target_count,
        "taxonomy_preset_count": tax_doc.get("preset_count"),
        "bigset_topic_ids": bigset_ids,
        "artifacts": {
            "presets": str(presets_path),
            "taxonomy": str(tax_path),
        },
    }
    out = ROOT / "docs/final/artifacts/logos_studio_preset_expansion_chain_v1_latest.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
