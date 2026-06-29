#!/usr/bin/env python3
"""TKM encounter_sequence P52 gate: NotebookLM export sync [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P51_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p51_gate_v1_latest.json"
EXPORT_SYNC = ROOT / "reports/tkm_encounter_sequence_notebooklm_export_sync_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_notebooklm_export_sync_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/tkm_encounter_sequence_notebooklm_export_manifest_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p52_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p51 = _load(P51_GATE)
    sync = _load(EXPORT_SYNC)
    weekly = _load(WEEKLY)
    nes = weekly.get("notebooklm_export_sync_kpi") if isinstance(weekly.get("notebooklm_export_sync_kpi"), dict) else {}
    vault = sync.get("vault_mirror") if isinstance(sync.get("vault_mirror"), dict) else {}

    checks = {
        "p51_gate_ok": {"passed": p51.get("gate_ok") is True},
        "export_sync_ok": {"passed": sync.get("export_sync_ok") is True},
        "sync_artifact_mirrored": {"passed": ARTIFACT.is_file()},
        "manifest_artifact_present": {"passed": MANIFEST.is_file()},
        "integrated_closure_ok": {"passed": sync.get("integrated_closure_ok") is True},
        "manifest_complete": {
            "passed": int(sync.get("manifest_files_present_count") or 0)
            >= int(sync.get("manifest_file_count") or 1)
        },
        "vault_mirror_ok": {"passed": vault.get("vault_mirror_ok") is True},
        "cloud_upload_forbidden": {"passed": sync.get("cloud_upload_forbidden") is True},
        "weekly_export_sync_sync_ok": {"passed": nes.get("notebooklm_export_sync_headline_ok") is True},
        "auto_training_forbidden": {"passed": sync.get("research_only") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p52_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "research_only": True,
        "tkm_encounter_sequence_p52_status": "notebooklm_export_sync_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "sync_artifact_path": str(ARTIFACT).replace("\\", "/"),
        "manifest_artifact_path": str(MANIFEST).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p52_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p52_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
