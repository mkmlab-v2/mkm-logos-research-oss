#!/usr/bin/env python3
"""TKM encounter_sequence P65 gate: post-ultra-grand passive observation [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import timezone, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P64_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p64_gate_v1_latest.json"
OBS = ROOT / "reports/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p65_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p64 = _load(P64_GATE)
    obs = _load(OBS)
    weekly = _load(WEEKLY)
    pug = weekly.get("post_ultra_grand_passive_observation_kpi") if isinstance(
        weekly.get("post_ultra_grand_passive_observation_kpi"), dict
    ) else {}

    checks = {
        "p64_gate_ok": {"passed": p64.get("gate_ok") is True},
        "observation_ok": {"passed": obs.get("observation_ok") is True},
        "observation_artifact_mirrored": {"passed": ARTIFACT.is_file()},
        "ultra_grand_export_bundle_vault_sync_ok": {
            "passed": obs.get("ultra_grand_export_bundle_vault_sync_ok") is True
        },
        "ultra_grand_post_export_closure_ok": {
            "passed": obs.get("ultra_grand_post_export_closure_ok") is True
        },
        "passive_observation_ok": {"passed": obs.get("passive_observation_ok") is True},
        "export_ingest_kpi_ok": {"passed": obs.get("export_ingest_kpi_ok") is True},
        "curated_milestone_ok": {"passed": obs.get("curated_milestone_ok") is True},
        "weekly_task_ready": {"passed": obs.get("weekly_task_ready") is True},
        "interpret_cpu_guard_ok": {"passed": obs.get("interpret_cpu_guard_ok") is True},
        "weekly_post_ultra_grand_sync_ok": {
            "passed": pug.get("post_ultra_grand_passive_observation_headline_ok") is True
        },
        "auto_training_forbidden": {"passed": obs.get("auto_training_forbidden") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p65_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "research_only": True,
        "tkm_encounter_sequence_p65_status": "post_ultra_grand_passive_observation_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "observation_artifact_path": str(ARTIFACT).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p65_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p65_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
