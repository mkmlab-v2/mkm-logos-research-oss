#!/usr/bin/env python3
"""Build baseline snapshot for MKM commercial-safe completion."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_commercial_baseline_snapshot_v1_latest.json"


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
    gate_path = ROOT / "docs" / "final" / "artifacts" / "three_lens_feature_gate_v2_latest.json"
    pack_path = ROOT / "docs" / "final" / "artifacts" / "three_lens_coordinator_decision_pack_v1_latest.json"
    status_path = ROOT / "docs" / "final" / "artifacts" / "three_lens_staged_inclusion_status_latest.json"
    scheduler_path = ROOT / "reports" / "scheduler_phase3_slimming_latest.json"
    evolution_path = ROOT / "docs" / "final" / "artifacts" / "evolution_lightweight_loop_latest.json"

    gate = _safe_json(gate_path)
    pack = _safe_json(pack_path)
    status = _safe_json(status_path)
    sched = _safe_json(scheduler_path)
    evo = _safe_json(evolution_path)

    payload = {
        "schema": "mkm_commercial_baseline_snapshot_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "three_lens_feature_gate_v2": str(gate_path),
            "three_lens_coordinator_decision_pack": str(pack_path),
            "three_lens_staged_inclusion_status": str(status_path),
            "scheduler_phase3_slimming": str(scheduler_path),
            "evolution_lightweight_loop": str(evolution_path),
        },
        "baseline_metrics": {
            "gate_action": ((gate.get("decision") or {}).get("action") if isinstance(gate.get("decision"), dict) else None),
            "gate_reason": ((gate.get("decision") or {}).get("reason") if isinstance(gate.get("decision"), dict) else None),
            "risk_score_0_1": ((gate.get("metrics") or {}).get("risk_score_0_1") if isinstance(gate.get("metrics"), dict) else None),
            "opportunity_score_0_1": ((gate.get("metrics") or {}).get("opportunity_score_0_1") if isinstance(gate.get("metrics"), dict) else None),
            "status_enabled_count": ((status.get("summary") or {}).get("enabled_count") if isinstance(status.get("summary"), dict) else None),
            "status_shadow_missing_count": ((status.get("summary") or {}).get("shadow_missing_count") if isinstance(status.get("summary"), dict) else None),
            "scheduler_morning_window_task_count": ((sched.get("summary") or {}).get("morning_window_task_count") if isinstance(sched.get("summary"), dict) else None),
            "scheduler_candidate_reduce_count": ((sched.get("summary") or {}).get("candidate_reduce_count") if isinstance(sched.get("summary"), dict) else None),
            "evolution_triggered": evo.get("triggered"),
            "evolution_overall_ok": evo.get("overall_ok"),
            "coordinator_action": ((pack.get("final_decision") or {}).get("action") if isinstance(pack.get("final_decision"), dict) else None),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
