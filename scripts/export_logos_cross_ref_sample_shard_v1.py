#!/usr/bin/env python3
"""Export Tier-A synoptic passion cross-ref sample shard for Logos Studio [HYPO].

NOT full TSK 63,779 — honest Tier A seed only (edge_budget_max 500).

Reproducible:
  py scripts/export_logos_cross_ref_sample_shard_v1.py
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json"
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/logos_cross_ref_sample_shard_v1_latest.json"
DEFAULT_OUT_STUDIO = (
    ROOT / "projects/no1kmedi/public/data/logos_studio/cross_ref_sample_shard_v1.json"
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_export(src_path: Path) -> dict[str, Any]:
    doc = json.loads(src_path.read_text(encoding="utf-8"))
    edges = doc.get("edges") if isinstance(doc.get("edges"), list) else []
    return {
        "schema": "logos_cross_ref_sample_shard_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_tier": "B",
        "tier": "A",
        "slice_id": doc.get("slice_id") or "SYNOPTIC_PASSION_WEEK_v1",
        "edge_count": len(edges),
        "edge_budget_max": int(doc.get("edge_budget_max") or 500),
        "source_fixture": str(src_path.relative_to(ROOT)).replace("\\", "/"),
        "provenance_ref": doc.get("provenance_ref"),
        "honesty": {
            "tsk_63779_loaded": False,
            "note_ko": "샘플 병렬 구절 샤드(~142 edges). TSK 전량 교차참조는 Tier C 로드맵.",
            "build_logos_63779_registry_is_pattern_registry": True,
        },
        "edges": edges,
        "reproduce": "py scripts/export_logos_cross_ref_sample_shard_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument("--out-studio", type=Path, default=DEFAULT_OUT_STUDIO)
    ap.add_argument("--skip-studio", action="store_true")
    args = ap.parse_args()
    if not args.src.is_file():
        print(f"missing src: {args.src}", file=sys.stderr)
        return 1
    doc = build_export(args.src)
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out_artifact} edges={doc['edge_count']}")
    if not args.skip_studio:
        args.out_studio.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.out_artifact, args.out_studio)
        print(f"copied studio {args.out_studio}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
