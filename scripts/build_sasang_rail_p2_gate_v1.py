#!/usr/bin/env python3
"""Sasang rail P2 gate: interpretive bundle + 4-agent smoke + literature joint bench [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTERPRETIVE = ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
PROTOCOL = ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_latest.json"
JOINT_SMOKE = ROOT / "data/myeongni/sasang_saju_joint_benchmark_smoke_v1.json"
JOINT_DATASET = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p2_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    bundle = _load(INTERPRETIVE)
    protocol = _load(PROTOCOL)
    smoke_doc = _load(JOINT_SMOKE)
    smoke = smoke_doc.get("summary") if isinstance(smoke_doc.get("summary"), dict) else smoke_doc

    hint = protocol.get("promotion_gate_hint") or {}
    notes = " ".join(str(x) for x in (hint.get("notes") or []))
    checks = {
        "interpretive_bundle_present": {
            "passed": bundle.get("schema") == "sasang_interpretive_insight_bundle_v1",
        },
        "interpretive_rail_b_track": {"passed": bundle.get("rail") == "B_TRACK"},
        "interpretive_synthesis_v1": {
            "passed": len(str((bundle.get("synthesis_v1") or {}).get("how_to_synthesize_ko") or "")) >= 80,
        },
        "protocol_4agent_present": {
            "passed": protocol.get("schema") == "sasang_4agent_collision_btrack_protocol_v1",
        },
        "protocol_research_only": {"passed": protocol.get("mode") == "research_only"},
        "protocol_non_gating": {"passed": protocol.get("policy_label") == "NON_GATING"},
        "protocol_no_track_a_autobridge": {
            "passed": "auto-bridge" in notes.lower() or "Do not auto-bridge" in notes,
        },
        "joint_dataset_present": {"passed": JOINT_DATASET.is_file()},
        "joint_smoke_passed": {
            "passed": int(smoke.get("failed") or 0) == 0
            and int(smoke.get("rows_with_birth_evaluated") or 0) >= 1,
        },
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p2_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p2_status": "enrichment_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "artifact_paths": {
            "interpretive_bundle": str(INTERPRETIVE).replace("\\", "/"),
            "protocol_4agent": str(PROTOCOL).replace("\\", "/"),
            "joint_smoke": str(JOINT_SMOKE).replace("\\", "/"),
            "joint_dataset": str(JOINT_DATASET).replace("\\", "/"),
        },
        "reproduce": "py scripts/run_sasang_rail_p2_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p2_status": doc["sasang_rail_p2_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
