#!/usr/bin/env python3
"""[HYPO] Sandbox: map sasang pathology axis hints to Transfer Entropy prior bands (B-track only).

Does NOT write ensemble weights, order APIs, or Track A routes. Output is an observation artifact
for human review and offline research.

Inputs (priority):
  1) --bundle  btrack_llm_input_bundle_latest.json (uses sasang_interpretive_bridge_context)
  2) --interpretive  full sasang_interpretive_insight_bundle JSON
  3) Optional --te-json  { "transfer_entropy": <float> } from monitor export or manual probe

Output: docs/final/artifacts/sasang_pathology_te_mapping_hypo_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.btrack_interpretive_bridge_v1 import interpretive_bridge_payload

DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_INTERPRETIVE = ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
DEFAULT_TE_SNAPSHOT = ROOT / "docs/final/artifacts/btrack_transfer_entropy_snapshot_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/sasang_pathology_te_mapping_hypo_v1_latest.json"

# Research-only phase labels (not clinical staging SSOT).
PHASE_LABELS = ("early_transition", "mid_transition", "late_transition", "observation_only")

# TE bands aligned with monitor heuristics (projects/bitcoin-trading alert thresholds ~3.0 high).
TE_BANDS = ("low", "moderate", "elevated", "extreme")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _te_band(te: float | None) -> str:
    if te is None:
        return "unknown"
    if te < 1.0:
        return "low"
    if te < 2.0:
        return "moderate"
    if te < 3.0:
        return "elevated"
    return "extreme"


def _pathology_phase_hypo(bridge: dict[str, Any]) -> str:
    """Sandbox phase from interpretive axes (availability + sasang core), not clinical staging SSOT."""
    sections = bridge.get("sections_slice") if isinstance(bridge.get("sections_slice"), list) else []
    by_id = {
        str(s.get("axis_id")): s
        for s in sections
        if isinstance(s, dict) and s.get("axis_id")
    }
    byeong = by_id.get("byeongjeung_yakri")
    sasang_core = by_id.get("sasang_core") or by_id.get("sasang_lens")
    market_sasang = by_id.get("market_sasang")

    def _avail(axis: dict[str, Any] | None) -> str:
        if not isinstance(axis, dict):
            return "missing"
        return str(axis.get("availability") or "missing").strip().lower()

    b_av = _avail(byeong)
    s_av = _avail(sasang_core)
    m_av = _avail(market_sasang)

    if b_av == "missing" and s_av == "missing" and m_av == "missing":
        return "observation_only"
    if b_av == "linked" and (s_av in ("linked", "partial") or m_av in ("linked", "partial")):
        return "late_transition"
    if b_av == "linked":
        return "mid_transition"
    if b_av == "partial":
        return "early_transition"
    if s_av in ("linked", "partial") or m_av in ("linked", "partial"):
        return "early_transition"
    return "observation_only"


def _coherence_label(phase: str, te_band: str) -> str:
    if te_band == "unknown":
        return "unspecified"
    if phase == "late_transition" and te_band in ("elevated", "extreme"):
        return "chaotic_flow"
    if phase == "early_transition" and te_band in ("elevated", "extreme"):
        return "divergent_flow"
    if phase == "mid_transition" and te_band == "moderate":
        return "mixed_flow"
    if te_band == "low":
        return "stable_flow"
    return "custom_band"


def _mapping_rows(phase: str, te_band: str) -> list[dict[str, Any]]:
    """Active cell + full grid (all weight_hint=0)."""
    active = {
        "pathology_phase_hypo": phase,
        "te_prior_band": te_band,
        "entropy_coherence_hypo": _coherence_label(phase, te_band),
        "weight_hint": 0.0,
        "note_ko": f"[HYPO] active cell {phase}×{te_band} — 관측만, 자동 가중치 금지",
        "active": True,
    }
    grid: list[dict[str, Any]] = []
    for p in PHASE_LABELS:
        for tb in TE_BANDS:
            grid.append(
                {
                    "pathology_phase_hypo": p,
                    "te_prior_band": tb,
                    "entropy_coherence_hypo": _coherence_label(p, tb),
                    "weight_hint": 0.0,
                    "active": p == phase and tb == te_band,
                }
            )
    return [active, *grid]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--interpretive", type=Path, default=DEFAULT_INTERPRETIVE)
    ap.add_argument("--te-json", type=Path, default=None, help="Optional {transfer_entropy: float}; default: btrack TE snapshot")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bridge: dict[str, Any] | None = None
    bundle_doc = _read_json(args.bundle)
    if bundle_doc:
        arts = bundle_doc.get("artifacts") if isinstance(bundle_doc.get("artifacts"), dict) else {}
        slot = arts.get("sasang_interpretive_bridge_context") if isinstance(arts, dict) else None
        if isinstance(slot, dict) and slot.get("available"):
            bridge = slot

    if bridge is None:
        full = _read_json(args.interpretive)
        bridge = interpretive_bridge_payload(full, source_path=args.interpretive)

    te_val: float | None = None
    te_source = "none"
    te_path = args.te_json or DEFAULT_TE_SNAPSHOT
    if te_path.is_file():
        te_doc = _read_json(te_path)
        if te_doc is not None:
            raw = te_doc.get("transfer_entropy")
            try:
                te_val = float(raw) if raw is not None else None
                te_source = str(te_path.resolve())
            except (TypeError, ValueError):
                te_val = None

    phase = _pathology_phase_hypo(bridge if isinstance(bridge, dict) else {})
    te_band = _te_band(te_val)
    rows = _mapping_rows(phase, te_band)

    doc: dict[str, Any] = {
        "schema": "sasang_pathology_te_mapping_hypo_v1",
        "version": "1.1.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "label": "[HYPO] Pathology phase ↔ TE prior band — sandbox only; weight_hint always 0.",
        "mapping_mode": "sandbox_observation_only",
        "track_a_live_routing_forbidden": True,
        "auto_weight_adjustment_forbidden": True,
        "inputs": {
            "bundle_path": str(args.bundle.resolve()) if args.bundle else None,
            "interpretive_path": str(args.interpretive.resolve()) if args.interpretive else None,
            "interpretive_bridge_available": bool(isinstance(bridge, dict) and bridge.get("available")),
            "transfer_entropy": te_val,
            "transfer_entropy_source": te_source,
            "te_band": te_band,
            "pathology_phase_hypo": phase,
        },
        "mapping_rows": rows,
        "mapping_grid_v1": {
            "phases": list(PHASE_LABELS),
            "te_bands": list(TE_BANDS),
            "cells_n": len(PHASE_LABELS) * len(TE_BANDS),
            "all_weight_hint_zero": True,
        },
        "next_steps_ko": [
            "N=400 압축 샌드박스와 별도 — 이 매핑은 예언 hit rate 승격 증거가 아님",
            "TE 실측은 unified_trading_monitor 산출 JSON을 --te-json으로 주입",
            "Track A 합선은 human sign-off + 별도 게이트 필요",
        ],
        "pointers": {
            "paradigm_factcheck": "docs/final/artifacts/paradigm_factcheck_v1.json",
            "interpretive_bundle": "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json",
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} phase={phase} te_band={te_band}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
