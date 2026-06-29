#!/usr/bin/env python3
"""TKM encounter_sequence P40 gate: passive integrated observation rollup [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P39_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p39_gate_v1_latest.json"
ROLLUP = ROOT / "reports/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p40_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p39 = _load(P39_GATE)
    rollup = _load(ROLLUP)
    weekly = _load(WEEKLY)
    pi = weekly.get("passive_integrated_rollup_kpi") if isinstance(weekly.get("passive_integrated_rollup_kpi"), dict) else {}

    checks = {
        "p39_gate_ok": {"passed": p39.get("gate_ok") is True},
        "integrated_rollup_ok": {"passed": rollup.get("integrated_ok") is True},
        "rollup_artifact_mirrored": {"passed": ARTIFACT.is_file()},
        "passive_observation_ok": {"passed": rollup.get("passive_observation_ok") is True},
        "interpret_cpu_guard_ok": {"passed": rollup.get("interpret_cpu_guard_ok") is True},
        "curated_learning_ack_ok": {"passed": rollup.get("curated_learning_ack_ok") is True},
        "weekly_integrated_sync_ok": {"passed": pi.get("passive_integrated_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p40_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p40_status": "passive_integrated_observation_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "interpret_gpu_train_attempted": rollup.get("interpret_gpu_train_attempted"),
        "interpret_gpu_train_ok": rollup.get("interpret_gpu_train_ok"),
        "rollup_artifact_path": str(ARTIFACT).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p40_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p40_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
