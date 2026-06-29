#!/usr/bin/env python3
"""Build dual-axis promotion gap report for delegation lane (raw metrics only)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
PACKET = ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
RECONCILE = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_coordinator_active_eval_axis_reconcile_v1_latest.json"
)
DEFAULT_OUT = ROOT / "reports/delegation_nextgen_dual_axis_gap_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    active = _load(ACTIVE)
    packet = _load(PACKET) if PACKET.is_file() else {}
    reconcile = _load(RECONCILE) if RECONCILE.is_file() else {}

    frozen = packet.get("frozen_active_metrics") or {
        "global_token_saving_rate": active.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": active.get("avg_reconstruction_fidelity_jaccard"),
    }
    fs = float(frozen.get("global_token_saving_rate") or 0)
    fj = float(frozen.get("avg_reconstruction_fidelity_jaccard") or 0)

    candidates = packet.get("candidates") if isinstance(packet.get("candidates"), list) else []
    golden40 = [
        c
        for c in candidates
        if isinstance(c.get("metrics"), dict) and c["metrics"].get("case_count") == 40
    ]
    best_beat = None
    for c in golden40:
        bc = c.get("beat_check") if isinstance(c.get("beat_check"), dict) else {}
        if bc.get("beat_frozen"):
            best_beat = c
            break

    selected_id = packet.get("selected_arm")
    selected = next((c for c in candidates if c.get("arm_id") == selected_id), None)

    out: dict[str, Any] = {
        "schema": "delegation_nextgen_dual_axis_gap_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "active_frozen": {
            "global_token_saving_rate": fs,
            "avg_reconstruction_fidelity_jaccard": fj,
        },
        "selected_arm": selected_id,
        "selected_delta": selected.get("beat_check") if selected else None,
        "any_dual_axis_beat": best_beat is not None,
        "export_prep_ready": packet.get("export_prep_ready"),
        "apply_forbidden": packet.get("apply_forbidden", True),
        "axis_reconcile": {
            "dual_axis_beat": reconcile.get("dual_axis_beat"),
            "active_saving": reconcile.get("active_saving"),
            "hybrid_payload_saving": reconcile.get("hybrid_payload_saving"),
            "conflation_guard": reconcile.get("conflation_guard"),
        },
        "promotion_gate": "human_signoff_required",
        "headline_rule": "longform-only beat excluded from MS/Track A headlines",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.out_json), "any_dual_axis_beat": out["any_dual_axis_beat"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
