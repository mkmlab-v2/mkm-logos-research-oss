#!/usr/bin/env python3
"""Pilot-tier commercial gate for Logos Graph Studio (Track C · B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_graph_studio_pilot_commercial_gate_v1_latest.json"

COMMERCIAL_READINESS = ROOT / "reports/logos_observatory_commercial_readiness_v1_latest.json"
L4L5 = ROOT / "docs/final/artifacts/logos_track_l_l4_l5_readiness_v1_latest.json"
JOINT = ROOT / "reports/logos_graphrag_ollama_joint_eval_v1_latest.json"
SUBGRAPH_GOLD = ROOT / "reports/logos_subgraph_gold_eval_v1_latest.json"
MEETING_READINESS = ROOT / "reports/logos_graph_studio_b2b_meeting_pack_readiness_v1_latest.json"
PILOT_APPROVAL = ROOT / "docs/final/artifacts/logos_graph_studio_commander_pilot_approval_v1_latest.json"
LEMMA_MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"
MIN_PILOT_LEMMA_EDGES = 500


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def check() -> dict[str, Any]:
    failures: list[str] = []
    checks: dict[str, Any] = {}

    cr = _read(COMMERCIAL_READINESS)
    checks["commercial_stack_ok"] = cr.get("commercial_stack_ok")
    if not cr.get("commercial_stack_ok"):
        failures.append("commercial_stack_ok false")

    l4l5 = _read(L4L5)
    checks["l4_l5_ok"] = l4l5.get("l4_l5_ok")
    if not l4l5.get("l4_l5_ok"):
        failures.append("l4_l5_ok false")

    lemma = _read(LEMMA_MANIFEST)
    jsonl_path = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
    edge_count_manifest = int(lemma.get("edge_count") or 0)
    edge_count_jsonl = 0
    if jsonl_path.is_file():
        edge_count_jsonl = sum(1 for line in jsonl_path.open(encoding="utf-8") if line.strip())
    edge_count = max(edge_count_manifest, edge_count_jsonl)
    checks["lemma_edge_count"] = edge_count
    checks["lemma_edge_count_jsonl"] = edge_count_jsonl
    checks["lemma_pilot_min"] = edge_count >= MIN_PILOT_LEMMA_EDGES
    if edge_count < MIN_PILOT_LEMMA_EDGES:
        failures.append(f"lemma edges {edge_count} < {MIN_PILOT_LEMMA_EDGES}")

    joint = _read(JOINT)
    checks["joint_ok"] = joint.get("joint_ok")
    checks["joint_pilot_min_lemma_lines"] = 500
    if not joint.get("joint_ok"):
        failures.append("joint_ok false (pilot tier)")

    sg = _read(SUBGRAPH_GOLD)
    sg_summary = sg.get("summary") if isinstance(sg.get("summary"), dict) else {}
    sg_pass = sg_summary.get("gold_required_all_pass")
    checks["subgraph_gold_all_pass"] = sg_pass
    if sg_pass is not True:
        failures.append("subgraph gold_required_all_pass false")

    mr = _read(MEETING_READINESS)
    b2b_ok = mr.get("ready_for_internal_b2b_meeting") is True or mr.get("ok") is True
    checks["b2b_meeting_pack_ok"] = b2b_ok
    if not b2b_ok:
        failures.append("b2b meeting pack readiness false")

    approval = _read(PILOT_APPROVAL)
    checks["commander_pilot_approval"] = approval.get("commander_signoff") is True
    if not approval.get("commander_signoff"):
        failures.append("commander pilot approval missing")

    # IP gate subprocess
    ip_proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_mkm_marketing_ip_governance_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    checks["marketing_ip_gate_exit0"] = ip_proc.returncode == 0
    if ip_proc.returncode != 0:
        failures.append("marketing IP governance gate failed")

    ok = len(failures) == 0
    return {
        "schema": "logos_graph_studio_pilot_commercial_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "pilot_tier": True,
        "pilot_commercial_ready": ok,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "ready_for_external_send_note": (
            "Pilot stack ready for internal B2B file럿 only; counsel sign-off + billing required for SEND."
        ),
        "track_wall": {
            "a_track_auto_promote": False,
            "live_trading_trigger": False,
            "logos_non_gating": True,
        },
        "ok": ok,
        "gate_failures": failures,
        "checks": checks,
        "reproducible_command": "py scripts/check_logos_graph_studio_pilot_commercial_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = check()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "pilot_commercial_ready": doc["pilot_commercial_ready"], "out": str(args.output)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
