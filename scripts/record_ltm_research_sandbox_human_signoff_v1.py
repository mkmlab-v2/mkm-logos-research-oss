#!/usr/bin/env python3
"""Record human sign-off for LTM research sandbox graph append (research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "reports/ltm_research_sandbox_human_signoff_v1.template.json"
DEFAULT_OUT = ROOT / "reports/ltm_research_sandbox_human_signoff_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reviewer", default="")
    ap.add_argument("--note", default="")
    ap.add_argument(
        "--acknowledge-ltm-graph-append",
        action="store_true",
        help="Required to approve manual CONCEPT_SPECS append after ingest gates.",
    )
    ap.add_argument("--revoke", action="store_true")
    args = ap.parse_args()

    if args.revoke:
        doc = _read(args.out_json) or _read(args.template)
        doc = dict(doc)
        doc["approved"] = False
        doc["acknowledge_ltm_graph_append"] = False
        doc["decision"] = "REVOKED"
        doc["recorded_at_utc"] = _utc_now()
    else:
        if not args.acknowledge_ltm_graph_append:
            print(
                "Refusing approve without --acknowledge-ltm-graph-append",
                file=sys.stderr,
            )
            return 2
        doc = _read(args.template)
        if not doc:
            raise SystemExit(f"missing template: {args.template}")
        doc = dict(doc)
        doc["approved"] = True
        doc["acknowledge_ltm_graph_append"] = True
        doc["decision"] = "APPROVED_RESEARCH_LTM_APPEND_ONLY"
        doc["recorded_at_utc"] = _utc_now()
        if args.reviewer:
            doc["reviewer"] = args.reviewer
        if args.note:
            doc["note"] = args.note
        scope = dict(doc.get("scope") or {})
        scope["track_a_merge"] = False
        scope["live_trading"] = False
        scope["auto_promote"] = False
        scope["auto_edit_concept_specs"] = False
        doc["scope"] = scope

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"approved={doc.get('approved')} ack={doc.get('acknowledge_ltm_graph_append')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
