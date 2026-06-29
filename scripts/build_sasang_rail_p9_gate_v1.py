#!/usr/bin/env python3
"""Sasang rail P9 gate: literature supervised + non-dummy benchmark composition [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LIT_GATE = ROOT / "docs/final/artifacts/sasang_literature_supervised_gate_v1_latest.json"
COMP = ROOT / "reports/sasang_joint_benchmark_composition_v1_latest.json"
MASTER = ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p9_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    lit = _load(LIT_GATE)
    comp = _load(COMP)
    master = _load(MASTER)

    checks = {
        "literature_supervised_gate_ok": {"passed": lit.get("gate_ok") is True},
        "literature_export_ok": {"passed": lit.get("literature_supervised_status") == "export_ok"},
        "benchmark_composition_ok": {"passed": comp.get("composition_ok") is True},
        "non_dummy_rows_present": {"passed": int(comp.get("rows_non_dummy") or 0) >= 1},
        "master_gate_ok": {"passed": master.get("gate_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p9_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p9_status": "literature_data_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "literature_supervised_rows": lit.get("rows"),
        "benchmark_rows_non_dummy": comp.get("rows_non_dummy"),
        "reproduce": "py scripts/run_sasang_rail_p9_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p9_status": doc["sasang_rail_p9_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
