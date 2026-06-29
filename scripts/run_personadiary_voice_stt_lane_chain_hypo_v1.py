#!/usr/bin/env python3
"""PersonaDiary voice STT audit + 4-lane classify chain v1 [HYPO]."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_personadiary_stt_audit_row_hypo_v1 import (  # noqa: E402
    append_stt_audit_row,
    build_paste_stt_audit_row,
    validate_stt_audit_row,
)
from classify_personadiary_voice_lane_hypo_v1 import (  # noqa: E402
    classify_voice_transcript,
    load_transcript_json,
)

STT_SCHEMA = ROOT / "docs/final/schemas/stt_routing_audit_log_v1.schema.json"
DEFAULT_STT_OUT = ROOT / "reports/stt_routing_audit_log_v1.jsonl"
DEFAULT_CLASS_OUT = ROOT / "reports/personadiary_voice_lane_classification_hypo_v1_latest.json"


def run_chain(
    *,
    text: str,
    active_lane_hint: str | None,
    stt_event_id: str,
    session_id: str | None,
    append_stt: bool,
    stt_audit_out: Path,
    classification_out: Path | None,
) -> dict:
    audit_row = build_paste_stt_audit_row(
        event_id=stt_event_id,
        transcript=text,
        session_id=session_id,
    )
    validate_stt_audit_row(audit_row, STT_SCHEMA)
    if append_stt:
        append_stt_audit_row(audit_row, stt_audit_out)

    classification = classify_voice_transcript(
        text,
        active_lane_hint=active_lane_hint,
        stt_event_id=stt_event_id,
    )
    classification["stt_audit_row"] = audit_row
    classification["stt_audit_linked"] = classification.get("stt_event_id") == audit_row["event_id"]

    if classification_out:
        classification_out.parent.mkdir(parents=True, exist_ok=True)
        classification_out.write_text(
            json.dumps(classification, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return classification


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--text", default="")
    ap.add_argument("--transcript-json", type=Path, default=None)
    ap.add_argument("--active-lane-hint", choices=("body", "mind", "work", "rest"), default=None)
    ap.add_argument("--stt-event-id", default="")
    ap.add_argument("--session-id", default="personadiary-cli")
    ap.add_argument("--append-stt-audit", action="store_true")
    ap.add_argument("--stt-audit-out", type=Path, default=DEFAULT_STT_OUT)
    ap.add_argument("--classification-out", type=Path, default=DEFAULT_CLASS_OUT)
    ap.add_argument("--no-classification-out", action="store_true")
    args = ap.parse_args()

    text = args.text
    hint = args.active_lane_hint
    stt_id = args.stt_event_id or str(uuid.uuid4())

    if args.transcript_json:
        loaded = load_transcript_json(args.transcript_json)
        text = loaded["text"]
        hint = hint or loaded.get("active_lane_hint")
        stt_id = args.stt_event_id or loaded.get("stt_event_id") or stt_id

    if not text.strip():
        print("usage: --text or --transcript-json required", file=sys.stderr)
        return 1

    out = run_chain(
        text=text,
        active_lane_hint=hint,
        stt_event_id=stt_id,
        session_id=args.session_id,
        append_stt=args.append_stt_audit,
        stt_audit_out=args.stt_audit_out,
        classification_out=None if args.no_classification_out else args.classification_out,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
