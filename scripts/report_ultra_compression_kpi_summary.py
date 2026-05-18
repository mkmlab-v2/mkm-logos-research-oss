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
ACTIVE_LITERAL = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json"
ACTIVE_ULTRA_LITERAL = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json"
HYDRATION_MIX = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_mix_latest.json"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"
# RQ-016 internal V2 bench reference (distinct from ULTRA_TOKEN_SAVING_POLICY_MIN=0.49 in evaluate_report).
BENCH_SAVING_FLOOR_REF = 0.47


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _kpi_from_report(report: dict[str, Any]) -> dict[str, Any]:
    active_metrics = report.get("compression_metrics", {}) if isinstance(report, dict) else {}
    quality = report.get("quality_gate", {}) if isinstance(report, dict) else {}
    saving = active_metrics.get("global_token_saving_rate")
    bench_floor_ok = (
        float(saving) >= BENCH_SAVING_FLOOR_REF if saving is not None else None
    )
    return {
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": active_metrics.get("avg_reconstruction_fidelity_jaccard"),
        "avg_sensitive_integrity": active_metrics.get("avg_sensitive_integrity"),
        "jaccard_drop_pp": quality.get("jaccard_drop_pp"),
        "jaccard_guardrail_ok": quality.get("jaccard_guardrail_ok"),
        "ultra_saving_50_ok": quality.get("ultra_saving_50_ok"),
        "ultra_saving_policy_ok": quality.get("ultra_saving_policy_ok"),
        "ultra_saving_policy_min": quality.get("ultra_saving_policy_min"),
        "bench_saving_floor_min": BENCH_SAVING_FLOOR_REF,
        "bench_saving_floor_ok": bench_floor_ok,
        "sensitive_integrity_ok": quality.get("sensitive_integrity_ok"),
    }


def main() -> int:
    round2 = _load(ROUND2)
    decision = _load(DECISION)
    active = _load(ACTIVE)
    active_literal = _load(ACTIVE_LITERAL)
    active_ultra_literal = _load(ACTIVE_ULTRA_LITERAL)
    hyd = _load(HYDRATION_MIX)

    selected = decision.get("selected_candidate", {}) if isinstance(decision, dict) else {}
    round2_perf = round2.get("perf", {}) if isinstance(round2, dict) else {}
    decision_perf = decision.get("perf", {}) if isinstance(decision, dict) else {}

    out = {
        "schema": "ultra_compression_kpi_summary_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "round2": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ROUND2_V1.json",
            "decision": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json",
            "active": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "literal_active": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json",
            "ultra_literal_active": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json",
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
        "active_kpi": _kpi_from_report(active) if isinstance(active.get("compression_metrics"), dict) else {},
        "literal_kpi": (
            _kpi_from_report(active_literal)
            if ACTIVE_LITERAL.is_file() and isinstance(active_literal.get("compression_metrics"), dict)
            else None
        ),
        "ultra_literal_kpi": (
            _kpi_from_report(active_ultra_literal)
            if ACTIVE_ULTRA_LITERAL.is_file() and isinstance(active_ultra_literal.get("compression_metrics"), dict)
            else None
        ),
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
