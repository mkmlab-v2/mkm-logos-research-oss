#!/usr/bin/env python3
"""Second sign-off: merge curated ko into export candidate (not production SSOT)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports/hangul_lexicon_export_merge_signoff_v1_latest.json"
INGEST_SIGNOFF = ROOT / "reports/hangul_lexicon_curated_ingest_signoff_v1_latest.json"
READINESS = ROOT / "reports/hangul_lexicon_ingest_pipeline_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commander-export-merge-approve",
        action="store_true",
        help="Approve export candidate build (requires ingest signoff + pipeline_ready).",
    )
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    ingest = json.loads(INGEST_SIGNOFF.read_text(encoding="utf-8")) if INGEST_SIGNOFF.is_file() else {}
    ready = json.loads(READINESS.read_text(encoding="utf-8")) if READINESS.is_file() else {}

    ingest_ok = bool(ingest.get("approved"))
    pipeline_ready = bool(ready.get("pipeline_ready"))

    if args.commander_export_merge_approve and (not ingest_ok or not pipeline_ready):
        print("ABORT: need ingest signoff approved + pipeline_ready readiness")
        return 1

    doc = {
        "schema": "hangul_lexicon_export_merge_signoff_v1",
        "recorded_at_utc": _utc(),
        "reviewer": str(args.reviewer),
        "approved": bool(args.commander_export_merge_approve),
        "decision": "APPROVED" if args.commander_export_merge_approve else "PENDING",
        "scope": {
            "research_only": True,
            "track_a_active_write": False,
            "production_ssot_swap": False,
            "export_candidate_build": True,
            "note": "Authorizes master_codebook export CANDIDATE only — not 41658_rows_latest overwrite.",
        },
        "prerequisites": {
            "ingest_signoff": str(INGEST_SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
            "ingest_signoff_approved": ingest_ok,
            "pipeline_readiness": str(READINESS.relative_to(ROOT)).replace("\\", "/"),
            "pipeline_ready": pipeline_ready,
        },
        "commander_note": str(args.note).strip() or None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "approved": doc["approved"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
