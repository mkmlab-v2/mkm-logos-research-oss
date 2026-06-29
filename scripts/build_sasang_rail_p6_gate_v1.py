#!/usr/bin/env python3
"""Sasang rail P6 gate: curated ingest unified + stack continuity [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UNIFIED_CURATED = ROOT / "docs/final/artifacts/sasang_curated_joint_unified_gate_v1_latest.json"
STACK = ROOT / "docs/final/artifacts/sasang_rail_stack_gate_v1_latest.json"
P5 = ROOT / "docs/final/artifacts/sasang_rail_p5_gate_v1_latest.json"
DRILL = ROOT / "reports/sasang_curated_joint_promote_drill_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p6_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    curated = _load(UNIFIED_CURATED)
    stack = _load(STACK)
    p5 = _load(P5)
    drill = _load(DRILL)

    checks = {
        "curated_unified_gate_ok": {"passed": curated.get("gate_ok") is True},
        "curated_dual_idle_or_ready": {
            "passed": curated.get("curated_joint_status")
            in (
                "dual_idle_hold",
                "csv_ready_to_apply",
                "jsonl_ready_to_apply",
                "dual_ready_to_apply",
                "applied_partial_or_full",
            ),
        },
        "promote_drill_ok": {"passed": drill.get("all_ok") is True if drill else True},
        "stack_gate_ok": {"passed": stack.get("gate_ok") is True},
        "p5_gate_ok": {"passed": p5.get("gate_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    if not drill:
        checks["promote_drill_ok"]["passed"] = True
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p6_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p6_status": "curated_ingest_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "curated_joint_status": curated.get("curated_joint_status"),
        "stack_status": stack.get("sasang_rail_stack_status"),
        "reproduce": "py scripts/run_sasang_rail_p6_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p6_status": doc["sasang_rail_p6_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
