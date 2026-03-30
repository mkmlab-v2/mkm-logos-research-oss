#!/usr/bin/env python3
"""Evaluate ENTRY_16 promotion gate from source-hunt summary."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "final" / "artifacts" / "entry16_source_hunt_summary.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "entry16_promotion_gate.json"


def main() -> int:
    summary = json.loads(SRC.read_text(encoding="utf-8"))
    has_direct_witness = bool(summary.get("has_direct_witness"))
    witness_counts = summary.get("witness_counts", {})
    yes_count = int(witness_counts.get("yes", 0))
    proxy_count = int(summary.get("proxy_anchor_candidate_count", 0))

    if has_direct_witness and yes_count > 0:
        decision = "promote_candidate"
        status = "candidate_ready_for_manual_review"
        rationale = "direct witness exists in source-hunt summary"
    elif proxy_count > 0:
        decision = "promote_proxy_candidate_manual"
        status = "proxy_candidate_ready_for_manual_review"
        rationale = "direct witness absent; thematic proxy anchor candidate exists for manual policy review"
    else:
        decision = "keep_locked"
        status = "missing_anchor_until_source_update"
        rationale = "no direct witness anchor for Ezra 2:54 yet"

    report = {
        "schema": "entry16_promotion_gate_v1",
        "source_summary": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "decision": decision,
        "status": status,
        "has_direct_witness": has_direct_witness,
        "witness_yes_count": yes_count,
        "proxy_anchor_candidate_count": proxy_count,
        "required_evidence": [
            "djd_or_equivalent_primary_source",
            "fragment_col_line_anchor_for_ezra_2_54",
            "citation_reproducibility_notes",
        ],
        "rationale": rationale,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
