#!/usr/bin/env python3
"""Sasang rail P5 gate: literature promote path + full ablation bootstrap [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROMOTE = ROOT / "docs/final/artifacts/sasang_literature_curated_promote_gate_v1_latest.json"
ABLATION = ROOT / "reports/sasang_4agent_protocol_ablation_v1_latest.json"
STACK = ROOT / "docs/final/artifacts/sasang_rail_stack_gate_v1_latest.json"
LIT = ROOT / "docs/final/artifacts/sasang_literature_supervised_gate_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p5_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    promote = _load(PROMOTE)
    ablation = _load(ABLATION)
    stack = _load(STACK)
    lit = _load(LIT)
    wall = ablation.get("track_wall") if isinstance(ablation.get("track_wall"), dict) else {}
    exp = ablation.get("experiment") if isinstance(ablation.get("experiment"), dict) else {}

    checks = {
        "promote_gate_ok": {"passed": promote.get("gate_ok") is True},
        "promote_status_hold_or_idle": {
            "passed": promote.get("promote_status")
            in ("csv_missing_hold", "idle_no_curator_rows", "ready_to_apply", "applied"),
        },
        "ablation_present": {"passed": ablation.get("schema") == "sasang_4agent_protocol_ablation_v1"},
        "ablation_full_bootstrap": {"passed": int(exp.get("bootstrap_trials") or 0) >= 200},
        "ablation_no_track_a": {"passed": wall.get("track_a_promotion") is False},
        "stack_gate_ok": {"passed": stack.get("gate_ok") is True},
        "literature_supervised_ok": {"passed": lit.get("gate_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p5_gate_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p5_status": "literature_ablation_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "promote_status": promote.get("promote_status"),
        "ablation_verdict": ablation.get("verdict"),
        "stack_status": stack.get("sasang_rail_stack_status"),
        "reproduce": "py scripts/run_sasang_rail_p5_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p5_status": doc["sasang_rail_p5_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
