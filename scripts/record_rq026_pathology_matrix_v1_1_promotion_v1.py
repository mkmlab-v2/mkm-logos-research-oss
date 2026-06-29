#!/usr/bin/env python3
"""Record B-track promotion of pathology matrix v1_1 to sim default (RQ-026, experiments/ only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs/final/artifacts/rq026_pathology_matrix_v1_1_btrack_promotion_v1_latest.json"
PROMOTED = ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_1.json"
SUPERSEDES = ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1.json"
SWEEP = ROOT / "docs/final/artifacts/sasang_temperament_agents_matrix_sweep_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--promoted-by", default="commander")
    args = ap.parse_args()

    sweep_doc: dict[str, Any] = {}
    if SWEEP.is_file():
        sweep_doc = json.loads(SWEEP.read_text(encoding="utf-8"))

    doc: dict[str, Any] = {
        "schema": "rq026_pathology_matrix_btrack_promotion_v1",
        "promotion_utc": _utc(),
        "promoted_by": args.promoted_by,
        "rq_id": "RQ-026",
        "hypothesis_tier": "B",
        "research_only": True,
        "not_promoted_track_a": True,
        "promotion_scope_ko": "experiments/sasang_temperament_agents_v1 sim DEFAULT_MATRIX only",
        "promoted_matrix": _rel(PROMOTED),
        "promoted_matrix_version": "1.1.0",
        "supersedes_default": _rel(SUPERSEDES),
        "supersedes_version": "1.0.0",
        "evidence_pointers": {
            "matrix_sweep": _rel(SWEEP),
            "recommended_candidate": sweep_doc.get("recommended_candidate"),
            "phase4_v1_1": _rel(
                ROOT
                / "docs/final/artifacts/sasang_temperament_agents_phase4_holdout_ablation_v1_1_latest.json"
            ),
        },
        "explicit_not_promoted": [
            "NG-40 codec merge",
            "Track A ACTIVE report",
            "live trading",
            "RQ-026 CLOSED",
            "CONSTITUTION body edit",
        ],
        "rollback": {
            "sim_flag": "--matrix experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1.json",
            "note_ko": "baseline v1은 파일 유지; DEFAULT만 v1_1로 교체.",
        },
        "boundary_ko": "B-track sim default 교체만. 압축·실매매·임상 게이팅 합선 아님.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": _rel(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
