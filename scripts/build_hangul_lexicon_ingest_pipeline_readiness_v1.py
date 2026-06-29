#!/usr/bin/env python3
"""Consolidate Hangul curated ingest post-signoff readiness ([HYPO])."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SIGNOFF = ROOT / "reports/hangul_lexicon_curated_ingest_signoff_v1_latest.json"
PILOT = ROOT / "reports/lexicon_hangul_curated_pilot_v1_latest.json"
DENYLIST = ROOT / "reports/lexicon_function_word_denylist_pilot_v1_latest.json"
POINTER = ROOT / "reports/constitution/btrack_pilot/master_codebook_bench_lexicon_pointer_v1_latest.json"
EXPORT_SIGNOFF = ROOT / "reports/hangul_lexicon_export_merge_signoff_v1_latest.json"
EXPORT_CANDIDATE = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41687_hangul_curated_export_candidate_v1.json"
)
OUT = ROOT / "reports/hangul_lexicon_ingest_pipeline_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    signoff = _read(SIGNOFF)
    pilot = _read(PILOT)
    deny = _read(DENYLIST)
    pointer = _read(POINTER)

    approved = bool(signoff and signoff.get("approved"))
    both_pass = bool(pilot and (pilot.get("double_gate") or {}).get("both_pass"))

    export_sig = _read(EXPORT_SIGNOFF)
    export_approved = bool(export_sig and export_sig.get("approved"))

    steps = [
        {
            "id": "H1_signoff",
            "ok": approved,
            "artifact": str(SIGNOFF.relative_to(ROOT)).replace("\\", "/") if SIGNOFF.is_file() else None,
        },
        {
            "id": "H2_curated_pilot",
            "ok": both_pass,
            "artifact": str(PILOT.relative_to(ROOT)).replace("\\", "/") if PILOT.is_file() else None,
        },
        {
            "id": "H3_function_word_denylist_pilot",
            "ok": DENYLIST.is_file(),
            "artifact": str(DENYLIST.relative_to(ROOT)).replace("\\", "/") if DENYLIST.is_file() else None,
        },
        {
            "id": "H4_pointer",
            "ok": pointer is not None and bool((pointer.get("research_overlay_hangul_curated") or {}).get("path")),
            "artifact": str(POINTER.relative_to(ROOT)).replace("\\", "/") if POINTER.is_file() else None,
        },
        {
            "id": "H5_export_merge_signoff",
            "ok": export_approved,
            "artifact": str(EXPORT_SIGNOFF.relative_to(ROOT)).replace("\\", "/")
            if EXPORT_SIGNOFF.is_file()
            else None,
        },
        {
            "id": "H6_export_candidate",
            "ok": EXPORT_CANDIDATE.is_file(),
            "artifact": str(EXPORT_CANDIDATE.relative_to(ROOT)).replace("\\", "/")
            if EXPORT_CANDIDATE.is_file()
            else None,
        },
    ]
    pipeline_ready = approved and both_pass and all(s["ok"] for s in steps)

    doc = {
        "schema": "hangul_lexicon_ingest_pipeline_readiness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "pipeline_ready": pipeline_ready,
        "steps": steps,
        "signoff_summary": {
            "approved": approved,
            "decision": (signoff or {}).get("decision"),
        },
        "curated_pilot_summary": (pilot or {}).get("double_gate"),
        "denylist_pilot_delta": ((deny or {}).get("golden40_compare") or {}).get("delta"),
        "export_merge_signoff_approved": export_approved,
        "next_export_pipeline": [
            "Export candidate: master_codebook_lexicon_v1_41687_hangul_curated_export_candidate_v1.json",
            "Swap production_ssot pointer only after Track A promotion sign-off (FAIL-COMP-004).",
            "Never auto-merge 392 harvest or overwrite MULTILENS active report.",
        ],
        "forbidden": [
            "Overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json from this readiness doc.",
            "Swap production_ssot pointer without export + human Track A gate.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "pipeline_ready": pipeline_ready}, ensure_ascii=False))
    return 0 if pipeline_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
