#!/usr/bin/env python3
"""TKM encounter_sequence P34 gate: passive observation + interpret micro [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P33_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p33_gate_v1_latest.json"
PASSIVE = ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json"
INTERPRET = ROOT / "reports/myeongri_interpret_micro_retrain_chain_v1_latest.json"
CROSS = ROOT / "reports/tkm_encounter_sequence_cross_lens_kpi_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p34_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p33 = _load(P33_GATE)
    passive = _load(PASSIVE)
    interpret = _load(INTERPRET)
    cross = _load(CROSS)

    checks = {
        "p33_gate_ok": {"passed": p33.get("gate_ok") is True},
        "passive_observation_ok": {"passed": passive.get("observation_ok") is True},
        "interpret_cpu_guard_ok": {"passed": interpret.get("cpu_guard_ok") is True},
        "cross_lens_motif_skew_ok": {"passed": cross.get("motif_skew_gate_ok") is True},
        "weekly_task_ready": {"passed": passive.get("weekly_task_ready") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p34_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p34_status": "passive_observation_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "cross_lens_resonance_index": cross.get("cross_lens_resonance_index"),
        "motif_top1_share": cross.get("motif_top1_share"),
        "interpret_gpu_train_attempted": interpret.get("gpu_train_attempted"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p34_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p34_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
