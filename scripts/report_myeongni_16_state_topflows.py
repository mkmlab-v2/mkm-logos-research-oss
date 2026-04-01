#!/usr/bin/env python3
"""Summarize top inbound/outbound flows from 16-state transition report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.myeongni.manseryeok_provenance import btrack_myeongni_16_state_stream_scope
SRC = ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_16_STATE_TRANSITION_V1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_16_STATE_TOPFLOWS_V1.json"


def _sid(label: str) -> int:
    return int(str(label).replace("state_", ""))


def main() -> int:
    report = json.loads(SRC.read_text(encoding="utf-8"))
    counts = report.get("counts_matrix", {})
    probs = report.get("probability_matrix", {})

    inbound: dict[int, list[dict]] = {i: [] for i in range(1, 17)}
    outbound: dict[int, list[dict]] = {i: [] for i in range(1, 17)}

    for src_label, dst_map in counts.items():
        src = _sid(src_label)
        for dst_label, cnt in dst_map.items():
            dst = _sid(dst_label)
            prob = float(probs.get(src_label, {}).get(dst_label, 0.0))
            flow = {"from_state": src, "to_state": dst, "count": int(cnt), "probability": prob}
            outbound[src].append(flow)
            inbound[dst].append(flow)

    state_rows: list[dict] = []
    for state_id in range(1, 17):
        out_sorted = sorted(
            outbound[state_id],
            key=lambda x: (x["count"], x["probability"], -x["to_state"]),
            reverse=True,
        )[:3]
        in_sorted = sorted(
            inbound[state_id],
            key=lambda x: (x["count"], x["probability"], -x["from_state"]),
            reverse=True,
        )[:3]
        state_rows.append(
            {
                "state_id": state_id,
                "outbound_top3": out_sorted,
                "inbound_top3": in_sorted,
                "outbound_total_count": int(sum(x["count"] for x in outbound[state_id])),
                "inbound_total_count": int(sum(x["count"] for x in inbound[state_id])),
            }
        )

    all_flows: list[dict] = []
    for row in state_rows:
        all_flows.extend(row["outbound_top3"])
    dedup = {(f["from_state"], f["to_state"]): f for f in all_flows}.values()
    global_top5 = sorted(
        dedup, key=lambda x: (x["count"], x["probability"], -x["to_state"]), reverse=True
    )[:5]

    out_doc = {
        "schema": "myeongni_16_state_topflows_v1",
        "manseryeok_scope": btrack_myeongni_16_state_stream_scope(),
        "source_transition_report": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "state_flow_summary": state_rows,
        "global_top5_flows": global_top5,
        "quality": report.get("quality", {}),
    }
    OUT.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
