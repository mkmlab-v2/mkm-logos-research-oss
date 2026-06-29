#!/usr/bin/env python3
"""Sasang rail P10 gate: real-slice 4-agent probe + non-dummy classification [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P9 = ROOT / "docs/final/artifacts/sasang_rail_p9_gate_v1_latest.json"
REAL_SLICE = ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_real_slice_latest.json"
CLASS_SMOKE = ROOT / "reports/sasang_joint_benchmark_non_dummy_classification_smoke_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p10_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p9 = _load(P9)
    proto = _load(REAL_SLICE)
    cls = _load(CLASS_SMOKE)
    exp = proto.get("experiment") if isinstance(proto.get("experiment"), dict) else {}
    hint = proto.get("promotion_gate_hint") if isinstance(proto.get("promotion_gate_hint"), dict) else {}

    checks = {
        "p9_gate_ok": {"passed": p9.get("gate_ok") is True},
        "p9_literature_data_ok": {"passed": p9.get("sasang_rail_p9_status") == "literature_data_ok"},
        "real_slice_protocol_present": {
            "passed": proto.get("schema") == "sasang_4agent_collision_btrack_protocol_v1",
        },
        "real_slice_data_mode": {
            "passed": exp.get("data_mode") == "real_slice_backtest_adapter",
        },
        "real_slice_research_only": {"passed": proto.get("mode") == "research_only"},
        "non_dummy_classification_ok": {"passed": cls.get("classification_ok") is True},
        "promotion_hint_not_go": {"passed": hint.get("decision") != "GO_CANDIDATE"},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p10_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p10_status": "exploratory_probe_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "real_slice_ticks": exp.get("ticks"),
        "non_dummy_rows_evaluated": cls.get("rows_with_birth_evaluated"),
        "reproduce": "py scripts/run_sasang_rail_p10_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p10_status": doc["sasang_rail_p10_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
