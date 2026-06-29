"""Sasang routing sidecar × narrative path A/B ([HYPO] — narrowing gate, no score fusion)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
_CORE = Path(__file__).resolve().parent
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from logos_narrative_path_eval_v1 import (  # noqa: E402
    _resonance_index,
    eval_narrative_sample,
)

DEFAULT_PANEL = (
    ROOT / "docs/final/artifacts/fixtures/sasang_routing_sidecar_narrative_ab_panel_v1.json"
)
DEFAULT_SIDECAR = (
    ROOT / "docs/final/artifacts/sasang_routing_sidecar_on_gematria_path_v1_latest.json"
)
DEFAULT_BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sidecar_narrowing_caps(sidecar: dict[str, Any]) -> dict[str, Any]:
    hints = sidecar.get("sasang_routing_hints") or {}
    posture = str(hints.get("posture_hint") or "observe_only")
    entropy_leg = str(hints.get("entropy_leg") or "observe")
    caps = {
        "max_router_paths": 6,
        "max_hop_count": 99,
        "min_flow_score": 0.0,
        "posture_hint": posture,
        "entropy_leg": entropy_leg,
        "pathology_state": hints.get("pathology_state"),
    }
    if entropy_leg == "tactical":
        caps["max_router_paths"] = 4
        caps["max_hop_count"] = 4
    elif entropy_leg == "structural":
        caps["max_router_paths"] = 3
        caps["min_flow_score"] = 0.5
    if posture == "valid_pathway_narrow":
        caps["max_router_paths"] = min(int(caps["max_router_paths"]), 5)
        caps["min_flow_score"] = max(float(caps["min_flow_score"]), 0.66)
    if posture == "entropy_leg_tactical_hold":
        caps["max_router_paths"] = min(int(caps["max_router_paths"]), 4)
    return caps


def apply_sidecar_narrowing(row: dict[str, Any], sidecar: dict[str, Any]) -> dict[str, Any]:
    caps = sidecar_narrowing_caps(sidecar)
    router_paths = int(row.get("router_paths") or 0)
    hop_count = int(row.get("hop_count") or 0)
    flow_score = float(row.get("flow_score") or 0.0)
    narrowed_router_paths = min(router_paths, int(caps["max_router_paths"]))
    path_within_cap = hop_count <= int(caps["max_hop_count"])
    flow_ok = flow_score >= float(caps["min_flow_score"])
    sidecar_gate_pass = bool(row.get("sample_pass")) and path_within_cap and flow_ok
    return {
        **row,
        "arm": "sidecar_on",
        "sidecar_applied": True,
        "sidecar_caps": caps,
        "narrowed_router_paths": narrowed_router_paths,
        "router_paths_delta": narrowed_router_paths - router_paths,
        "sidecar_path_within_cap": path_within_cap,
        "sidecar_flow_ok": flow_ok,
        "sidecar_gate_pass": sidecar_gate_pass,
    }


ENTROPY_PROFILES: dict[str, dict[str, Any]] = {
    "observe": {
        "posture_hint": "valid_pathway_narrow",
        "entropy_leg": "observe",
        "pathology_state": "watch",
    },
    "tactical": {
        "posture_hint": "entropy_leg_tactical_hold",
        "entropy_leg": "tactical",
        "pathology_state": "stress",
    },
    "structural": {
        "posture_hint": "entropy_leg_structural_wait",
        "entropy_leg": "structural",
        "pathology_state": "watch",
    },
}


def resolve_sample_ids(panel: dict[str, Any], bridge: dict[str, Any]) -> list[str]:
    mode = str(panel.get("panel_mode") or "fixed")
    if mode == "full":
        return [str(s.get("sample_id")) for s in bridge.get("narrative_path_samples") or [] if s.get("sample_id")]
    return list(panel.get("sample_ids") or [])


def apply_entropy_profile(sidecar: dict[str, Any], profile_id: str | None) -> dict[str, Any]:
    if not profile_id:
        return sidecar
    patch = ENTROPY_PROFILES.get(profile_id)
    if not patch:
        raise ValueError(f"unknown entropy profile: {profile_id!r}")
    out = json.loads(json.dumps(sidecar))
    hints = dict(out.get("sasang_routing_hints") or {})
    hints.update(patch)
    out["sasang_routing_hints"] = hints
    out["entropy_profile_id"] = profile_id
    return out


def build_ab_report(
    *,
    panel_path: Path = DEFAULT_PANEL,
    sidecar_path: Path = DEFAULT_SIDECAR,
    bridge_path: Path = DEFAULT_BRIDGE,
    run_router: bool = True,
    entropy_profile: str | None = None,
    report_tag: str | None = None,
) -> dict[str, Any]:
    panel = _load_json(panel_path)
    sidecar = apply_entropy_profile(_load_json(sidecar_path), entropy_profile)
    bridge = _load_json(bridge_path)

    sample_ids = resolve_sample_ids(panel, bridge)
    by_id = {str(s.get("sample_id")): s for s in bridge.get("narrative_path_samples") or []}
    missing = [sid for sid in sample_ids if sid not in by_id]
    if missing:
        raise ValueError(f"panel sample_ids missing from bridge: {missing}")

    resonance = _resonance_index(bridge)
    arm_off_rows: list[dict[str, Any]] = []
    arm_on_rows: list[dict[str, Any]] = []

    for sid in sample_ids:
        base = eval_narrative_sample(by_id[sid], resonance=resonance, run_router=run_router)
        base["arm"] = "sidecar_off"
        arm_off_rows.append(base)
        arm_on_rows.append(apply_sidecar_narrowing(base, sidecar))

    n = len(arm_off_rows)

    def _rate(rows: list[dict[str, Any]], key: str) -> float:
        return round(sum(1 for r in rows if r.get(key)) / n, 4) if n else 0.0

    def _mean(rows: list[dict[str, Any]], key: str) -> float:
        vals = [float(r.get(key) or 0) for r in rows]
        return round(sum(vals) / n, 4) if n else 0.0

    off_sample_pass = _rate(arm_off_rows, "sample_pass")
    on_sidecar_pass = _rate(arm_on_rows, "sidecar_gate_pass")
    off_router_paths = _mean(arm_off_rows, "router_paths")
    on_router_paths = _mean(arm_on_rows, "narrowed_router_paths")

    return {
        "schema": "sasang_routing_sidecar_narrative_path_ab_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "note_ko": (
            "Narrative path A/B — sidecar_off=baseline eval; sidecar_on=path narrowing caps only. "
            "No gematria×sasang score fusion · no prophecy vote merge."
        ),
        "inputs": {
            "panel": str(panel_path.relative_to(ROOT)).replace("\\", "/"),
            "panel_mode": str(panel.get("panel_mode") or "fixed"),
            "sidecar": str(sidecar_path.relative_to(ROOT)).replace("\\", "/"),
            "entropy_profile": entropy_profile,
            "report_tag": report_tag,
            "bridge": str(bridge_path.relative_to(ROOT)).replace("\\", "/"),
            "run_router": run_router,
        },
        "panel_sample_count": n,
        "arm_off": {
            "sample_pass_rate": off_sample_pass,
            "router_hit_rate": _rate(arm_off_rows, "router_hit"),
            "mean_router_paths": off_router_paths,
            "rows": arm_off_rows,
        },
        "arm_on": {
            "sidecar_gate_pass_rate": on_sidecar_pass,
            "mean_narrowed_router_paths": on_router_paths,
            "mean_router_paths_delta": round(on_router_paths - off_router_paths, 4),
            "rows": arm_on_rows,
        },
        "delta": {
            "sidecar_gate_pass_rate_minus_sample_pass_rate": round(on_sidecar_pass - off_sample_pass, 4),
            "narrowed_router_paths_minus_baseline": round(on_router_paths - off_router_paths, 4),
        },
        "forbidden_synthesis_ack": True,
        "must_not_merge_into": [
            "prophecy_vote",
            "track_a_compression_floor",
            "production_gematria_kernel",
        ],
        "reproduce": "py scripts/run_sasang_routing_sidecar_narrative_path_ab_chain_v1.py",
    }
