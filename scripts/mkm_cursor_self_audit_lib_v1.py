"""Suspect-first self-audit blocks for Cursor LTM continuity (Pillar A)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from mkm_ops_memory_index_lib_v1 import LANE_TOPIC_HINTS

SUSPECT_FIRST_RULES: tuple[str, ...] = (
    "Doubt chat/shallow memory before implementation or pass/fail claims",
    "Verify CONSTITUTION path + runnable script exit 0 — not NL/chat alone",
    "Look back: deep_reads <= 3; required SSOT in deep_fetch_next queue",
    "graph_axis=A_ltm here; Logos graph_slice = other (Oracle) chat",
    "End meaningful turns with session_end or checkpoint + continuity-id",
)


def lane_default_topic_query(lane: str) -> str:
    """Build a default LTM graph query from lane topic hints (no user topic required)."""
    hints = LANE_TOPIC_HINTS.get(lane, ())
    if not hints:
        return lane.strip() or "infra"
    return " ".join(str(h) for h in hints[:6])


def build_self_audit(
    *,
    lookback_performed: bool = False,
    deep_reads_count: int = 0,
    violation_flags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "suspect_first": True,
        "lookback_performed": lookback_performed,
        "implementation_claims_need_path": True,
        "deep_reads_count": deep_reads_count,
        "violation_flags": list(violation_flags or []),
        "contract_ack": "AI must doubt defaults; verify disk SSOT before claims",
        "rules": list(SUSPECT_FIRST_RULES),
    }


def build_agent_self_check(*, lane: str, continuity_id: str) -> dict[str, Any]:
    cid = continuity_id.strip() or f"pillar-a-{lane}"
    return {
        "contract": "suspect_first",
        "lane": lane,
        "continuity_id": cid,
        "rules": list(SUSPECT_FIRST_RULES),
        "session_end_command": (
            f"py scripts/run_mkm_cursor_session_end_v1.py --lane {lane} "
            f'--continuity-id {cid} --message "<one line>"'
        ),
    }
