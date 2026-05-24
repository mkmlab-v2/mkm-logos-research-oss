#!/usr/bin/env python3
"""Apply commander in-chat approval: signoff, lock, candidate refresh, checklist, packet, gut_brain."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    o = json.loads(path.read_text(encoding="utf-8"))
    return o if isinstance(o, dict) else {}


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(ROOT))
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def _refresh_track_a_candidate(gate: dict[str, Any], out: Path, lock_path: Path) -> None:
    tracks = gate.get("tracks") or {}
    lens_gates = ((tracks.get("per_date_lens") or {}).get("gates") or [])
    inst_gates = ((tracks.get("instrument_combo") or {}).get("gates") or [])

    def _mean(gates: list) -> float | None:
        for g in gates:
            if isinstance(g, dict) and g.get("gate_id", "").endswith("mean_test_accuracy"):
                obs = g.get("observed") or {}
                v = obs.get("mean_test_accuracy")
                return float(v) if v is not None else None
        return None

    doc = {
        "schema": "prophecy_track_a_candidate_v1",
        "generated_at_utc": _now(),
        "status": "APPROVED_CANDIDATE",
        "source_track": "B",
        "promotion_mode": "human_approved_candidate_only",
        "human_approval": {
            "approved_at_utc": _now(),
            "approval_channel": "cursor_in_chat",
            "ensemble_v2_lane": True,
        },
        "candidate_gate": {
            "promotion_track_mode": (gate.get("inputs") or {}).get("promotion_track_mode"),
            "strict_pass_streak": gate.get("strict_pass_streak"),
            "strict_passed": gate.get("strict_passed"),
            "combined_all_passed": gate.get("combined_all_passed"),
        },
        "candidate_metrics": {
            "lens_mean_test_accuracy": _mean(lens_gates),
            "instrument_mean_test_accuracy": _mean(inst_gates),
            "lens_walkforward_gates": lens_gates,
            "instrument_walkforward_gates": inst_gates,
        },
        "runtime_constraints": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "requires_human_review_each_release": True,
        },
        "evidence": {
            "manual_lock": str(lock_path.resolve()),
            "promotion_gate_strict": "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json",
            "promotion_gate_recommended_chain": "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json",
            "evidence_pack": "docs/final/artifacts/prophecy_gate_evidence_pack_v1_latest.json",
            "human_signoff": "docs/final/artifacts/prophecy_release_human_signoff_v1_latest.json",
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument(
        "--note",
        default="지휘관 in-chat 승인 (2026-05-15): ensemble v2 recommended_chain strict gates.",
    )
    args = ap.parse_args()
    py = sys.executable
    gate_strict = ART / "prophecy_promotion_gates_v1_latest.json"
    gate_rec = REPORTS / "prophecy_promotion_gates_recommended_chain_v1_latest.json"
    if gate_rec.is_file():
        ART.mkdir(parents=True, exist_ok=True)
        gate_strict.write_text(gate_rec.read_text(encoding="utf-8"), encoding="utf-8")

    _run(
        [
            py,
            "scripts/record_prophecy_release_human_signoff_v1.py",
            "--reviewer",
            args.reviewer,
            "--decision",
            "APPROVED",
            "--note",
            args.note,
            "--evidence-bundle",
            "docs/final/artifacts/prophecy_gate_evidence_pack_v1_latest.json",
        ]
    )
    _run(
        [
            py,
            "scripts/lock_prophecy_manual_promotion_decision_v1.py",
            "--reviewer",
            args.reviewer,
            "--decision-note",
            args.note,
            "--promotion-gate",
            str(gate_strict),
        ]
    )
    gate = _load(gate_strict)
    lock_path = ART / "prophecy_manual_promotion_decision_lock_v1_latest.json"
    _refresh_track_a_candidate(gate, ART / "prophecy_track_a_candidate_v1_latest.json", lock_path)

    pre = _load(ART / "prophecy_track_a_candidate_pre_review_v1_latest.json")
    if pre:
        pre["status"] = "HUMAN_APPROVED"
        pre["decision_snapshot"] = "APPROVED_IN_CHAT"
        pre["human_approved_at_utc"] = _now()
        pre["blockers"] = []
        (ART / "prophecy_track_a_candidate_pre_review_v1_latest.json").write_text(
            json.dumps(pre, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    _run(
        [
            py,
            "scripts/build_prophecy_approved_candidate_release_checklist_v1.py",
            "--promotion-gate",
            str(gate_strict),
        ]
    )
    _run([py, "scripts/build_prophecy_release_signoff_packet_v1.py"])
    _run(
        [
            py,
            "scripts/refresh_gut_brain_btrack_promotion_status_v1.py",
            "--gates-json",
            str(gate_rec if gate_rec.is_file() else gate_strict),
        ]
    )

    gut = _load(ART / "gut_brain_agent_constitution_promotion_v1_latest.json")
    layers = gut.get("promotion_layers") or {}
    btrack = layers.get("btrack_numeric_to_track_a") or {}
    if isinstance(btrack, dict):
        btrack["status"] = "human_approved_track_a_candidate"
        btrack["human_approved_at_utc"] = _now()
        btrack["human_signoff_artifact"] = "docs/final/artifacts/prophecy_release_human_signoff_v1_latest.json"
        layers["btrack_numeric_to_track_a"] = btrack
        gut["promotion_layers"] = layers
        gut["generated_at_utc"] = _now()
        (ART / "gut_brain_agent_constitution_promotion_v1_latest.json").write_text(
            json.dumps(gut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print("OK human approval applied (B-track candidate; live/auto-bridge still off)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
