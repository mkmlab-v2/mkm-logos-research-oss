#!/usr/bin/env python3
"""Build a simple 16-state transition report from B-track JSONL."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.myeongni.manseryeok_provenance import btrack_myeongni_16_state_stream_scope
SRC = ROOT / "data" / "myeongni" / "myeongni_16_state_experiment_v1.jsonl"
OUT = ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_16_STATE_TRANSITION_V1.json"


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            rows.append(json.loads(s))
    return rows


def main() -> int:
    rows = _rows(SRC)
    rows_sorted = sorted(rows, key=lambda r: _parse_ts(str(r.get("ts_utc", ""))))

    observed_states: list[int] = []
    for row in rows_sorted:
        state_id = row.get("state_id")
        if isinstance(state_id, int) and 1 <= state_id <= 16:
            observed_states.append(state_id)

    transitions: Counter[tuple[int, int]] = Counter()
    from_counts: Counter[int] = Counter()
    for prev, nxt in zip(observed_states, observed_states[1:]):
        transitions[(prev, nxt)] += 1
        from_counts[prev] += 1

    counts_matrix: dict[str, dict[str, int]] = defaultdict(dict)
    probs_matrix: dict[str, dict[str, float]] = defaultdict(dict)
    for (src, dst), cnt in sorted(transitions.items()):
        k1 = f"state_{src}"
        k2 = f"state_{dst}"
        counts_matrix[k1][k2] = int(cnt)
        probs_matrix[k1][k2] = cnt / from_counts[src]

    summary = {
        "schema": "myeongni_16_state_transition_report_v1",
        "manseryeok_scope": btrack_myeongni_16_state_stream_scope(),
        "source_log": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "total_rows": len(rows_sorted),
        "state_rows": len(observed_states),
        "transition_count": max(0, len(observed_states) - 1),
        "unique_states_observed": sorted(set(observed_states)),
        "counts_matrix": counts_matrix,
        "probability_matrix": probs_matrix,
        "quality": {
            "sufficient_for_signal": len(observed_states) >= 30,
            "min_rows_for_signal": 30,
            "current_stage": (
                "analysis_ready" if len(observed_states) >= 30 else "bootstrap_insufficient_rows"
            ),
        },
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
