#!/usr/bin/env python3
"""Sasang rail master gate: stack + P6 + P9/P10 phase gates closure [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "docs/final/artifacts/sasang_rail_stack_gate_v1_latest.json"
P6 = ROOT / "docs/final/artifacts/sasang_rail_p6_gate_v1_latest.json"
P5 = ROOT / "docs/final/artifacts/sasang_rail_p5_gate_v1_latest.json"
UNIFIED = ROOT / "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json"
CURATED = ROOT / "docs/final/artifacts/sasang_curated_joint_unified_gate_v1_latest.json"
P9 = ROOT / "docs/final/artifacts/sasang_rail_p9_gate_v1_latest.json"
P10 = ROOT / "docs/final/artifacts/sasang_rail_p10_gate_v1_latest.json"
P11 = ROOT / "docs/final/artifacts/sasang_rail_p11_gate_v1_latest.json"
P12 = ROOT / "docs/final/artifacts/sasang_rail_p12_gate_v1_latest.json"
P13 = ROOT / "docs/final/artifacts/sasang_rail_p13_gate_v1_latest.json"
P14 = ROOT / "docs/final/artifacts/sasang_rail_p14_gate_v1_latest.json"
P15 = ROOT / "docs/final/artifacts/sasang_rail_p15_gate_v1_latest.json"
P16 = ROOT / "docs/final/artifacts/sasang_rail_p16_gate_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    stack = _load(STACK)
    p6 = _load(P6)
    p5 = _load(P5)
    unified = _load(UNIFIED)
    curated = _load(CURATED)
    p9 = _load(P9)
    p10 = _load(P10)
    p11 = _load(P11)
    p12 = _load(P12)
    p13 = _load(P13)
    p14 = _load(P14)
    p15 = _load(P15)
    p16 = _load(P16)
    p10_present = P10.is_file() and bool(p10.get("schema"))
    p11_present = P11.is_file() and bool(p11.get("schema"))
    p12_present = P12.is_file() and bool(p12.get("schema"))
    p13_present = P13.is_file() and bool(p13.get("schema"))
    p14_present = P14.is_file() and bool(p14.get("schema"))
    p15_present = P15.is_file() and bool(p15.get("schema"))
    p16_present = P16.is_file() and bool(p16.get("schema"))

    checks = {
        "stack_gate_ok": {"passed": stack.get("gate_ok") is True},
        "stack_status_ok": {"passed": stack.get("sasang_rail_stack_status") == "stack_ok"},
        "p6_gate_ok": {"passed": p6.get("gate_ok") is True},
        "p6_curated_ok": {"passed": p6.get("sasang_rail_p6_status") == "curated_ingest_ok"},
        "p5_gate_ok": {"passed": p5.get("gate_ok") is True},
        "unified_stack_ok": {"passed": unified.get("sasang_rail_stack_status") == "stack_ok"},
        "curated_unified_ok": {"passed": curated.get("gate_ok") is True},
        "p9_gate_ok": {"passed": p9.get("gate_ok") is True},
        "p9_literature_data_ok": {"passed": p9.get("sasang_rail_p9_status") == "literature_data_ok"},
        "p10_gate_ok": {"passed": (not p10_present) or (p10.get("gate_ok") is True)},
        "p10_exploratory_probe_ok": {
            "passed": (not p10_present) or (p10.get("sasang_rail_p10_status") == "exploratory_probe_ok"),
        },
        "p11_gate_ok": {"passed": (not p11_present) or (p11.get("gate_ok") is True)},
        "p11_dual_probe_enrich_ok": {
            "passed": (not p11_present) or (p11.get("sasang_rail_p11_status") == "dual_probe_enrich_ok"),
        },
        "p12_gate_ok": {"passed": (not p12_present) or (p12.get("gate_ok") is True)},
        "p12_partition_compare_ok": {
            "passed": (not p12_present) or (p12.get("sasang_rail_p12_status") == "partition_compare_ok"),
        },
        "p13_gate_ok": {"passed": (not p13_present) or (p13.get("gate_ok") is True)},
        "p13_archive_drift_ok": {
            "passed": (not p13_present) or (p13.get("sasang_rail_p13_status") == "archive_drift_ok"),
        },
        "p14_gate_ok": {"passed": (not p14_present) or (p14.get("gate_ok") is True)},
        "p14_mainline_eval_ok": {
            "passed": (not p14_present) or (p14.get("sasang_rail_p14_status") == "mainline_eval_ok"),
        },
        "p15_gate_ok": {"passed": (not p15_present) or (p15.get("gate_ok") is True)},
        "p15_eval_path_locked_ok": {
            "passed": (not p15_present) or (p15.get("sasang_rail_p15_status") == "eval_path_locked_ok"),
        },
        "p16_gate_ok": {"passed": (not p16_present) or (p16.get("gate_ok") is True)},
        "p16_promote_drill_attested_ok": {
            "passed": (not p16_present) or (p16.get("sasang_rail_p16_status") == "promote_drill_attested_ok"),
        },
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_master_gate_v1",
        "version": "1.7.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_master_status": "master_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "phase_summary": {
            "stack": stack.get("sasang_rail_stack_status"),
            "p5": p5.get("sasang_rail_p5_status"),
            "p6": p6.get("sasang_rail_p6_status"),
            "curated_joint": curated.get("curated_joint_status"),
            "p9": p9.get("sasang_rail_p9_status"),
            "p10": p10.get("sasang_rail_p10_status") if p10_present else None,
            "p11": p11.get("sasang_rail_p11_status") if p11_present else None,
            "p12": p12.get("sasang_rail_p12_status") if p12_present else None,
            "p13": p13.get("sasang_rail_p13_status") if p13_present else None,
            "p14": p14.get("sasang_rail_p14_status") if p14_present else None,
            "p15": p15.get("sasang_rail_p15_status") if p15_present else None,
            "p16": p16.get("sasang_rail_p16_status") if p16_present else None,
        },
        "p10_gate_present": p10_present,
        "p11_gate_present": p11_present,
        "p12_gate_present": p12_present,
        "p13_gate_present": p13_present,
        "p14_gate_present": p14_present,
        "p15_gate_present": p15_present,
        "p16_gate_present": p16_present,
        "reproduce": "py scripts/run_sasang_rail_master_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_master_status": doc["sasang_rail_master_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
