#!/usr/bin/env python3
"""Apply explicit human approval to Logos symbolic promotion gate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--approver", required=True)
    ap.add_argument(
        "--note",
        default="Human approved Logos symbolic promotion candidate after B-track gate review.",
    )
    ap.add_argument("--gate-json", type=Path, default=None)
    ap.add_argument("--approval-json", type=Path, default=None)
    ap.add_argument("--approval-md", type=Path, default=None)
    ap.add_argument("--candidate-json", type=Path, default=None)
    ap.add_argument("--candidate-md", type=Path, default=None)
    ap.add_argument(
        "--allow-reapprove",
        action="store_true",
        help="Allow overwriting existing human approval artifacts.",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"
    gate_path = args.gate_json if args.gate_json is not None else (art / "logos_symbolic_event_promotion_gate_latest.json")
    approval_json_path = args.approval_json if args.approval_json is not None else (art / "logos_symbolic_event_human_approval_latest.json")
    approval_md_path = args.approval_md if args.approval_md is not None else (art / "logos_symbolic_event_human_approval_latest.md")
    candidate_json_path = args.candidate_json if args.candidate_json is not None else (art / "logos_symbolic_event_track_a_candidate_latest.json")
    candidate_md_path = args.candidate_md if args.candidate_md is not None else (art / "logos_symbolic_event_track_a_candidate_latest.md")

    gate = _safe_json(gate_path)
    if not gate:
        raise SystemExit(f"missing gate artifact: {gate_path}")

    decision = str(gate.get("decision") or "")
    if decision == "GO_RESEARCH_PROMOTION_CANDIDATE_WITH_HUMAN_APPROVAL":
        if not args.allow_reapprove:
            raise SystemExit("human approval already applied; use --allow-reapprove to overwrite")
        decision = "GO_RESEARCH_PROMOTION_CANDIDATE"
    if decision != "GO_RESEARCH_PROMOTION_CANDIDATE":
        raise SystemExit(
            f"gate decision '{gate.get('decision')}' is not eligible for human-approval promotion"
        )

    ts = _now_utc()
    approval = {
        "schema": "logos_symbolic_event_human_approval_v1",
        "approved_at_utc": ts,
        "approver": args.approver,
        "approval_note": args.note,
        "input_gate_decision": gate.get("decision"),
        "approved": True,
    }
    approval_json_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    approval_md_path.write_text(
        "\n".join(
            [
                "# Logos Symbolic Human Approval",
                "",
                f"- approved_at_utc: `{ts}`",
                f"- approver: `{args.approver}`",
                f"- approved: `True`",
                f"- input_gate_decision: `{gate.get('decision')}`",
                "",
                "## Note",
                args.note,
                "",
            ]
        ),
        encoding="utf-8",
    )

    gate["decision"] = "GO_RESEARCH_PROMOTION_CANDIDATE_WITH_HUMAN_APPROVAL"
    gate["human_review_gate_required"] = False
    gate["auto_bridge_allowed"] = False
    gate["approved_at_utc"] = ts
    gate["approved_by"] = args.approver
    gate["human_approval_ref"] = str(approval_json_path).replace("\\", "/")
    gate["promotion_scope"] = "btrack_candidate_only"
    gate["track_wall"] = {
        "promotion_to_a_track_allowed": False,
        "live_trigger_auto_enabled": False,
        "human_review_gate_required": False,
        "note": "Human-approved B-track candidate; A-track/live auto bridge remains forbidden.",
    }
    gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    candidate = {
        "schema": "logos_symbolic_event_track_a_candidate_v1",
        "generated_at_utc": ts,
        "status": "APPROVED_CANDIDATE",
        "source_track": "B",
        "promotion_mode": "human_approved_candidate_only",
        "candidate_gate": {
            "all_pass": gate.get("all_pass"),
            "decision": gate.get("decision"),
        },
        "candidate_metrics": gate.get("metrics_snapshot"),
        "runtime_constraints": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "requires_human_review_each_release": True,
        },
        "evidence": {
            "gate_json": str(gate_path.resolve()),
            "human_approval_json": str(approval_json_path.resolve()),
            "backtest_ref": gate.get("backtest_ref"),
            "input_refs": gate.get("input_refs"),
        },
    }
    candidate_json_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    candidate_md_path.write_text(
        "\n".join(
            [
                "# Logos Symbolic Track A Candidate",
                "",
                f"- generated_at_utc: `{candidate['generated_at_utc']}`",
                f"- status: `{candidate['status']}`",
                f"- promotion_mode: `{candidate['promotion_mode']}`",
                f"- decision: `{candidate['candidate_gate']['decision']}`",
                f"- all_pass: `{candidate['candidate_gate']['all_pass']}`",
                "",
                "## Runtime Constraints",
                "- track_b_to_a_auto_bridge: `False`",
                "- live_trigger_auto_enabled: `False`",
                "- requires_human_review_each_release: `True`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(str(approval_json_path))
    print(str(candidate_json_path))
    print(str(gate_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

