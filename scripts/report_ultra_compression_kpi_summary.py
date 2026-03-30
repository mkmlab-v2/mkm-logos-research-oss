#!/usr/bin/env python3
"""Emit compact KPI summary for ultra compression artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ROUND2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ROUND2_V1.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
HYDRATION_MIX = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_mix_latest.json"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    round2 = _load(ROUND2)
    decision = _load(DECISION)
    active = _load(ACTIVE)
    hyd = _load(HYDRATION_MIX)

    selected = decision.get("selected_candidate", {}) if isinstance(decision, dict) else {}
    active_metrics = active.get("compression_metrics", {}) if isinstance(active, dict) else {}
    quality = active.get("quality_gate", {}) if isinstance(active, dict) else {}
    round2_perf = round2.get("perf", {}) if isinstance(round2, dict) else {}
    decision_perf = decision.get("perf", {}) if isinstance(decision, dict) else {}

    out = {
        "schema": "ultra_compression_kpi_summary_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "round2": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ROUND2_V1.json",
            "decision": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json",
            "active": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "hydration_mix": "reports/constitution/btrack_pilot/token_api_hydration_mix_latest.json",
        },
        "decision": {
            "go_no_go": decision.get("go_no_go"),
            "rollout_policy": decision.get("rollout_policy"),
            "selected_candidate": {
                "strategy": selected.get("strategy"),
                "intensity": selected.get("intensity"),
                "global_token_saving_rate": selected.get("global_token_saving_rate"),
                "avg_reconstruction_fidelity_jaccard": selected.get("avg_reconstruction_fidelity_jaccard"),
                "avg_sensitive_integrity": selected.get("avg_sensitive_integrity"),
                "jaccard_drop_pp": selected.get("jaccard_drop_pp"),
            },
        },
        "active_kpi": {
            "global_token_saving_rate": active_metrics.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": active_metrics.get("avg_reconstruction_fidelity_jaccard"),
            "avg_sensitive_integrity": active_metrics.get("avg_sensitive_integrity"),
            "jaccard_drop_pp": quality.get("jaccard_drop_pp"),
            "jaccard_guardrail_ok": quality.get("jaccard_guardrail_ok"),
            "ultra_saving_50_ok": quality.get("ultra_saving_50_ok"),
            "sensitive_integrity_ok": quality.get("sensitive_integrity_ok"),
        },
        "performance": {
            "bench_total_elapsed_ms": decision_perf.get("total_elapsed_ms"),
            "round2_elapsed_ms": round2_perf.get("elapsed_ms"),
            "round2_full_grid_count": round2_perf.get("full_grid_count"),
            "round2_evaluated_count": round2_perf.get("evaluated_count"),
            "round2_pruned_by_saving_count": round2_perf.get("pruned_by_saving_count"),
            "round2_pruned_by_bound_count": round2_perf.get("pruned_by_bound_count"),
        },
        "api_hydration_mix": {
            "total_examples": hyd.get("total_examples"),
            "metrics_mode_counts": hyd.get("metrics_mode_counts"),
            "live_ratio": hyd.get("live_ratio"),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
