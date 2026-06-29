#!/usr/bin/env python3
"""Record human sign-off for 31k/41k shadow allowlist review (research-only; not Track A)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "reports/btrack_31k41k_shadow_human_signoff_v1.template.json"
DEFAULT_OUT = ROOT / "reports/btrack_31k41k_shadow_human_signoff_latest.json"


def _iso_now() -> str:
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
        "--revoke",
        action="store_true",
        help="Write approved=false / decision=REVOKED.",
    )
    args = ap.parse_args()

    if args.revoke:
        doc = _read(args.out_json) or _read(args.template)
        doc["approved"] = False
        doc["decision"] = "REVOKED"
        doc["recorded_at_utc"] = _iso_now()
    else:
        doc = _read(args.template)
        if not doc:
            raise SystemExit(f"missing template: {args.template}")
        doc = dict(doc)
        doc["approved"] = True
        doc["decision"] = "APPROVED"
        doc["recorded_at_utc"] = _iso_now()
        if args.reviewer:
            doc["reviewer"] = args.reviewer
        if args.note:
            doc["note"] = args.note
        scope = doc.get("scope") if isinstance(doc.get("scope"), dict) else {}
        scope = dict(scope)
        scope["track_a_merge"] = False
        scope["live_trading"] = False
        doc["scope"] = scope

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"approved={doc.get('approved')} decision={doc.get('decision')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
