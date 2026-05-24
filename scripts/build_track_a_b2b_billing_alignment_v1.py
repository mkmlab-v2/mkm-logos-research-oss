#!/usr/bin/env python3
"""Build Track A B2B billing alignment matrix (metering + API + MS KPI boundaries)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/track_a_b2b_billing_alignment_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
SIGNOFF = ROOT / "docs/final/artifacts/multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json"
METER_SUM = ROOT / "docs/final/artifacts/track_a_metering_summary_latest.json"
METER_WEEK = ROOT / "docs/final/artifacts/track_a_metering_weekly_report_latest.json"
BAND = ROOT / "docs/final/artifacts/track_a_metering_band_gate_latest.json"
COST = ROOT / "docs/final/artifacts/track_a_conversational_cost_simulation_latest.json"
HEADLINE = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
OPENAPI = ROOT / "docs/final/openapi_token_compression_stub_v1.yaml"
SLA = ROOT / "docs/final/TRACK_A_SLA_DRAFT.md"
TIER = ROOT / "docs/final/artifacts/compression_domain_adoption_tier_matrix_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


def main() -> int:
    active = _load(ACTIVE) or {}
    cm = active.get("compression_metrics") if isinstance(active.get("compression_metrics"), dict) else {}
    signoff = _load(SIGNOFF)
    band = _load(BAND) or {}
    week = _load(METER_WEEK) or {}
    headline = _load(HEADLINE) or {}

    hp = headline.get("headline_promotion_v1") if isinstance(headline.get("headline_promotion_v1"), dict) else {}
    saving = cm.get("global_token_saving_rate")
    jaccard = cm.get("avg_reconstruction_fidelity_jaccard")

    doc: dict[str, Any] = {
        "schema": "track_a_b2b_billing_alignment_v1",
        "generated_at_utc": _utc(),
        "status": "internal_b2b_alignment_draft",
        "research_only": False,
        "track_a_live_auto_merge": False,
        "api_surface_ssot": _rel(OPENAPI) if OPENAPI.is_file() else None,
        "sla_draft_pointer": _rel(SLA) if SLA.is_file() else None,
        "adoption_tier_pointer": _rel(TIER) if TIER.is_file() else None,
        "ms_kpi_only": {
            "global_token_saving_rate": saving,
            "avg_reconstruction_fidelity_jaccard": jaccard,
            "apply_gematria_4d_bridge_policy": (active.get("run_config") or {}).get("apply_gematria_4d_bridge_policy")
            if isinstance(active.get("run_config"), dict)
            else None,
            "active_report": _rel(ACTIVE),
            "promotion_signoff": _rel(SIGNOFF) if signoff else None,
            "selected_variant_id": (signoff or {}).get("selected_variant_id"),
        },
        "excluded_from_b2b_pricing_headline": {
            "prophecy_oracle_hit_rate": (headline.get("metrics") or {}).get("price_directional_hit_rate"),
            "prophecy_lane": hp.get("lane"),
            "note": "Oracle 57.3% is commander headline lane; MS/compression B2B cites 47.5% only.",
        },
        "metering_chain": {
            "log_path_default": "reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl",
            "summary": _rel(METER_SUM) if METER_SUM.is_file() else None,
            "weekly": _rel(METER_WEEK) if METER_WEEK.is_file() else None,
            "band_gate": {
                "path": _rel(BAND) if BAND.is_file() else None,
                "decision": band.get("decision"),
                "mode": band.get("mode"),
                "target_band_hit_rate": week.get("target_band_hit_rate"),
            },
            "cost_simulation": _rel(COST) if COST.is_file() else None,
        },
        "billing_unit_candidates_v1": [
            {
                "unit_id": "per_compress_request",
                "source": "POST /v1/compress + meter_log token_in/token_out",
                "settlement": "TBD_not_payapp_wired",
            },
            {
                "unit_id": "token_saving_rate_band",
                "source": "meter_log saving_rate vs ACTIVE bench global_token_saving_rate",
                "settlement": "warning_mode_band_gate",
            },
        ],
        "b2b_copy_guardrails": [
            "Do not cite prophecy hit-rate in compression MS or a-codeai pricing deck.",
            "Do not cite Logos RAG KO mean as compression KPI.",
            "Jaccard is reconstruction proxy not legal/compliance seal.",
            "Metering log is evidence not invoice; PayApp path separate.",
        ],
        "settlement_integration": {
            "payapp_wired": False,
            "next_human_gate": "legal_review + PayApp SKU mapping",
        },
        "reproduction": [
            "py scripts/run_track_a_commercialization_daily_chain.ps1",
            "py scripts/build_track_a_b2b_billing_alignment_v1.py",
            "py scripts/check_compression_domain_adoption_tier_v1.py",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(OUT), "saving_rate": saving, "band": band.get("decision")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
