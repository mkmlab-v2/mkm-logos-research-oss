#!/usr/bin/env python3
"""Append mkm_cursor_turn_meta_v1 line — preserve deep_queue + required SSOT refs."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_mkm_cursor_turn_meta_stub_v1 import build_stub, validate_turn_meta  # noqa: E402
from mkm_cursor_continuity_ssot_v1 import (  # noqa: E402
    REQUIRED_SSOT_REFS,
    merge_deep_fetch_queue,
    missing_required_paths,
    read_jsonl_tail,
    required_ssot_refs_payload,
    verify_required_files_exist,
)
from mkm_cursor_self_audit_lib_v1 import build_self_audit  # noqa: E402

DEFAULT_ENVELOPE = ROOT / "docs/final/artifacts/mkm_cursor_deep_handoff_envelope_v1_latest.json"
DEFAULT_LOG = ROOT / "reports/mkm_cursor_turn_meta_log.jsonl"
DEFAULT_RESOLVE = ROOT / "reports/mkm_deep_fetch_resolve_smoke_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_turn_record(
    *,
    lane: str,
    continuity_id: str,
    envelope: dict[str, Any],
    deep_reads: list[dict[str, Any]] | None = None,
    verify_status: str = "partial",
    checkpoint_message: str = "",
) -> dict[str, Any]:
    prev = read_jsonl_tail(DEFAULT_LOG, continuity_id=continuity_id)
    prev_queue = (prev or {}).get("deep_fetch_next") or []
    merged_queue = merge_deep_fetch_queue(
        list(prev_queue),
        list(envelope.get("deep_fetch_next") or []),
    )
    missing = missing_required_paths(merged_queue)
    if missing:
        merged_queue = merge_deep_fetch_queue(merged_queue, missing)

    doc = build_stub(
        lane=lane,
        continuity_id=continuity_id,
        turn_id=f"cursor-turn-{uuid.uuid4().hex[:12]}",
        deep_fetch_next=merged_queue,
        deep_reads=deep_reads or [],
    )
    doc["generated_at_utc"] = _utc_now()
    doc["verify_status"] = verify_status if not missing else "partial"
    doc["required_ssot_refs"] = required_ssot_refs_payload()
    doc["required_ssot_missing"] = missing
    doc["meta_coordinator"] = {
        "mission_log_mode": "next_one_table_pin_only",
        "resume_trigger_ko": "장기기억 맥락이어",
        "never_paste": "Full MISSION_LOG.md",
        "checkpoint_message": checkpoint_message.strip(),
    }
    if missing:
        doc["unverified_claims"] = [f"missing_required_ssot:{p}" for p in missing]
    else:
        doc["unverified_claims"] = []
    doc["self_audit"] = build_self_audit(
        lookback_performed=bool(deep_reads),
        deep_reads_count=len(deep_reads or []),
        violation_flags=[f"missing_required_ssot:{p}" for p in missing] if missing else [],
    )
    return doc


def append_turn(doc: dict[str, Any], log_path: Path) -> None:
    errs = validate_turn_meta(doc)
    if errs:
        raise ValueError("; ".join(errs))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", default="infra")
    parser.add_argument("--continuity-id", required=True)
    parser.add_argument("--envelope", type=Path, default=DEFAULT_ENVELOPE)
    parser.add_argument("--resolve-json", type=Path, default=DEFAULT_RESOLVE)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--checkpoint-message", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    missing_files = verify_required_files_exist(ROOT)
    if missing_files:
        print(f"WARN: required SSOT files missing: {missing_files}", file=sys.stderr)

    if not args.envelope.is_file():
        print(f"FAIL: envelope missing: {args.envelope}", file=sys.stderr)
        return 1

    envelope = _read_json(args.envelope)
    deep_reads: list[dict[str, Any]] = []
    if args.resolve_json.is_file():
        resolved = _read_json(args.resolve_json)
        for p in resolved.get("paths") or []:
            deep_reads.append({"path": p, "status": "read"})

    doc = build_turn_record(
        lane=args.lane,
        continuity_id=args.continuity_id,
        envelope=envelope,
        deep_reads=deep_reads[:3],
        checkpoint_message=args.checkpoint_message,
    )

    if doc.get("required_ssot_missing"):
        print(f"WARN: patched queue; was missing: {doc['required_ssot_missing']}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0

    append_turn(doc, args.log)
    print(f"APPENDED: {args.log}")
    print(f"continuity_id={args.continuity_id} deep_fetch_next={len(doc['deep_fetch_next'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
