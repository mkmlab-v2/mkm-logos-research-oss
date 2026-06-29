#!/usr/bin/env python3
"""Record commander RQ-031 scope ack (second human gate · operator-assist lane only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "reports/a_code_promotion_rq_readiness_v1_latest.json"
DEFAULT_LOCAL = ROOT / "data/personalization/commander_a_code_promotion_rq_ack_v1.local.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/a_code_promotion_rq_commander_ack_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_ack_doc(*, ack_reference: str, note: str = "") -> dict[str, Any]:
    readiness = _load(READINESS)
    if not readiness.get("summary", {}).get("discussion_ready"):
        raise ValueError("discussion_ready is false; run promotion rq readiness bundle first")

    ref = ack_reference.strip()
    if not ref:
        raise ValueError("ack_reference required")

    now = _utc()
    local_doc = {
        "schema": "commander_a_code_promotion_rq_ack_v1",
        "version": "1.0.0",
        "updated_at_utc": now,
        "rq_id": "RQ-031",
        "parent_rq": ["RQ-028", "RQ-029"],
        "hypothesis_tier": "B",
        "research_only": True,
        "acknowledged": True,
        "ack_by": "commander",
        "ack_utc": now,
        "ack_reference": ref,
        "scope_confirmed": {
            "operator_assist_trackc_only": True,
            "no_track_a_live_ms_merge": True,
            "separate_pr_for_constitution": True,
        },
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_auto_trigger": False,
            "note_ko": "RQ-031 operator-assist lane only",
        },
        "note_ko": note.strip() or "commander scope ack for RQ-031 promotion discussion",
    }

    artifact = {
        "schema": "a_code_promotion_rq_commander_ack_v1",
        "generated_at_utc": now,
        "classification": "INTERNAL_ONLY",
        "rq_id": "RQ-031",
        "rq_031_scope_acknowledged": True,
        "hypothesis_tier": "B",
        "research_only": True,
        "ack_reference": ref,
        "ack_by": "commander",
        "ack_utc": now,
        "promotion_target_lane": readiness.get("promotion_target_lane"),
        "explicit_not_promoted": readiness.get("explicit_not_promoted") or [],
        "evidence_pointers": {
            "promotion_rq_readiness": _rel(READINESS),
            "promotion_rq_draft": _rel(
                ROOT / "experiments/a_code_12ai_v2/specs/a_code_promotion_rq_draft_v1.json"
            ),
            "checklist_readiness": _rel(
                ROOT / "reports/a_code_promotion_checklist_readiness_v1_latest.json"
            ),
        },
        "boundary_ack": (
            "RQ-031 ack = operator-assist·Track C observation lane scope only. "
            "No Track A·live·MS auto promotion."
        ),
    }
    return {"local": local_doc, "artifact": artifact}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ack-reference",
        default="COMMANDER-RQ031-SCOPE-ACK-2026-06-05",
        help="human gate reference id",
    )
    parser.add_argument("--note", default="")
    parser.add_argument("--local-out", type=Path, default=DEFAULT_LOCAL)
    parser.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--skip-local", action="store_true")
    args = parser.parse_args()

    docs = build_ack_doc(ack_reference=args.ack_reference, note=args.note)
    if not args.skip_local:
        args.local_out.parent.mkdir(parents=True, exist_ok=True)
        args.local_out.write_text(
            json.dumps(docs["local"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    args.artifact_out.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_out.write_text(
        json.dumps(docs["artifact"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "local": _rel(args.local_out) if not args.skip_local else None,
                "artifact": _rel(args.artifact_out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
