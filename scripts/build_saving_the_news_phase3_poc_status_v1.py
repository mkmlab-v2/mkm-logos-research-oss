#!/usr/bin/env python3
"""Phase 3 PoC status snapshot."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
GATING = ART / "saving_the_news_phase3_truth_gating_v1_latest.json"
PHASE2 = ART / "saving_the_news_phase2_poc_status_v1_latest.json"
OUT_JSON = ART / "saving_the_news_phase3_poc_status_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_status() -> dict[str, Any]:
    gating = json.loads(GATING.read_text(encoding="utf-8")) if GATING.is_file() else {}
    p2 = json.loads(PHASE2.read_text(encoding="utf-8")) if PHASE2.is_file() else {}
    combined = bool(gating.get("combined_all_passed"))
    exit_criteria = {
        "phase2_promote_gate": bool((p2.get("exit_criteria") or {}).get("promote_to_phase3")),
        "P3-S1_truth_gating_json": GATING.is_file(),
        "P3-S2_public_event_stub": (ART / "saving_the_news_public_event_ingest_stub_v1.json").is_file(),
        "P3-S3_combined_gates_passed": combined,
        "P3-S4_human_signoff_gate_explicit": True,
        "P3-S5_no_publish_without_human": not bool((gating.get("publish_signoff") or {}).get("cms_publish_allowed")),
        "roadmap_complete_internal": combined and GATING.is_file(),
    }
    return {
        "schema": "saving_the_news_phase3_poc_status_v1",
        "phase": "Phase 3 — Truth Gating API (stub)",
        "status": "POC_COMPLETE" if exit_criteria["roadmap_complete_internal"] else "POC_IN_PROGRESS",
        "lane": "research_only",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "exit_criteria": exit_criteria,
        "gating_snapshot": {
            "outcome_class": gating.get("outcome_class"),
            "combined_all_passed": combined,
            "cms_publish_allowed": (gating.get("publish_signoff") or {}).get("cms_publish_allowed"),
            "streaming_watch_metadata_allowed": (gating.get("publish_signoff") or {}).get(
                "streaming_watch_metadata_allowed"
            ),
        },
        "explicit_gaps": list(gating.get("explicit_not_implemented") or [])
        + ["Legal review before external send", "Production CMS wiring"],
        "refs": {
            "truth_gating": "docs/final/artifacts/saving_the_news_phase3_truth_gating_v1_latest.json",
            "public_event_stub": "docs/final/artifacts/saving_the_news_public_event_ingest_stub_v1.json",
            "public_event_gateway": "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_event_gateway.py",
        },
    }


def main() -> int:
    doc = build_status()
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON.name} status={doc['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
