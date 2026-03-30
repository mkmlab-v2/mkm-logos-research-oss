#!/usr/bin/env python3
"""Generate first integrated topflow interpretation snapshot (B-track)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOPFLOW = ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_16_STATE_TOPFLOW_INTERPRETATION_V1.json"
ENTRY16_GATE = ROOT / "docs" / "final" / "artifacts" / "entry16_promotion_gate.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_TOPFLOW_INTEGRATED_REPORT_V1.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    top = json.loads(TOPFLOW.read_text(encoding="utf-8"))
    gate = json.loads(ENTRY16_GATE.read_text(encoding="utf-8"))

    stage = str(top.get("quality_gate", {}).get("current_stage", "unknown"))
    dominant = top.get("global_top5_flows", [])
    has_dominant = bool(dominant)

    report = {
        "schema": "myeongni_topflow_integrated_report_v1",
        "generated_at_utc": _now_iso(),
        "sources": {
            "topflow_interpretation": str(TOPFLOW.relative_to(ROOT)).replace("\\", "/"),
            "entry16_gate": str(ENTRY16_GATE.relative_to(ROOT)).replace("\\", "/"),
        },
        "core_readout": {
            "one_line": top.get("one_line_interpretation", ""),
            "dominant_flow": dominant[0] if has_dominant else None,
            "quality_stage": stage,
            "entry16_gate_decision": gate.get("decision"),
        },
        "operational_call": (
            "analysis_read_only_continue"
            if stage == "bootstrap_insufficient_rows"
            else "analysis_ready_expand"
        ),
        "guardrails": [
            "B-track only",
            "no auto-merge into A-track trading triggers",
            "ENTRY_16 direct witness remains unresolved unless explicitly updated",
        ],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
