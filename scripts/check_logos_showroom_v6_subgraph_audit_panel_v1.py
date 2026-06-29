#!/usr/bin/env python3
"""Phase 3 gate: subgraph replay + showroom v6 wire/subgraph audit panel ([HYPO], NON_GATING)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MVP = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
DEFAULT_PANEL = ROOT / "reports/logos_showroom_v6_subgraph_audit_panel_v1_latest.json"
DEFAULT_REPLAY = ROOT / "reports/subgraph_router_replay_summary_latest.json"
DEFAULT_WIRE = MVP / "showroom_logos_graph_wire_rag_poc_v1.json"
DEFAULT_V6 = MVP / "public_showroom_logos_oracle_v6.html"
DEFAULT_GRAPH = MVP / "showroom_meaning_topology_graph_slice_v1.json"
DEFAULT_PRESETS = MVP / "showroom_meaning_topology_qa_presets_v1.json"
DEFAULT_SUBGRAPH_SLICE = MVP / "showroom_logos_subgraph_audit_slice_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_showroom_v6_subgraph_audit_panel_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def check(
    *,
    panel_path: Path,
    replay_path: Path,
    wire_path: Path,
    v6_html_path: Path,
    graph_path: Path,
    presets_path: Path,
    subgraph_slice_path: Path,
    min_replay_pass: int,
) -> dict[str, Any]:
    panel = json.loads(panel_path.read_text(encoding="utf-8-sig")) if panel_path.is_file() else {}
    replay = json.loads(replay_path.read_text(encoding="utf-8-sig")) if replay_path.is_file() else {}
    wire = json.loads(wire_path.read_text(encoding="utf-8-sig")) if wire_path.is_file() else {}

    gate_failures: list[str] = []
    if panel.get("schema") != "logos_showroom_v6_subgraph_audit_panel_v1":
        gate_failures.append("audit_panel schema missing")
    if replay.get("pass") is not True:
        gate_failures.append("subgraph_replay_summary pass=false")
    pass_count = int(replay.get("pass_count") or 0)
    if pass_count < min_replay_pass:
        gate_failures.append(f"replay pass_count {pass_count} < min {min_replay_pass}")
    if not wire_path.is_file():
        gate_failures.append("missing showroom wire poc json")
    elif not isinstance((wire.get("wire") or {}).get("honest_metrics"), dict):
        gate_failures.append("wire poc missing honest_metrics")
    for label, path in [
        ("v6_html", v6_html_path),
        ("graph_slice", graph_path),
        ("qa_presets", presets_path),
    ]:
        if not path.is_file():
            gate_failures.append(f"missing {label}: {path.name}")
    audit = panel.get("wire_audit_panel") if isinstance(panel.get("wire_audit_panel"), dict) else {}
    if not audit.get("wire_audit_ui_present"):
        gate_failures.append("v6 html missing wire-audit UI hook")
    if not subgraph_slice_path.is_file():
        gate_failures.append("missing showroom subgraph audit slice json")
    elif not audit.get("subgraph_audit_ui_present"):
        gate_failures.append("v6 html missing subgraph-audit UI hook")
    if panel.get("non_gating") is not True:
        gate_failures.append("panel non_gating not true")

    return {
        "schema": "logos_showroom_v6_subgraph_audit_panel_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "send_gate": "HOLD",
        "subgraph_replay_pass_count": pass_count,
        "subgraph_replay_query_count": replay.get("query_count"),
        "wire_payload_savings_ratio": audit.get("payload_savings_ratio"),
        "gate_pass": len(gate_failures) == 0,
        "gate_failures": gate_failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-json", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--replay-json", type=Path, default=DEFAULT_REPLAY)
    ap.add_argument("--wire-json", type=Path, default=DEFAULT_WIRE)
    ap.add_argument("--v6-html", type=Path, default=DEFAULT_V6)
    ap.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--subgraph-slice-json", type=Path, default=DEFAULT_SUBGRAPH_SLICE)
    ap.add_argument("--min-replay-pass", type=int, default=12)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = check(
        panel_path=args.panel_json,
        replay_path=args.replay_json,
        wire_path=args.wire_json,
        v6_html_path=args.v6_html,
        graph_path=args.graph_json,
        presets_path=args.presets_json,
        subgraph_slice_path=args.subgraph_slice_json,
        min_replay_pass=args.min_replay_pass,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_pass"], "out": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
