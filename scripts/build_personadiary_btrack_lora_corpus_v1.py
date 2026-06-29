#!/usr/bin/env python3
"""Aggregate validated personadiary_btrack_export_v1 inbox files into research JSONL corpus."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_btrack_export_v1.schema.json"
DEFAULT_INBOX = ROOT / "reports/constitution/btrack_pilot/personadiary_export_inbox"
DEFAULT_JSONL = ROOT / "reports/constitution/btrack_pilot/personadiary_lora_corpus_v1_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "reports/personadiary_btrack_lora_corpus_build_latest.json"

BOUNDARY_ACK = (
    "research_only · derived from redacted btrack export · no Track A or mkmlife auto merge"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def export_to_corpus_row(path: Path, export_doc: dict[str, Any]) -> dict[str, Any]:
    payload = export_doc.get("payload") or {}
    north = payload.get("north_star_by_lane_hypo_v1") or {}
    lanes = north.get("lanes") if isinstance(north, dict) else {}
    north_lines: dict[str, str] = {}
    if isinstance(lanes, dict):
        for lane in ("body", "mind", "work", "rest"):
            node = lanes.get(lane) or {}
            if isinstance(node, dict):
                north_lines[lane] = str(node.get("one_line") or "")[:280]

    row: dict[str, Any] = {
        "schema": "personadiary_btrack_lora_corpus_row_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "source_file": str(path.name),
        "source_pseudonym_id": export_doc.get("pseudonym_id"),
        "source_export_generated_at_utc": export_doc.get("generated_at_utc"),
        "week_label": (export_doc.get("source") or {}).get("week_label"),
        "active_lane": payload.get("active_lane"),
        "weekly_top5": payload.get("weekly_top5") or [],
        "next_one_action": payload.get("next_one_action") or {},
        "north_star_lines": north_lines,
        "diary_lane_stats": payload.get("diary_lane_stats"),
        "checkpoint_count": payload.get("checkpoint_count"),
        "redaction": export_doc.get("redaction"),
        "boundary_ack": BOUNDARY_ACK,
        "pack0_b_note": (
            "Adjacent B-track corpus only — not myeongri_deterministic_lora_golden_set_v1 input"
        ),
    }
    return row


def build_corpus(
    *,
    inbox_dir: Path,
    out_jsonl: Path,
    export_schema: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for path in sorted(inbox_dir.glob("*.json")):
        try:
            export_doc = json.loads(path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=export_doc, schema=export_schema)
            if export_doc.get("auto_upload") is not False:
                raise ValueError("auto_upload must be false")
            rows.append(export_to_corpus_row(path, export_doc))
        except Exception as exc:  # noqa: BLE001 — collect per-file errors
            errors.append({"file": path.name, "error": str(exc)[:280]})

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return rows, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inbox-dir", type=Path, default=DEFAULT_INBOX)
    parser.add_argument("--out-jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any inbox file fails")
    args = parser.parse_args()

    export_schema = json.loads(EXPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
    rows, errors = build_corpus(
        inbox_dir=args.inbox_dir,
        out_jsonl=args.out_jsonl,
        export_schema=export_schema,
    )

    summary = {
        "schema": "personadiary_btrack_lora_corpus_build_v1",
        "built_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "inbox_dir": str(args.inbox_dir.relative_to(ROOT)).replace("\\", "/"),
        "out_jsonl": str(args.out_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "rows_written": len(rows),
        "errors": errors,
        "track_wall": {
            "track_a_auto_merge": False,
            "mkmlife_db_join": False,
            "live_trading": False,
            "peft_auto_train": False,
        },
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_jsonl} rows={len(rows)} errors={len(errors)}")
    print(f"WROTE: {args.summary_json}")

    if errors and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
