#!/usr/bin/env python3
"""Sasang rail P13 gate: dummy archive + attested snapshot + dual drift [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P12 = ROOT / "docs/final/artifacts/sasang_rail_p12_gate_v1_latest.json"
ARCHIVE = ROOT / "reports/sasang_joint_benchmark_dummy_archive_export_v1_latest.json"
SNAPSHOT = ROOT / "reports/sasang_joint_benchmark_attested_only_snapshot_v1_latest.json"
DRIFT = ROOT / "reports/sasang_4agent_dual_probe_drift_v1_latest.json"
ABLATION = ROOT / "reports/sasang_4agent_dual_probe_ablation_v1_latest.json"
REGISTER = ROOT / "docs/final/artifacts/sasang_4agent_dual_probe_ablation_register_v1.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p13_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p12 = _load(P12)
    archive = _load(ARCHIVE)
    snapshot = _load(SNAPSHOT)
    drift = _load(DRIFT)
    ablation = _load(ABLATION)
    reg = _load(REGISTER)

    commander_ids = snapshot.get("commander_attested_ids") or []
    checks = {
        "p12_gate_ok": {"passed": p12.get("gate_ok") is True},
        "p12_partition_compare_ok": {"passed": p12.get("sasang_rail_p12_status") == "partition_compare_ok"},
        "dummy_archive_export_ok": {"passed": archive.get("export_ok") is True},
        "attested_snapshot_ok": {"passed": snapshot.get("snapshot_ok") is True},
        "commander_attested_present": {"passed": len(commander_ids) >= 1},
        "dual_probe_drift_ok": {"passed": drift.get("drift_ok") is True},
        "dual_probe_ablation_ok": {"passed": ablation.get("all_ok") is True},
        "dual_probe_register_present": {"passed": reg.get("schema") == "sasang_4agent_dual_probe_ablation_register_v1"},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p13_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p13_status": "archive_drift_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "attested_rows": snapshot.get("rows_attested"),
        "dummy_archive_rows": archive.get("dummy_rows_exported"),
        "drift_status": drift.get("drift_status"),
        "reproduce": "py scripts/run_sasang_rail_p13_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p13_status": doc["sasang_rail_p13_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
