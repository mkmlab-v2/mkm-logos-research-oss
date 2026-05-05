#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.4, M:0.7}
# Balance: 88
# Purpose: Apply threshold proposal to baseline thresholds artifact.
# Keywords: apply thresholds, proposal, gated apply
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply threshold proposal to thresholds artifact.")
    ap.add_argument("--proposal-json", default="docs/final/artifacts/btrack_external_baseline_threshold_tuning_proposal_latest.json")
    ap.add_argument("--thresholds-json", default="docs/final/artifacts/btrack_external_baseline_thresholds_v1.json")
    ap.add_argument("--approval-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_approval_latest.json")
    ap.add_argument("--apply-log-jsonl", default="docs/final/artifacts/external_bible_crossref_threshold_apply_log.jsonl")
    args = ap.parse_args()

    p_proposal = resolve(args.proposal_json)
    p_thresholds = resolve(args.thresholds_json)
    p_approval = resolve(args.approval_json)
    p_log = resolve(args.apply_log_jsonl)
    if not p_proposal.is_file() or not p_thresholds.is_file() or not p_approval.is_file():
        raise SystemExit("missing proposal, thresholds, or approval json")

    proposal = json.loads(p_proposal.read_text(encoding="utf-8"))
    thresholds_doc = json.loads(p_thresholds.read_text(encoding="utf-8"))
    approval_doc = json.loads(p_approval.read_text(encoding="utf-8"))
    proposed = proposal.get("proposed_thresholds", {})
    if not isinstance(proposed, dict) or not proposed:
        raise SystemExit("proposal missing proposed_thresholds")
    if not isinstance(thresholds_doc, dict):
        raise SystemExit("thresholds artifact must be json object")

    thresholds_doc["thresholds"] = proposed
    thresholds_doc["generated_at_utc"] = now_utc()
    thresholds_doc["last_applied_from_proposal_ref"] = str(p_proposal)
    thresholds_doc["last_applied_at_utc"] = now_utc()
    p_thresholds.write_text(json.dumps(thresholds_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_row = {
        "applied_at_utc": now_utc(),
        "proposal_ref": str(p_proposal),
        "thresholds_ref": str(p_thresholds),
        "approved_by": approval_doc.get("approved_by"),
        "approved_reason": approval_doc.get("approved_reason"),
        "applied_thresholds": proposed,
    }
    p_log.parent.mkdir(parents=True, exist_ok=True)
    with p_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_row, ensure_ascii=False) + "\n")

    # One-shot approval reset after successful apply.
    approval_doc["approved"] = False
    approval_doc["consumed_at_utc"] = now_utc()
    p_approval.write_text(json.dumps(approval_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(p_thresholds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
