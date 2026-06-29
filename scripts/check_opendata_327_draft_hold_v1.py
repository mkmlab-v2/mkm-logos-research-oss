#!/usr/bin/env python3
"""OpenData 327 draft HOLD gate (local, deterministic, no network)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "tests/fixtures/opendata_327_policy_slot_hold_v1.json"
DEFAULT_OUT = ROOT / "reports/opendata_327_draft_hold_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("input must be a JSON object")
    return raw


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def evaluate(doc: dict[str, Any], source_path: Path) -> dict[str, Any]:
    slots = doc.get("slots")
    if not isinstance(slots, list):
        raise ValueError("input must contain 'slots' array")

    violations: list[dict[str, Any]] = []
    checked_slots = 0
    for idx, slot in enumerate(slots, start=1):
        if not isinstance(slot, dict):
            violations.append(
                {
                    "slot_index": idx,
                    "slot_id": f"slot_{idx}",
                    "reason": "slot_not_object",
                    "detail": "slot item must be object",
                }
            )
            continue

        checked_slots += 1
        slot_id = str(slot.get("slot_id") or f"slot_{idx}")
        evidence = slot.get("evidence_chunk_ids")
        required_fields = slot.get("required_fields")
        text = slot.get("text")

        if not isinstance(evidence, list) or len(evidence) == 0:
            violations.append(
                {
                    "slot_index": idx,
                    "slot_id": slot_id,
                    "reason": "missing_evidence_chunk_ids",
                    "detail": "evidence_chunk_ids must be non-empty list",
                }
            )

        if _is_blank(text):
            violations.append(
                {
                    "slot_index": idx,
                    "slot_id": slot_id,
                    "reason": "blank_text",
                    "detail": "draft text is empty",
                }
            )

        if not isinstance(required_fields, dict):
            violations.append(
                {
                    "slot_index": idx,
                    "slot_id": slot_id,
                    "reason": "required_fields_not_object",
                    "detail": "required_fields must be object",
                }
            )
        else:
            for key, value in required_fields.items():
                if _is_blank(value):
                    violations.append(
                        {
                            "slot_index": idx,
                            "slot_id": slot_id,
                            "reason": "required_field_blank",
                            "field": key,
                            "detail": f"required_fields.{key} is blank",
                        }
                    )

    hold = len(violations) > 0
    return {
        "schema": "opendata_327_draft_hold_v1",
        "generated_at_utc": _utc_now(),
        "source": str(source_path),
        "checked_slots": checked_slots,
        "violations": violations,
        "send_gate": "HOLD",
        "ready_for_human_review": not hold,
        "decision": "HOLD" if hold else "REVIEW_READY",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _read_json(args.input_json)
    result = evaluate(doc, args.input_json)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": result["ready_for_human_review"],
                "decision": result["decision"],
                "violations": len(result["violations"]),
                "output": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["ready_for_human_review"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
