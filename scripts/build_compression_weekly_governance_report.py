#!/usr/bin/env python3
"""Emit weekly compression governance report with refresh timestamps (Track A + optional Track B pointers)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ART = ROOT / "docs" / "final" / "artifacts"
KPI_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"
OUT_LATEST = ART / "compression_weekly_governance_report_latest.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _headline_kpi(blob: dict[str, Any] | None) -> dict[str, Any] | None:
    if not blob or not isinstance(blob, dict):
        return None
    keys = (
        "global_token_saving_rate",
        "avg_reconstruction_fidelity_jaccard",
        "avg_sensitive_integrity",
        "jaccard_guardrail_ok",
        "ultra_saving_policy_ok",
        "sensitive_integrity_ok",
    )
    out = {k: blob[k] for k in keys if k in blob}
    return out or None


def main() -> int:
    kpi = _load(KPI_SUMMARY)
    if not kpi or kpi.get("schema") != "ultra_compression_kpi_summary_v1":
        print(f"ERROR: missing or invalid KPI summary: {KPI_SUMMARY}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    date_utc = now.strftime("%Y-%m-%d")
    iso_year, iso_week, _ = now.isocalendar()
    iso_week_label = f"{iso_year}-W{iso_week:02d}"

    active = kpi.get("active_kpi") if isinstance(kpi.get("active_kpi"), dict) else {}
    lit = kpi.get("literal_kpi")
    lit_h = _headline_kpi(lit) if isinstance(lit, dict) else None

    doc: dict[str, Any] = {
        "schema": "compression_weekly_governance_report_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "refresh_calendar_date_utc": date_utc,
        "iso_week_label": iso_week_label,
        "sources": {
            "kpi_summary": "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json",
            "kpi_summary_ts_utc": kpi.get("ts_utc"),
            "sla_policy": "docs/final/COMPRESSION_SLA_POLICY_V1.md",
            "interpretation_fact_lock": "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
        },
        "artifact_pointers": {
            "active_report_track_a": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "active_report_literal": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json",
            "loss_patterns_universal": "reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_latest.json",
            "loss_patterns_literal": "reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_literal_latest.json",
        },
        "headline": {
            "track_a_universal": _headline_kpi(active),
            "track_b_literal": lit_h,
        },
        "decision_snapshot": {
            "go_no_go": (kpi.get("decision") or {}).get("go_no_go"),
            "rollout_policy": (kpi.get("decision") or {}).get("rollout_policy"),
        },
        "kpi_summary_embed": kpi,
        "governance": {
            "webhook_alarm_evaluates_track_a_active_kpi_only": True,
            "chain_runner": "scripts/run_compression_weekly_governance_chain.ps1",
        },
        "fact_safe_note": (
            "Governance report is observability for scheduled refresh; it does not certify legal/clinical correctness. "
            "Re-run scripts to reproduce numbers on this workspace."
        ),
        "out_of_scope": "No production trading trigger; no automatic policy change from this JSON alone.",
    }

    ART.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_LATEST.write_text(text, encoding="utf-8")
    dated_path = ART / f"compression_weekly_governance_report_{date_utc}.json"
    dated_path.write_text(text, encoding="utf-8")
    print(f"WROTE: {OUT_LATEST}")
    print(f"WROTE: {dated_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
