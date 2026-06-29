#!/usr/bin/env python3
"""Record human sign-off for BTC calibration research shadow (not operational score)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "reports/btrack_btc_calibration_wf_human_signoff_v1.template.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_calibration_wf_human_signoff_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reviewer", type=str, default="")
    ap.add_argument("--note", type=str, default="")
    ap.add_argument(
        "--acknowledge-btc-calibration-layer-change",
        action="store_true",
        help="Required to approve: confirms calibration BTC shadow layer is intentional.",
    )
    ap.add_argument("--revoke", action="store_true")
    args = ap.parse_args()

    if args.revoke:
        doc = _read(args.out_json) or _read(args.template)
        doc = dict(doc)
        doc["approved"] = False
        doc["instrument_layer_change_acknowledged"] = False
        doc["decision"] = "REVOKED"
        doc["recorded_at_utc"] = _utc_now()
    else:
        if not args.acknowledge_btc_calibration_layer_change:
            print("Refusing approve without --acknowledge-btc-calibration-layer-change", flush=True)
            return 2
        doc = _read(args.template)
        if not doc:
            raise SystemExit(f"missing template: {args.template}")
        doc = dict(doc)
        doc["approved"] = True
        doc["instrument_layer_change_acknowledged"] = True
        doc["decision"] = "APPROVED_RESEARCH_SHADOW_ONLY"
        doc["recorded_at_utc"] = _utc_now()
        if args.reviewer:
            doc["reviewer"] = args.reviewer
        if args.note:
            doc["note"] = args.note
        scope = doc.get("scope") if isinstance(doc.get("scope"), dict) else {}
        scope = dict(scope)
        scope["track_a_merge"] = False
        scope["live_trading"] = False
        scope["auto_promote"] = False
        scope["operational_score_unchanged"] = True
        doc["scope"] = scope

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(
        f"approved={doc.get('approved')} "
        f"decision={doc.get('decision')} "
        f"ack={doc.get('instrument_layer_change_acknowledged')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
