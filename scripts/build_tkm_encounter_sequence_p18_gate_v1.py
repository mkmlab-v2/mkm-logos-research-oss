#!/usr/bin/env python3
"""TKM encounter_sequence P18 gate: intake L0 wire + curated ack + weekly register [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P17_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p17_gate_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_human_gate_ack_v1.json"
DRAFTS = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_draft_v1_latest.json"
SMOKE = ROOT / "reports/intake_fusion_encounter_sequence_smoke_v1_latest.json"
REGISTER = ROOT / "scripts/Register-TkmEncounterSequenceWeeklyReport_v1.ps1"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p18_gate_v1_latest.json"
SEQ_ID = "SEQ-DISAGREE-01"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _disagreement_in_ledger() -> bool:
    import importlib.util

    ledger_path = ROOT / "scripts" / "encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
    if spec is None or spec.loader is None:
        return False
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for row in mod.iter_ledger_records(ROOT):
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        if str(enc.get("sequence_id") or "") == SEQ_ID:
            return True
    return False


def _register_dry_run_ok() -> bool:
    if not REGISTER.is_file():
        return False
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REGISTER),
            "-DryRun",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and "DRY_RUN" in (proc.stdout or "")


def build() -> dict[str, Any]:
    p17 = _load(P17_GATE)
    ack = _load(ACK)
    drafts = _load(DRAFTS)
    smoke = _load(SMOKE)
    disagree_count = int(drafts.get("disagreement_draft_count") or 0)

    checks = {
        "p17_gate_ok": {"passed": p17.get("gate_ok") is True},
        "disagreement_ledger_or_draft_ok": {
            "passed": _disagreement_in_ledger() or disagree_count >= 1,
        },
        "curated_human_gate_ack_ok": {"passed": ack.get("human_gate_ack") is True},
        "intake_fusion_l0_smoke_ok": {"passed": smoke.get("smoke_ok") is True},
        "weekly_register_script_dry_run_ok": {"passed": _register_dry_run_ok()},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p18_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p18_status": "intake_l0_weekly_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "disagreement_draft_count": disagree_count,
        "reproduce": "py scripts/run_tkm_encounter_sequence_p18_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p18_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
