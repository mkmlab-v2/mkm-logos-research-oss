"""Shared case loading for sandbox compression benches (B-track)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HEAVY_LANES = frozenset(
    {"stack_trace", "code_context", "agent_rules_excerpt", "long_multifile"}
)
SHORT_LANES = frozenset({"single_token_probe", "user_query_short"})


def load_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get("raw_text") is not None:
            rows.append(row)
    return rows


def filter_cases(
    cases: list[dict[str, Any]],
    *,
    lanes: set[str] | frozenset[str] | None = None,
    exclude_lanes: set[str] | frozenset[str] | None = None,
    max_cases: int = 0,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in cases:
        lane = str(row.get("lane") or "")
        if lanes and lane not in lanes:
            continue
        if exclude_lanes and lane in exclude_lanes:
            continue
        out.append(row)
        if max_cases and len(out) >= max_cases:
            break
    return out
