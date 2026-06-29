#!/usr/bin/env python3
"""Record commander L3 ack for KOSPI Field band shadow research lane [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_packet_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_v1_latest.json"
DEFAULT_LOCAL = ROOT / "data/personalization/commander_kospi_field_band_l3_ack_v1.local.json"
DEFAULT_LOG = ROOT / "reports/kospi_field_band_commander_ack_log_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_ack_doc(
    *,
    packet: dict[str, Any],
    ack_reference: str,
    reviewer: str = "commander",
    note: str = "",
) -> dict[str, Any]:
    ref = ack_reference.strip()
    if not ref:
        raise ValueError("ack_reference required")

    now = _utc()
    return {
        "schema": "kospi_field_band_commander_ack_v1",
        "generated_at_utc": now,
        "hypothesis_tier": "B",
        "research_only": True,
        "classification": "INTERNAL_ONLY",
        "ladder_stage": "L3_commander_ack",
        "decision": "ACK_L3_BAND_SHADOW_RESEARCH",
        "acknowledged": True,
        "ack_by": reviewer,
        "ack_utc": now,
        "ack_reference": ref,
        "send_gate": "HOLD",
        "auto_apply": False,
        "scope_confirmed": {
            "field_band_layer_only": True,
            "direction_fusion_excluded": True,
            "no_live_trading_inject": True,
            "no_track_a_auto_merge": True,
            "science_backfill_caveat_read": True,
        },
        "packet_snapshot": {
            "ack_ready": packet.get("ack_ready"),
            "metrics": packet.get("metrics"),
            "caveats_ko": packet.get("caveats_ko"),
            "scope_if_ack": packet.get("scope_if_ack"),
        },
        "track_wall": packet.get("track_wall") or {},
        "note_ko": note.strip() or "L3: Field band shadow 연구 레인 commander ack — L4·실매매 별도.",
        "evidence_pointers": packet.get("evidence_pointers") or {},
        "boundary_ack": (
            "L3 ack = B-track band shadow 연구 승인. Track A·live·send_gate OPEN 아님."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ack-reference", required=True, help="e.g. COMMANDER-KOSPI-BAND-L3-ACK-2026-06-23")
    ap.add_argument("--packet-json", type=Path, default=DEFAULT_PACKET)
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    ap.add_argument("--force", action="store_true", help="Record even if packet ack_ready is false.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--local-out", type=Path, default=DEFAULT_LOCAL)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--skip-local", action="store_true")
    args = ap.parse_args()

    packet = _read(args.packet_json)
    if not packet.get("ack_ready") and not args.force:
        print(
            json.dumps(
                {"ok": False, "error": "packet_not_ack_ready", "action": packet.get("recommended_commander_action")},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    doc = build_ack_doc(
        packet=packet,
        ack_reference=args.ack_reference,
        reviewer=args.reviewer,
        note=args.note,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    if not args.skip_local:
        args.local_out.parent.mkdir(parents=True, exist_ok=True)
        args.local_out.write_text(payload, encoding="utf-8")
    args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.log_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(json.dumps({"ok": True, "decision": doc["decision"], "ack_reference": doc["ack_reference"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
