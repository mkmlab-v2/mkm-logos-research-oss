"""Resolve RQ-019 lifecycle status from counsel + commander-close artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIGNOFF = ROOT / "docs/final/artifacts/mkm_inter_agent_legal_counsel_signoff_v1_latest.json"
CLOSE = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_commander_close_v1_latest.json"
READINESS = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_closure_readiness_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def resolve_rq019_status() -> str:
    """OPEN | READY_FOR_COMMANDER_CLOSE | CLOSED."""
    close = _load(CLOSE) or {}
    if close.get("rq_019_closed") is True:
        return "CLOSED"
    readiness = _load(READINESS) or {}
    signoff = _load(SIGNOFF) or {}
    if readiness.get("closure_allowed") or (
        signoff.get("counsel_signoff") and signoff.get("rq_019_checklist_item_7_met")
    ):
        return "READY_FOR_COMMANDER_CLOSE"
    return "OPEN"
