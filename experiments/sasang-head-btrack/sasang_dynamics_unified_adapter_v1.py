"""Sasang dynamics unified adapter v1 — B-track only (SPEC-MKM-2026-06A).

Pipeline: machine_readables → stress → pathology_stage → severity → geumhwa gate (read-only).
Delegates formulas to C:\\workspace\\scripts\\sasang_persona_grid_v1.py — no new clinical formulas.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_SCRIPTS = Path(r"C:\workspace\scripts")
if str(WORKSPACE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_SCRIPTS))

from sasang_persona_grid_v1 import (  # noqa: E402
    pathology_stage_from_stress,
    severity_from_stress,
    stress_from_machine_readables,
)

SCHEMA = "sasang_dynamics_unified_ablation_v1"
VERSION = "1.0.0"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_geumhwa_gate(
    workspace_root: Path,
) -> dict[str, Any]:
    policy_path = workspace_root / "docs/final/artifacts/sasang_4agent_monitor_policy_v1.json"
    fusion_path = workspace_root / "docs/final/artifacts/sasang_4agent_fusion_gate_latest.json"
    policy = _load_json(policy_path) if policy_path.is_file() else {}
    fusion = _load_json(fusion_path) if fusion_path.is_file() else {}
    threshold = float(policy.get("geumhwa_transition_threshold", 0.58))
    geumhwa = (fusion.get("fusion") or {}).get("geumhwa_transition") or {}
    score = geumhwa.get("score")
    breach = isinstance(score, (int, float)) and float(score) >= threshold
    return {
        "threshold": threshold,
        "score": score,
        "breach": breach,
        "force_hold_tactical": breach and bool((policy.get("auto_injection") or {}).get("force_hold")),
        "provenance": {
            "monitor_policy": str(policy_path).replace("\\", "/"),
            "fusion_gate": str(fusion_path).replace("\\", "/"),
        },
        "note_ko": "geumhwa gate = 4-agent monitor 은유; 체질·임상·Track A 아님.",
    }


def build_unified_output(
    machine_readables: dict[str, Any],
    *,
    workspace_root: Path,
    input_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    heat = machine_readables.get("heat_proxy")
    vol = machine_readables.get("volatility_rarefaction_proxy")
    tim = machine_readables.get("thermal_imbalance_proxy")
    if tim is None and isinstance(heat, (int, float)) and isinstance(machine_readables.get("cold_proxy"), (int, float)):
        tim = abs(float(heat) - float(machine_readables["cold_proxy"]))

    stress = stress_from_machine_readables(machine_readables)
    stage = pathology_stage_from_stress(stress, thermal_imbalance=tim, heat=heat if isinstance(heat, (int, float)) else None)
    severity = severity_from_stress(stress)
    geumhwa = _read_geumhwa_gate(workspace_root)

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc(),
        "rail": "B_TRACK",
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_to_a_track_allowed": False,
        "decision_authority": "human_only",
        "pipeline_v1": [
            "machine_readables",
            "stress_from_machine_readables",
            "pathology_stage_from_stress",
            "severity_from_stress",
            "geumhwa_monitor_read_only",
        ],
        "input_provenance": input_provenance or {},
        "machine_readables": machine_readables,
        "stress_v1": stress,
        "pathology_stage_v1": stage,
        "severity_v1": severity,
        "geumhwa_gate_v1": geumhwa,
        "forbidden_merges_ack": [
            "clinical_diagnosis_output",
            "live_trading_trigger",
            "track_a_compression_floor",
        ],
        "contract_ref": "docs/final/artifacts/SASANG_DYNAMICS_V1_CONTRACT.json",
    }


def machine_readables_from_lens_doc(doc: dict[str, Any]) -> dict[str, Any] | None:
    stream = doc.get("sasang_stream_outputs") or {}
    mr = stream.get("machine_readables")
    if isinstance(mr, dict):
        return mr
    axis = doc.get("b_track_axis_scores_v1") or {}
    if isinstance(axis, dict) and axis.get("heat_proxy") is not None:
        return {
            "heat_proxy": axis.get("heat_proxy"),
            "cold_proxy": axis.get("cold_proxy"),
            "volatility_rarefaction_proxy": axis.get("volatility_rarefaction_proxy"),
            "thermal_imbalance_proxy": axis.get("thermal_imbalance_proxy"),
        }
    return None
