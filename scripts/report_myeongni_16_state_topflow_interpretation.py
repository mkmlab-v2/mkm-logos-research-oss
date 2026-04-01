#!/usr/bin/env python3
"""Generate concise interpretation from topflow summary (B-track only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.myeongni.manseryeok_provenance import btrack_myeongni_16_state_stream_scope
SRC = ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_16_STATE_TOPFLOWS_V1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_16_STATE_TOPFLOW_INTERPRETATION_V1.json"


def main() -> int:
    topflows = json.loads(SRC.read_text(encoding="utf-8"))
    quality = topflows.get("quality", {})
    global_flows = topflows.get("global_top5_flows", [])

    if global_flows:
        top = global_flows[0]
        one_liner = (
            f"current dominant transition is state {top['from_state']} -> {top['to_state']} "
            f"(count={top['count']}, p={float(top['probability']):.3f}); "
            "B-track interpretation only."
        )
    else:
        one_liner = "no observed transition yet; keep collecting B-track state rows."

    report = {
        "schema": "myeongni_16_state_topflow_interpretation_v1",
        "manseryeok_scope": btrack_myeongni_16_state_stream_scope(),
        "source_topflows_report": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "one_line_interpretation": one_liner,
        "global_top5_flows": global_flows,
        "quality_gate": {
            "sufficient_for_signal": bool(quality.get("sufficient_for_signal", False)),
            "current_stage": str(quality.get("current_stage", "unknown")),
            "min_rows_for_signal": int(quality.get("min_rows_for_signal", 30)),
        },
        "boundary_note": (
            "B-track only. Do not auto-merge into A-track trading triggers or risk caps."
        ),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
