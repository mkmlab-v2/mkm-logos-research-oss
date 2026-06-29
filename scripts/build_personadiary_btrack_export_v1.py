#!/usr/bin/env python3
"""Build personadiary_btrack_export_v1 from personadiary_mobile_ops_v1 (PII redact · Human Gate)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

HUMAN_GATE_ACK_TEXT_KO = (
    "연구용 비식별 패키지입니다. 자동 업로드 없음. Track A·mkmlife·실매매 합선 없음."
)
BOUNDARY_ACK = (
    "research_only · manual inbox drop · no server upload · no Track A or mkmlife auto merge"
)
INBOX_REL = "reports/constitution/btrack_pilot/personadiary_export_inbox/"
PACK0_HINT = (
    "research_only · Pack0-B LoRA sandbox · prep_myeongri_deterministic_lora_golden_v1.py · no Track A merge"
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\b\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def strip_obvious_pii(text: str) -> str:
    out = EMAIL_RE.sub("[redacted-email]", text)
    return PHONE_RE.sub("[redacted-phone]", out)


def pseudonym_id(*, week_label: str, generated_at_utc: str, salt: str) -> str:
    raw = f"{week_label}|{generated_at_utc}|{salt}".encode("utf-8")
    return f"pdexp_{hashlib.sha256(raw).hexdigest()[:16]}"


def build_btrack_export(
    ops: dict[str, Any],
    *,
    pii_redact: bool = True,
    human_gate_ack: bool = True,
    ack_at_utc: str | None = None,
    salt: str = "local",
) -> dict[str, Any]:
    if ops.get("schema") != "personadiary_mobile_ops_v1":
        raise ValueError("expected personadiary_mobile_ops_v1")

    generated_at = _utc_now()
    ack_at = ack_at_utc or generated_at
    week_label = str(ops.get("week_label") or "unknown")

    fields_removed: list[str] = []
    diary_mode = "full_text"
    payload: dict[str, Any] = {
        "active_lane": ops.get("active_lane", "rest"),
        "weekly_top5": [],
        "next_one_action": {"text": "", "lane": ops.get("active_lane", "rest")},
    }

    for item in ops.get("weekly_top5") or []:
        text = str(item.get("text") or "")[:200]
        if pii_redact:
            text = strip_obvious_pii(text)
        payload["weekly_top5"].append(
            {
                "id": str(item.get("id") or "")[:32],
                "text": text,
                "status": item.get("status") if item.get("status") == "done" else "pending",
                "lane": item.get("lane") or "mind",
            }
        )

    next_one = ops.get("next_one_action") or {}
    next_text = str(next_one.get("text") or "")[:200]
    if pii_redact:
        next_text = strip_obvious_pii(next_text)
    payload["next_one_action"] = {
        "text": next_text,
        "lane": next_one.get("lane") or payload["active_lane"],
        "due_local": next_one.get("due_local"),
    }
    payload["next_one_action"] = {
        k: v for k, v in payload["next_one_action"].items() if v is not None
    }

    north = ops.get("north_star_by_lane_hypo_v1")
    if isinstance(north, dict) and north.get("hypothesis_tier") == "B":
        payload["north_star_by_lane_hypo_v1"] = north

    if pii_redact:
        fields_removed.extend(
            [
                "local_birth_profile_v1",
                "local_birth_profile_v1.nickname",
                "local_birth_profile_v1.birth_instant_utc",
            ]
        )
        diary_mode = "lane_stats_only"
        stats = {"body": 0, "mind": 0, "work": 0, "rest": 0, "total_entries": 0}
        for entry in ops.get("diary_entries_local") or []:
            lane = entry.get("lane") or "mind"
            if lane in stats:
                stats[lane] += 1
            stats["total_entries"] += 1
        payload["diary_lane_stats"] = stats
        payload["checkpoint_count"] = len(ops.get("checkpoints") or [])
    else:
        diary_mode = "text_redacted"
        redacted_entries = []
        for entry in ops.get("diary_entries_local") or []:
            body = strip_obvious_pii(str(entry.get("body") or ""))[:2000]
            redacted_entries.append(
                {
                    "date_local": str(entry.get("date_local") or "")[:10],
                    "body": body,
                    "lane": entry.get("lane") or "mind",
                }
            )
        payload["diary_entries_redacted"] = redacted_entries
        payload["checkpoint_count"] = len(ops.get("checkpoints") or [])

    if not human_gate_ack:
        raise ValueError("human_gate_ack required for btrack export")

    return {
        "schema": "personadiary_btrack_export_v1",
        "generated_at_utc": generated_at,
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_upload": False,
        "human_gate_ack": {
            "acknowledged": True,
            "ack_text_ko": HUMAN_GATE_ACK_TEXT_KO,
            "ack_at_utc": ack_at,
        },
        "redaction": {
            "pii_redact_applied": pii_redact,
            "fields_removed": fields_removed,
            "diary_mode": diary_mode,
        },
        "pseudonym_id": pseudonym_id(
            week_label=week_label, generated_at_utc=generated_at, salt=salt
        ),
        "source": {
            "mobile_ops_schema": "personadiary_mobile_ops_v1",
            "mobile_ops_version": int(ops.get("version") or 1),
            "week_label": week_label[:16],
        },
        "payload": payload,
        "inbox_pointer": {
            "manual_drop_only": True,
            "repo_relative_path": INBOX_REL,
            "pack0_b_lora_hint": PACK0_HINT,
        },
        "boundary_ack": BOUNDARY_ACK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ops-json",
        type=Path,
        default=ROOT / "docs/final/artifacts/fixtures/personadiary_mobile_ops_v1.example.json",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "docs/final/artifacts/fixtures/personadiary_btrack_export_v1.example.json",
    )
    parser.add_argument("--no-pii-redact", action="store_true")
    args = parser.parse_args()

    ops = json.loads(args.ops_json.read_text(encoding="utf-8"))
    doc = build_btrack_export(ops, pii_redact=not args.no_pii_redact, human_gate_ack=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
