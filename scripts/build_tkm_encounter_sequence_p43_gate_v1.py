#!/usr/bin/env python3
"""TKM encounter_sequence P43 gate: GPU+passive+curated observability [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P42_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p42_gate_v1_latest.json"
ROLLUP = ROOT / "reports/tkm_encounter_sequence_p43_observability_rollup_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p43_observability_rollup_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p43_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p42 = _load(P42_GATE)
    rollup = _load(ROLLUP)
    weekly = _load(WEEKLY)
    ob = weekly.get("p43_observability_kpi") if isinstance(weekly.get("p43_observability_kpi"), dict) else {}

    checks = {
        "p42_gate_ok": {"passed": p42.get("gate_ok") is True},
        "observability_ok": {"passed": rollup.get("observability_ok") is True},
        "rollup_artifact_mirrored": {"passed": ARTIFACT.is_file()},
        "passive_observation_ok": {"passed": rollup.get("passive_observation_ok") is True},
        "interpret_cpu_guard_ok": {"passed": rollup.get("interpret_cpu_guard_ok") is True},
        "curated_review_mark_ok": {"passed": rollup.get("curated_review_mark_ok") is True},
        "curated_reviewed_min_ok": {
            "passed": int((rollup.get("curated_review_counts") or {}).get("reviewed") or 0) >= 1
        },
        "weekly_observability_sync_ok": {"passed": ob.get("p43_observability_headline_ok") is True},
        "auto_training_forbidden": {"passed": rollup.get("auto_training_forbidden") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p43_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "research_only": True,
        "tkm_encounter_sequence_p43_status": "gpu_passive_curated_observation_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "interpret_gpu_train_attempted": rollup.get("interpret_gpu_train_attempted"),
        "interpret_gpu_train_ok": rollup.get("interpret_gpu_train_ok"),
        "rollup_artifact_path": str(ARTIFACT).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p43_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p43_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
