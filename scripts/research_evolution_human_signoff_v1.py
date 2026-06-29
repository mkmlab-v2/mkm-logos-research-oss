#!/usr/bin/env python3
"""Validate and record human sign-off for R-IBL briefing evolution apply [HYPO]."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    ROOT / "docs" / "final" / "artifacts" / "schemas" / "research_evolution_human_signoff_v1.schema.json"
)
DEFAULT_SIGNOFF_LATEST = ROOT / "reports" / "research_evolution_human_signoff_latest.json"
REQUIRED_SCOPE = "ribl_briefing_evolution_rules_only"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def proposal_id(proposal: Dict[str, Any]) -> str:
    if proposal.get("branch_id"):
        return f"branch:{proposal['branch_id']}:{proposal.get('action')}"
    lens = proposal.get("lens") or "unknown"
    kind = proposal.get("kind") or "unknown"
    return f"lens:{lens}:{kind}:{proposal.get('action')}"


def validate_signoff(path: Path, *, schema_path: Path | None = None) -> List[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover
        return [f"jsonschema_missing:{exc}"]

    if not path.is_file():
        return [f"missing_signoff:{path}"]

    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    schema = json.loads((schema_path or DEFAULT_SCHEMA).read_text(encoding="utf-8"))
    try:
        Draft202012Validator(schema).validate(doc)
    except Exception as exc:
        return [f"signoff_schema:{exc}"]

    errs: List[str] = []
    if doc.get("scope") != REQUIRED_SCOPE:
        errs.append(f"bad_scope:{doc.get('scope')}")
    if doc.get("decision") != "APPROVED":
        errs.append(f"decision_not_approved:{doc.get('decision')}")
    if doc.get("track_a_auto_merge_forbidden") is not True:
        errs.append("track_a_auto_merge_forbidden")
    if doc.get("live_trading_trigger_forbidden") is not True:
        errs.append("live_trading_trigger_forbidden")
    return errs


def build_signoff_record(
    *,
    decision: str,
    actor: str,
    approved_proposal_ids: Optional[List[str]] = None,
    evolution_source_path: str = "",
    note_ko: str = "",
) -> Dict[str, Any]:
    return {
        "schema": "research_evolution_human_signoff_v1",
        "decision": decision,
        "actor": actor,
        "ack_at_utc": _utc_now(),
        "scope": REQUIRED_SCOPE,
        "approved_proposal_ids": approved_proposal_ids or [],
        "evolution_source_path": evolution_source_path,
        "note_ko": note_ko,
        "track_a_auto_merge_forbidden": True,
        "live_trading_trigger_forbidden": True,
    }


def write_signoff(doc: Dict[str, Any], out_path: Path = DEFAULT_SIGNOFF_LATEST) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path
