#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build integrated report for staged full-canon global atom runs.")
    ap.add_argument("--stages-json", required=True)
    ap.add_argument("--output-json", default="docs/final/artifacts/global_atom_full_canon_batch_report_latest.json")
    args = ap.parse_args()

    sp = resolve(args.stages_json)
    op = resolve(args.output_json)
    if not sp.is_file():
        raise SystemExit(f"missing stage manifest: {sp}")
    manifest = load(sp)
    stages = manifest.get("stages") or []
    if not isinstance(stages, list) or not stages:
        raise SystemExit("stage manifest has no stages")
    use_verse_source = bool(manifest.get("use_verse_source", False))
    use_event_source = bool(manifest.get("use_event_source", False))

    rows: list[dict[str, Any]] = []
    all_ok = True
    total_nodes = 0
    total_edges = 0
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        phase_path = resolve(str(stage.get("phase_report_json", "")))
        status = "missing_phase_report"
        summary: dict[str, Any] = {}
        if phase_path.is_file():
            phase = load(phase_path)
            summary = dict((phase.get("summary") or {}))
            status = "ok"
        else:
            all_ok = False
        nodes = int(summary.get("node_count", 0) or 0)
        edges = int(summary.get("edge_count", 0) or 0)
        total_nodes += nodes
        total_edges += edges
        rows.append(
            {
                "stage": stage.get("stage"),
                "target_count": stage.get("target_count"),
                "min_similarity": stage.get("min_similarity"),
                "phase_report_json": str(phase_path),
                "status": status,
                "node_count": nodes,
                "edge_count": edges,
                "phase_transition_signal": summary.get("phase_transition_signal"),
            }
        )

    out = {
        "schema": "global_atom_full_canon_batch_report_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "run_lineage": {
            "run_stamp": manifest.get("run_stamp"),
            "start_stage": manifest.get("start_stage"),
            "end_stage": manifest.get("end_stage"),
            "use_verse_source": bool(manifest.get("use_verse_source", False)),
            "use_event_source": bool(manifest.get("use_event_source", False)),
            "event_window_size": manifest.get("event_window_size"),
        },
        "summary": {
            "stages_total": len(stages),
            "stages_ok": sum(1 for r in rows if r["status"] == "ok"),
            "status": "GO" if all_ok else "HOLD",
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "source_mode": (
                "event_level_ingest" if use_event_source else ("verse_level_ingest" if use_verse_source else "seed_bootstrap")
            ),
        },
        "stages": rows,
        "note": (
            "Stage report from event-level ingest."
            if use_event_source
            else ("Stage report from verse-level ingest." if use_verse_source else "Stage bootstrap report; full-canon readiness still requires verse-level source extraction.")
        ),
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

