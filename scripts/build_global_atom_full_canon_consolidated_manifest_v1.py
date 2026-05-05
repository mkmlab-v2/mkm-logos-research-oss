#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts" / "global_atom_full_canon"
STAGES = ["genesis", "torah", "prophets", "gospels", "full_canon"]
TARGETS = {"genesis": 512, "torah": 2048, "prophets": 3072, "gospels": 2048, "full_canon": 4096}
MINSIM = {"genesis": 0.70, "torah": 0.71, "prophets": 0.73, "gospels": 0.72, "full_canon": 0.75}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pick_latest(stage: str, suffix: str) -> Path:
    pattern = f"*_{stage}_{suffix}"
    cands = sorted(ART.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        raise SystemExit(f"missing artifact for stage={stage}, suffix={suffix}")
    return cands[0]


def detect_source_mode(example_input_json: Path) -> tuple[bool, bool]:
    try:
        doc = json.loads(example_input_json.read_text(encoding="utf-8-sig"))
        meta = doc.get("meta") if isinstance(doc, dict) else {}
        profile = str((meta or {}).get("profile", "")).lower()
        if "event_ingest" in profile:
            return False, True
        if "verse_ingest" in profile:
            return True, False
    except Exception:
        pass
    return True, False


def main() -> int:
    ap = argparse.ArgumentParser(description="Build consolidated 5-stage manifest from latest stage artifacts.")
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/global_atom_full_canon/global_atom_full_canon_consolidated_manifest_latest.json",
    )
    args = ap.parse_args()

    stages: list[dict[str, Any]] = []
    first_input: Path | None = None
    for stage in STAGES:
        input_json = pick_latest(stage, "input.json")
        if first_input is None:
            first_input = input_json
        row = {
            "stage": stage,
            "target_count": TARGETS[stage],
            "min_similarity": MINSIM[stage],
            "input_json": str(input_json),
            "nodes_jsonl": str(pick_latest(stage, "nodes.jsonl")),
            "edges_jsonl": str(pick_latest(stage, "edges.jsonl")),
            "matrix_json": str(pick_latest(stage, "similarity_matrix.json")),
            "phase_report_json": str(pick_latest(stage, "phase_report.json")),
        }
        stages.append(row)
    use_verse_source, use_event_source = detect_source_mode(first_input or Path())

    out = {
        "schema": "global_atom_full_canon_batch_manifest_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "run_stamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "out_dir": str(ART),
        "fast_smoke": False,
        "use_verse_source": use_verse_source,
        "use_event_source": use_event_source,
        "verse_source_json": "data/logos/verse_4pipeline_full_31102.json",
        "seed_insight_json": "docs/final/artifacts/bible_meaning_insight_candidates_latest.json",
        "start_stage": "genesis",
        "end_stage": "full_canon",
        "stages": stages,
        "note": "Auto-consolidated from latest stage artifacts.",
    }

    op = Path(args.output_json)
    if not op.is_absolute():
        op = ROOT / op
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

