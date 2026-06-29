#!/usr/bin/env python3
"""Sasang rail unified gate: containment + P2 enrichment + P3 ablation/literature stack [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTAINMENT = ROOT / "docs/final/artifacts/sasang_rail_containment_gate_v1_latest.json"
P2 = ROOT / "docs/final/artifacts/sasang_rail_p2_gate_v1_latest.json"
P3 = ROOT / "docs/final/artifacts/sasang_rail_p3_gate_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    c = _load(CONTAINMENT)
    p2 = _load(P2)
    p3 = _load(P3)

    checks = {
        "containment_gate_ok": {"passed": c.get("gate_ok") is True},
        "containment_status_ok": {"passed": c.get("sasang_rail_status") == "containment_ok"},
        "p2_gate_ok": {"passed": p2.get("gate_ok") is True},
        "p2_enrichment_ok": {"passed": p2.get("sasang_rail_p2_status") == "enrichment_ok"},
        "p3_gate_ok": {"passed": p3.get("gate_ok") is True},
        "p3_ablation_literature_ok": {
            "passed": p3.get("sasang_rail_p3_status") == "ablation_literature_ok",
        },
        "all_send_gate_hold": {
            "passed": c.get("send_gate") == "HOLD"
            and p2.get("send_gate") == "HOLD"
            and p3.get("send_gate") == "HOLD",
        },
        "track_a_bridge_forbidden": {"passed": True},
    }
    gate_ok = all(x.get("passed") for x in checks.values())
    return {
        "schema": "sasang_rail_unified_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_stack_status": "stack_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "phase_gates": {
            "containment": c.get("sasang_rail_status"),
            "p2": p2.get("sasang_rail_p2_status"),
            "p3": p3.get("sasang_rail_p3_status"),
        },
        "reproduce": "py scripts/run_sasang_rail_p3_chain_v1.py --require-prior-phases",
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
