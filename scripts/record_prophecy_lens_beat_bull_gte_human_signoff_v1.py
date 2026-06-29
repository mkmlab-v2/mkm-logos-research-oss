#!/usr/bin/env python3
"""Record human sign-off for lens beat-bull gte research shadow (not production Track A)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "reports/prophecy_lens_beat_bull_gte_human_signoff_v1.template.json"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_beat_bull_gte_human_signoff_latest.json"


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
        "--acknowledge-gate-definition-change",
        action="store_true",
        help="Required to approve: confirms gt→gte comparator change is intentional.",
    )
    ap.add_argument("--revoke", action="store_true")
    args = ap.parse_args()

    if args.revoke:
        doc = _read(args.out_json) or _read(args.template)
        doc = dict(doc)
        doc["approved"] = False
        doc["gate_definition_change_acknowledged"] = False
        doc["decision"] = "REVOKED"
        doc["recorded_at_utc"] = _utc_now()
    else:
        if not args.acknowledge_gate_definition_change:
            print("Refusing approve without --acknowledge-gate-definition-change", flush=True)
            return 2
        doc = _read(args.template)
        if not doc:
            raise SystemExit(f"missing template: {args.template}")
        doc = dict(doc)
        doc["approved"] = True
        doc["gate_definition_change_acknowledged"] = True
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
        doc["scope"] = scope

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(
        f"approved={doc.get('approved')} "
        f"ack={doc.get('gate_definition_change_acknowledged')} "
        f"decision={doc.get('decision')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
