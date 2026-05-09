#!/usr/bin/env python3
"""Build MKM commercial-safe gate pack summary artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_commercial_gate_pack_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return _read_json(path)
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=OUT)
    args = ap.parse_args()
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    baseline = _safe_json(ROOT / "docs" / "final" / "artifacts" / "mkm_commercial_baseline_snapshot_v1_latest.json")
    gate = _safe_json(ROOT / "docs" / "final" / "artifacts" / "three_lens_feature_gate_v2_latest.json")
    status = _safe_json(ROOT / "docs" / "final" / "artifacts" / "three_lens_staged_inclusion_status_latest.json")
    scheduler = _safe_json(ROOT / "reports" / "scheduler_phase3_slimming_latest.json")
    evolution = _safe_json(ROOT / "docs" / "final" / "artifacts" / "mkm_evolution_readiness_report_v1_latest.json")

    decision = (gate.get("decision") or {}) if isinstance(gate.get("decision"), dict) else {}
    status_summary = (status.get("summary") or {}) if isinstance(status.get("summary"), dict) else {}
    sched_summary = (scheduler.get("summary") or {}) if isinstance(scheduler.get("summary"), dict) else {}
    evo_quality = (evolution.get("quality") or {}) if isinstance(evolution.get("quality"), dict) else {}

    payload = {
        "schema": "mkm_commercial_gate_pack_v1",
        "generated_at_utc": _now(),
        "mode": "safe_production",
        "inputs": {
            "baseline_snapshot": "docs/final/artifacts/mkm_commercial_baseline_snapshot_v1_latest.json",
            "three_lens_feature_gate_v2": "docs/final/artifacts/three_lens_feature_gate_v2_latest.json",
            "three_lens_staged_inclusion_status": "docs/final/artifacts/three_lens_staged_inclusion_status_latest.json",
            "scheduler_phase3_slimming": "reports/scheduler_phase3_slimming_latest.json",
            "evolution_readiness_report": "docs/final/artifacts/mkm_evolution_readiness_report_v1_latest.json",
        },
        "gate_summary": {
            "action": decision.get("action"),
            "reason": decision.get("reason"),
            "research_only": decision.get("research_only"),
            "human_signoff_required": decision.get("human_signoff_required"),
        },
        "staged_inclusion_summary": {
            "enabled_count": status_summary.get("enabled_count"),
            "shadow_count": status_summary.get("shadow_count"),
            "shadow_missing_count": status_summary.get("shadow_missing_count"),
        },
        "scheduler_summary": {
            "morning_window_task_count": sched_summary.get("morning_window_task_count"),
            "candidate_reduce_count": sched_summary.get("candidate_reduce_count"),
        },
        "evolution_summary": {
            "loop_overall_ok": evo_quality.get("loop_overall_ok"),
            "proposal_count": evo_quality.get("proposal_count"),
            "requires_human_approval": evo_quality.get("requires_human_approval"),
        },
        "commercial_ready_safe_mode": bool(
            decision.get("action") in {"GO", "WATCH"}
            and status_summary.get("shadow_missing_count") in {0, None}
            and evo_quality.get("loop_overall_ok") is True
        ),
        "notes": [
            "Safe mode keeps research_only and human signoff enabled.",
            "Direct live trigger bridge remains blocked by policy.",
        ],
        "baseline_reference": baseline.get("baseline_metrics"),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
