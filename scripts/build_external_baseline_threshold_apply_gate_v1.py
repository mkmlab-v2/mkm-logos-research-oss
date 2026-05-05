#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.4, M:0.7}
# Balance: 88
# Purpose: Decide whether threshold proposal is allowed to apply.
# Keywords: threshold, apply gate, approval, human review
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build apply gate decision for threshold proposal.")
    ap.add_argument("--hint-json", default="docs/final/artifacts/external_bible_crossref_threshold_recalibration_hint_latest.json")
    ap.add_argument("--resolution-json", default="docs/final/artifacts/external_bible_crossref_human_review_resolution_latest.json")
    ap.add_argument("--approval-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_approval_latest.json")
    ap.add_argument("--proposal-json", default="docs/final/artifacts/btrack_external_baseline_threshold_tuning_proposal_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_gate_latest.json")
    args = ap.parse_args()

    p_hint = resolve(args.hint_json)
    p_resolution = resolve(args.resolution_json)
    p_approval = resolve(args.approval_json)
    p_proposal = resolve(args.proposal_json)
    p_out = resolve(args.output_json)

    hint = load_json(p_hint)
    resolution = load_json(p_resolution)
    approval = load_json(p_approval)

    now = datetime.now(timezone.utc)
    hint_active = bool(hint.get("hint_active", False))
    resolution_completed = str(resolution.get("resolution_state", "")) == "completed"
    approval_granted_raw = bool(approval.get("approved", False))
    approved_by = str(approval.get("approved_by", "")).strip()
    approved_reason = str(approval.get("approved_reason", "")).strip()
    expires_at_utc = str(approval.get("expires_at_utc", "")).strip()
    expires_dt = parse_utc(expires_at_utc) if expires_at_utc else None
    approval_not_expired = bool(expires_dt and expires_dt > now)
    approval_schema_valid = bool(approved_by and approved_reason and expires_at_utc and expires_dt is not None)
    approval_granted = approval_granted_raw and approval_schema_valid and approval_not_expired
    proposal_exists = p_proposal.is_file()
    can_apply = hint_active and resolution_completed and approval_granted and proposal_exists

    out = {
        "schema": "external_bible_crossref_threshold_apply_gate_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "checks": {
            "hint_active": hint_active,
            "resolution_completed": resolution_completed,
            "approval_granted": approval_granted,
            "approval_schema_valid": approval_schema_valid,
            "approval_not_expired": approval_not_expired,
            "proposal_exists": proposal_exists,
        },
        "can_apply_thresholds": can_apply,
        "refs": {
            "hint": str(p_hint) if p_hint.is_file() else None,
            "resolution": str(p_resolution) if p_resolution.is_file() else None,
            "approval": str(p_approval) if p_approval.is_file() else None,
            "proposal": str(p_proposal) if p_proposal.is_file() else None,
        },
    }
    p_out.parent.mkdir(parents=True, exist_ok=True)
    p_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(p_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
