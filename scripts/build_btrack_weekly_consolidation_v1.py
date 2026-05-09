#!/usr/bin/env python3
"""Merge B-track 99% plan artifacts into one consolidation JSON (research lane)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "btrack_weekly_consolidation_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    lb_path = ART / "btrack_compression_leaderboard_latest.json"
    r2_path = ART / "btrack_gate_r2_phase_sweep_latest.json"
    stress_path = ART / "trackb_stress_benchmark_summary_latest.json"
    det_path = ART / "trackb_determinism_repeatcheck_latest.json"

    lb = _load(lb_path) if lb_path.exists() else {}
    r2 = _load(r2_path) if r2_path.exists() else {}
    stress = _load(stress_path) if stress_path.exists() else {}
    det = _load(det_path) if det_path.exists() else {}

    out: dict[str, Any] = {
        "schema": "btrack_weekly_consolidation_v1",
        "generated_at_utc": _utc_now(),
        "lane": "research_only",
        "inputs": {
            "compression_leaderboard": str(lb_path.relative_to(ROOT)).replace("\\", "/"),
            "gate_r2_sweep": str(r2_path.relative_to(ROOT)).replace("\\", "/"),
            "trackb_stress_benchmark_summary": str(stress_path.relative_to(ROOT)).replace("\\", "/"),
            "trackb_determinism": str(det_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "week22_spike_lane": {
            "best_overall": lb.get("best_overall"),
            "gate_r2_best_row": r2.get("best_row"),
            "reached_saving_ge_060": r2.get("reached_saving_ge_060"),
        },
        "track_b_quaternion_lane": {
            "stress_recommendation": stress.get("recommendation"),
            "top3_artifacts": [
                (r.get("artifact") if isinstance(r, dict) else None)
                for r in (stress.get("top3_candidates") or [])[:3]
            ],
            "determinism_overall": det.get("overall_deterministic"),
            "determinism_decision": det.get("decision"),
        },
        "interpretation_note": (
            "Week22 E2 spike metrics (saving/jaccard from pool spike artifacts) and Track B quaternion "
            "stress evaluators are different stacks; do not numerically equate their scores."
        ),
        "out_of_scope": "No production promotion, no trading trigger.",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
