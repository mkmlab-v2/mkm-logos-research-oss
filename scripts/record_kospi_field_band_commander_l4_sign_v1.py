#!/usr/bin/env python3
"""Record commander L4 scope sign-off for KOSPI Field band Track A discussion [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_L3 = ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_v1_latest.json"
DEFAULT_PREP = ROOT / "docs/final/artifacts/kospi_field_band_l4_prep_packet_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/kospi_field_band_commander_l4_sign_v1_latest.json"
DEFAULT_LOCAL = ROOT / "data/personalization/commander_kospi_field_band_l4_sign_v1.local.json"
DEFAULT_LOG = ROOT / "reports/kospi_field_band_commander_l4_sign_log_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_l4_sign_doc(
    *,
    l3_ack: dict[str, Any],
    prep: dict[str, Any],
    sign_reference: str,
    reviewer: str = "commander",
    note: str = "",
) -> dict[str, Any]:
    ref = sign_reference.strip()
    if not ref:
        raise ValueError("sign_reference required")
    if not l3_ack.get("acknowledged"):
        raise ValueError("L3 ack required before L4 sign")

    now = _utc()
    return {
        "schema": "kospi_field_band_commander_l4_sign_v1",
        "generated_at_utc": now,
        "hypothesis_tier": "B",
        "research_only": True,
        "classification": "INTERNAL_ONLY",
        "ladder_stage": "L4_commander_scope_signed",
        "decision": "SIGN_L4_TRACK_A_DISCUSSION_SCOPE",
        "signed": True,
        "signed_by": reviewer,
        "signed_utc": now,
        "sign_reference": ref,
        "l3_ack_reference": l3_ack.get("ack_reference"),
        "send_gate": "HOLD",
        "auto_apply": False,
        "track_a_go": False,
        "promotion_ready": False,
        "scope_confirmed": {
            "field_band_layer_only": True,
            "direction_fusion_excluded": True,
            "no_live_trading_inject": True,
            "no_track_a_auto_merge": True,
            "science_backfill_caveat_read": True,
            "l4_is_discussion_scope_not_live_go": True,
        },
        "authorized_after_l4_sign": [
            "CONSTITUTION row draft for Field band stack_union research path",
            "Track A commercialization discussion and ECC-scoped prod touch planning",
            "Premium/B-track band stack section refresh on new prophecy days",
            "Monthly prophecy-only nested revalidate routine",
        ],
        "still_forbidden": [
            "start_live_trading.py patch without ECC",
            "VPS auto-apply",
            "send_gate OPEN",
            "direction fusion promotion",
            "Track A compression KPI merge without raw gate",
        ],
        "prep_snapshot": {
            "summary_metrics": prep.get("summary_metrics"),
            "nested_revalidation_pass": (prep.get("summary_metrics") or {}).get("nested_revalidation_pass"),
        },
        "note_ko": note.strip() or "L4: Track A 논의·CONSTITUTION 초안 범위 서명 — live·send_gate OPEN 아님.",
        "boundary_ack": (
            "L4 sign = discussion·documentation scope. track_a_go·live trading·send_gate OPEN 별도 ECC·지휘관 결정."
        ),
        "reproduce": "py scripts/record_kospi_field_band_commander_l4_sign_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sign-reference", required=True, help="e.g. COMMANDER-KOSPI-BAND-L4-SIGN-2026-06-23")
    ap.add_argument("--l3-ack-json", type=Path, default=DEFAULT_L3)
    ap.add_argument("--prep-json", type=Path, default=DEFAULT_PREP)
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    ap.add_argument("--force", action="store_true", help="Sign even if nested revalidation_pass is false.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--local-out", type=Path, default=DEFAULT_LOCAL)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--skip-local", action="store_true")
    args = ap.parse_args()

    l3 = _read(args.l3_ack_json)
    prep = _read(args.prep_json)
    nested_pass = (prep.get("summary_metrics") or {}).get("nested_revalidation_pass")
    if nested_pass is not True and not args.force:
        print(
            json.dumps({"ok": False, "error": "nested_revalidation_not_pass"}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1

    doc = build_l4_sign_doc(
        l3_ack=l3,
        prep=prep,
        sign_reference=args.sign_reference,
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

    prep_out = dict(prep)
    prep_out["ladder_stage"] = "L4_commander_scope_signed"
    prep_out["l4_sign_reference"] = doc["sign_reference"]
    prep_out["l4_signed_utc"] = doc["signed_utc"]
    DEFAULT_PREP.write_text(json.dumps(prep_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "decision": doc["decision"], "sign_reference": doc["sign_reference"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
