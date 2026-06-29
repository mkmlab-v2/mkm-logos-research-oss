#!/usr/bin/env python3
"""Record commander planning sign-off for Track L external send (does NOT set ready_for_external_send true)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNOFF = ROOT / "docs/final/artifacts/logos_track_l_external_send_signoff_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_l_commander_external_send_ack_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reviewer", type=str, default="commander")
    ap.add_argument(
        "--decision",
        type=str,
        default="HOLD_NO_EXTERNAL_SEND",
        help="Planning ack only; external send still blocked without legal counsel.",
    )
    ap.add_argument(
        "--notes",
        type=str,
        default="Track L L9-L12 internal draft ack; PUBLIC_FACING lint passed; no external send.",
    )
    args = ap.parse_args()

    signoff_path = args.signoff_json if args.signoff_json.is_absolute() else ROOT / args.signoff_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    if not signoff_path.is_file():
        raise SystemExit(f"Missing signoff template: {signoff_path}")

    signoff = _read_json(signoff_path)
    l912 = ROOT / "docs/final/artifacts/logos_track_l_l9_l12_readiness_v1_latest.json"
    l912_doc: dict[str, Any] = {}
    if l912.is_file():
        try:
            l912_doc = _read_json(l912)
        except json.JSONDecodeError:
            l912_doc = {}

    payload: dict[str, Any] = {
        "schema": "logos_track_l_commander_external_send_ack_v1",
        "generated_at_utc": _utc_now(),
        "decision": str(args.decision),
        "reviewer_label": str(args.reviewer),
        "notes": str(args.notes),
        "ready_for_external_send": False,
        "legal_counsel_required_for_external_send": True,
        "l9_l12_ok_at_record": bool(l912_doc.get("l9_l12_ok")),
        "signoff_template_schema": signoff.get("schema"),
        "track_wall": {
            "logos_non_gating": True,
            "a_track_auto_promote": False,
            "live_trading_trigger": False,
        },
        "evidence_paths": {
            "signoff_template": str(signoff_path.resolve()),
            "commander_ack_json": str(out_path.resolve()),
            "public_facing_lint": str((ROOT / "reports/logos_track_l_public_facing_readiness_v1_latest.json").resolve()),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "ready_for_external_send": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
