#!/usr/bin/env python3
"""Build human review queue artifact from Logos symbolic promotion gate.

This script never auto-approves promotion. It only opens/closes queue items.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_promotion_gate_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_human_review_queue_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--promotion-gate-json", default=str(DEFAULT_GATE))
    ap.add_argument("--output-json", default=str(DEFAULT_OUT))
    ap.add_argument("--owner", default="athena_human_review_pool")
    ap.add_argument("--due-hours", type=int, default=48)
    args = ap.parse_args()

    gate_path = _resolve(args.promotion_gate_json)
    out_path = _resolve(args.output_json)
    gate = _read_json(gate_path)
    if not gate:
        raise SystemExit(f"missing/invalid gate json: {gate_path}")

    decision = str(gate.get("decision") or "")
    all_pass = bool(gate.get("all_pass") is True)
    include = all_pass and decision == "GO_RESEARCH_PROMOTION_CANDIDATE"

    generated = datetime.now(timezone.utc)
    due = generated + timedelta(hours=max(1, int(args.due_hours)))

    out = {
        "schema": "logos_symbolic_human_review_queue_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "included": include,
        "trigger_decision": decision,
        "owner": args.owner,
        "due_utc": due.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "open" if include else "closed",
        "gate_ref": str(gate_path).replace("\\", "/"),
        "items": [],
        "guardrails": [
            "Queue only; no automatic human-approval execution.",
            "A-track/live auto bridge remains forbidden.",
        ],
    }
    if include:
        out["items"] = [
            {
                "id": "logos_symbolic_candidate_review",
                "title": "Review Logos symbolic promotion candidate evidence",
                "status": "open",
                "evidence": {
                    "metrics_snapshot": gate.get("metrics_snapshot"),
                    "checks": gate.get("checks"),
                    "input_refs": gate.get("input_refs"),
                    "backtest_ref": gate.get("backtest_ref"),
                },
                "checkpoints": [
                    "Confirm blind holdout sample sufficiency policy.",
                    "Confirm no label-leakage from seed generation path.",
                    "Decide approve/reject and log explicit approver identity.",
                ],
            }
        ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

