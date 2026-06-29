#!/usr/bin/env python3
"""Sasang rail P14 gate: mainline prune + attested eval + drift alert [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P13 = ROOT / "docs/final/artifacts/sasang_rail_p13_gate_v1_latest.json"
PRUNE = ROOT / "reports/sasang_joint_benchmark_mainline_prune_v1_latest.json"
CLASS_GATE = ROOT / "docs/final/artifacts/sasang_attested_only_classification_gate_v1_latest.json"
CLINICAL = ROOT / "docs/final/artifacts/sasang_commander_attested_clinical_template_gate_v1_latest.json"
ALERT = ROOT / "reports/sasang_4agent_dual_probe_weekly_drift_alert_v1_latest.json"
PARTITION = ROOT / "reports/sasang_joint_benchmark_tier_partition_v1_latest.json"
BENCH = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p14_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_dummy(row: dict[str, Any]) -> bool:
    pid = str(row.get("person_id") or "")
    disp = str(row.get("display_name") or "")
    if "dummy" in pid.lower() or "dummy" in disp.lower():
        return True
    if "DUMMYCSV" in pid or "DUMMYJSONL" in pid:
        return True
    if "[DUMMY]" in disp:
        return True
    return False


def _mainline_dummy_count() -> int:
    n = 0
    if BENCH.is_file():
        for line in BENCH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            if _is_dummy(json.loads(line)):
                n += 1
    return n


def build() -> dict[str, Any]:
    p13 = _load(P13)
    prune = _load(PRUNE)
    class_gate = _load(CLASS_GATE)
    clinical = _load(CLINICAL)
    alert = _load(ALERT)
    partition = _load(PARTITION)
    mainline_dummy = _mainline_dummy_count()

    checks = {
        "p13_gate_ok": {"passed": p13.get("gate_ok") is True},
        "p13_archive_drift_ok": {"passed": p13.get("sasang_rail_p13_status") == "archive_drift_ok"},
        "mainline_prune_applied": {
            "passed": prune.get("prune_ok") is True
            and (prune.get("applied") is True or prune.get("already_pruned") is True),
        },
        "mainline_zero_dummy": {"passed": mainline_dummy == 0},
        "attested_classification_gate_ok": {"passed": class_gate.get("gate_ok") is True},
        "clinical_template_gate_ok": {"passed": clinical.get("gate_ok") is True},
        "weekly_drift_alert_ok": {"passed": alert.get("alert_ok") is True},
        "tier_partition_ok": {"passed": partition.get("partition_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p14_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p14_status": "mainline_eval_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "mainline_dummy_rows": mainline_dummy,
        "mainline_rows_after_prune": prune.get("mainline_rows_after"),
        "drift_alert_level": alert.get("alert_level"),
        "reproduce": "py scripts/run_sasang_rail_p14_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p14_status": doc["sasang_rail_p14_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
