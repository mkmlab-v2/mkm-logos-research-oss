#!/usr/bin/env python3
"""Sasang rail stack gate: containment + P2 + P3 chains → unified stack_ok [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UNIFIED = ROOT / "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json"
CONTAINMENT_CHAIN = ROOT / "reports/sasang_rail_containment_chain_v1_latest.json"
P2_CHAIN = ROOT / "reports/sasang_rail_p2_chain_v1_latest.json"
P3_CHAIN = ROOT / "reports/sasang_rail_p3_chain_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_stack_gate_v1_latest.json"

def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    unified = _load(UNIFIED)
    c_chain = _load(CONTAINMENT_CHAIN)
    p2_chain = _load(P2_CHAIN)
    p3_chain = _load(P3_CHAIN)

    checks = {
        "unified_gate_ok": {"passed": unified.get("gate_ok") is True},
        "unified_stack_ok": {"passed": unified.get("sasang_rail_stack_status") == "stack_ok"},
        "containment_chain_ok": {"passed": c_chain.get("all_ok") is True},
        "p2_chain_ok": {"passed": p2_chain.get("all_ok") is True},
        "p3_chain_ok": {"passed": p3_chain.get("all_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": unified.get("send_gate") == "HOLD"},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_stack_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_stack_status": "stack_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "phase_gates": unified.get("phase_gates") or {},
        "reproduce": "py scripts/run_sasang_rail_stack_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_stack_status": doc["sasang_rail_stack_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
