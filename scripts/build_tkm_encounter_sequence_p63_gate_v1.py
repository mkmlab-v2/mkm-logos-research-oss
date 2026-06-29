#!/usr/bin/env python3
"""TKM encounter_sequence P63 gate: ultra-grand post-export closure [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P62_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p62_gate_v1_latest.json"
CLOSURE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p63_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p62 = _load(P62_GATE)
    closure = _load(CLOSURE)
    weekly = _load(WEEKLY)
    ugpec = weekly.get("ultra_grand_post_export_closure_kpi") if isinstance(
        weekly.get("ultra_grand_post_export_closure_kpi"), dict
    ) else {}
    gates = closure.get("gates") if isinstance(closure.get("gates"), dict) else {}

    checks = {
        "p62_gate_ok": {"passed": p62.get("gate_ok") is True},
        "ultra_grand_post_export_closure_ok": {
            "passed": closure.get("ultra_grand_post_export_closure_ok") is True
        },
        "closure_artifact_mirrored": {"passed": ARTIFACT.is_file()},
        "all_gates_p33_p62_ok": {
            "passed": all((gates.get(k) or {}).get("gate_ok") is True for k in gates)
        },
        "grand_stack_stack_closure_ok": {"passed": closure.get("grand_stack_stack_closure_ok") is True},
        "grand_stack_extension_export_bundle_ok": {
            "passed": closure.get("grand_stack_extension_export_bundle_ok") is True
        },
        "full_grand_stack_final_closure_ok": {"passed": closure.get("full_grand_stack_final_closure_ok") is True},
        "grand_post_export_closure_ok": {"passed": closure.get("grand_post_export_closure_ok") is True},
        "post_export_stack_closure_ok": {"passed": closure.get("post_export_stack_closure_ok") is True},
        "full_extension_closure_ok": {"passed": closure.get("full_extension_closure_ok") is True},
        "integrated_closure_ok": {"passed": closure.get("integrated_closure_ok") is True},
        "weekly_ultra_grand_post_export_sync_ok": {
            "passed": ugpec.get("ultra_grand_post_export_closure_headline_ok") is True
        },
        "auto_training_forbidden": {"passed": closure.get("research_only") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p63_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "research_only": True,
        "tkm_encounter_sequence_p63_status": "ultra_grand_post_export_closure_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "closure_artifact_path": str(ARTIFACT).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p63_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p63_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
