# Keywords: showroom, trust_visualization_v0, stt_routing_audit, thin slice
"""Emit a small JSON next to jemaai-cloud-mvp static HTML for Visualization v0 (read-only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
KPI_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"
POLICY_DECISION = ROOT / "docs" / "final" / "artifacts" / "track_a_policy_floor_decision_v1.json"
SHADOW_AUDITOR = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_shadow_auditor_latest.json"
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
BOARD_MS_REPORT = ROOT / "docs" / "final" / "artifacts" / "compression_board_ms_correlation_report_v1_latest.json"
VPS_TRIPLET = ROOT / "docs" / "final" / "artifacts" / "compression_board_ms_vps_bench_triplet_v1_latest.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_dashboard(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _nodata_trust() -> Dict[str, Any]:
    return {
        "state": "NODATA",
        "path": "docs/final/schemas/trust_visualization_panel_v0.example.json",
        "role": "trust_visualization_read_only_v0",
    }


def _nodata_stt() -> Dict[str, Any]:
    return {
        "state": "NODATA",
        "summary_path": "reports/stt_routing_audit_log_v1_summary_latest.json",
        "role": "silver_stt_audit_summary_v0",
    }


def _rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _compression_governance_slice() -> Dict[str, Any]:
    """Read-only compression discipline panel for public showroom (artifact-bound)."""
    missing: list[str] = []
    kpi_doc: Dict[str, Any] = {}
    policy_doc: Dict[str, Any] = {}
    shadow_doc: Dict[str, Any] = {}

    if KPI_SUMMARY.is_file():
        try:
            kpi_doc = json.loads(KPI_SUMMARY.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            missing.append(_rel_path(KPI_SUMMARY))
    else:
        missing.append(_rel_path(KPI_SUMMARY))

    if POLICY_DECISION.is_file():
        try:
            policy_doc = json.loads(POLICY_DECISION.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            missing.append(_rel_path(POLICY_DECISION))
    else:
        missing.append(_rel_path(POLICY_DECISION))

    if SHADOW_AUDITOR.is_file():
        try:
            shadow_doc = json.loads(SHADOW_AUDITOR.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    active = kpi_doc.get("active_kpi") if isinstance(kpi_doc.get("active_kpi"), dict) else {}
    policy_min = active.get("ultra_saving_policy_min")
    policy_ok = active.get("ultra_saving_policy_ok")
    saving = active.get("global_token_saving_rate")
    jaccard = active.get("avg_reconstruction_fidelity_jaccard")

    state = "OK" if not missing and policy_ok is True else ("PARTIAL" if kpi_doc else "NODATA")

    return {
        "state": state,
        "role": "compression_governance_read_only_v0",
        "policy_floor": policy_min,
        "ultra_saving_policy_ok": policy_ok,
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": jaccard,
        "avg_sensitive_integrity": active.get("avg_sensitive_integrity"),
        "policy_decision_note": policy_doc.get("summary") or policy_doc.get("decision_note"),
        "shadow_auditor_ok": shadow_doc.get("audit_ok"),
        "artifact_paths": {
            "kpi_summary": _rel_path(KPI_SUMMARY),
            "policy_decision": _rel_path(POLICY_DECISION),
            "active_report": _rel_path(ACTIVE_REPORT),
            "shadow_auditor": _rel_path(SHADOW_AUDITOR) if SHADOW_AUDITOR.is_file() else None,
            "executive_summary": "docs/final/artifacts/compression_enterprise_executive_summary_v1.md",
        },
        "missing_paths": missing,
        "boundary_note": (
            "Bench KPI only; not production SLA, BOM savings, or trading signal. "
            "Jaccard is lexical overlap proxy—not semantic equivalence."
        ),
    }


def _board_ms_latency_slice() -> Dict[str, Any]:
    """RQ-017 read-only latency layers; no causal token-saving ↔ RTT claim."""
    if not BOARD_MS_REPORT.is_file():
        return {
            "state": "NODATA",
            "role": "compression_board_ms_research_read_only_v0",
            "artifact_path": _rel_path(BOARD_MS_REPORT),
            "boundary_note": "Run build_compression_board_ms_correlation_report_v1.py after bench runs.",
        }
    try:
        doc = json.loads(BOARD_MS_REPORT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "state": "PARTIAL",
            "role": "compression_board_ms_research_read_only_v0",
            "artifact_path": _rel_path(BOARD_MS_REPORT),
        }
    layers = doc.get("latency_layers") if isinstance(doc.get("latency_layers"), dict) else {}
    local = layers.get("local_loopback") if isinstance(layers.get("local_loopback"), dict) else {}
    vps = layers.get("vps_same_host_snapshot") if isinstance(layers.get("vps_same_host_snapshot"), dict) else {}
    derived = doc.get("derived") if isinstance(doc.get("derived"), dict) else {}
    triplet_doc: Dict[str, Any] = {}
    if VPS_TRIPLET.is_file():
        try:
            triplet_doc = json.loads(VPS_TRIPLET.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            triplet_doc = {}
    triplet_derived = (
        triplet_doc.get("derived") if isinstance(triplet_doc.get("derived"), dict) else {}
    )
    return {
        "state": "OK",
        "role": "compression_board_ms_research_read_only_v0",
        "hypothesis_tag": doc.get("status") or "[HYPO]",
        "correlation_claim_allowed": derived.get("correlation_claim_allowed"),
        "local_p95_ms": local.get("p95_ms"),
        "vps_p95_ms": vps.get("p95_ms"),
        "vps_p95_ms_triplet_median": triplet_derived.get("p95_ms_median"),
        "vps_triplet_ok": triplet_derived.get("triplet_ok"),
        "local_bench_environment": local.get("bench_environment"),
        "vps_bench_environment": vps.get("bench_environment"),
        "artifact_path": _rel_path(BOARD_MS_REPORT),
        "boundary_note": derived.get("correlation_claim_note")
        or "Research-only; loopback is not edge/VPS SLA.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dashboard",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "mkm_trackc_ops_dashboard_latest.json",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT
        / "projects"
        / "bitcoin-trading"
        / "ops"
        / "windows-rehearsal"
        / "jemaai-cloud-mvp"
        / "showroom_trust_visualization_slice_v0.json",
    )
    args = ap.parse_args()

    dash = _read_dashboard(args.dashboard)
    tc = dash.get("trackc") if isinstance(dash.get("trackc"), dict) else {}
    trust = tc.get("trust_visualization_v0")
    stt = tc.get("stt_routing_audit_log_slice")
    if not isinstance(trust, dict):
        trust = _nodata_trust()
    if not isinstance(stt, dict):
        stt = _nodata_stt()

    try:
        rel_dash = str(args.dashboard.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        rel_dash = str(args.dashboard)

    compression = _compression_governance_slice()

    doc: Dict[str, Any] = {
        "schema": "showroom_trust_visualization_slice_v0",
        "version": "0.1.2",
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now_z(),
        "source_dashboard_rel": rel_dash,
        "trust_visualization_v0": trust,
        "stt_routing_audit_log_slice": stt,
        "compression_governance_v0": compression,
        "compression_board_ms_v0": _board_ms_latency_slice(),
        "boundary_note": "Read-only showroom slice from Track C ops dashboard; not a trading signal.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(args.out),
                "trust_state": trust.get("state"),
                "stt_state": stt.get("state"),
                "compression_state": compression.get("state"),
                "policy_floor": compression.get("policy_floor"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
