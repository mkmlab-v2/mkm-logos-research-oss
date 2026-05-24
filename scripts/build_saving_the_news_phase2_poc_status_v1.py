#!/usr/bin/env python3
"""Phase 2 PoC status — matrix view readiness snapshot."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
MATRIX = ART / "saving_the_news_phase2_matrix_view_v1_latest.json"
PHASE1 = ART / "saving_the_news_phase1_poc_status_v1_latest.json"
OUT_JSON = ART / "saving_the_news_phase2_poc_status_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_status() -> dict[str, Any]:
    matrix = _read(MATRIX) or {}
    phase1 = _read(PHASE1) or {}
    p1_ok = bool((phase1.get("exit_criteria") or {}).get("promote_to_phase2"))
    rows = matrix.get("matrix_rows") or []
    official_present = sum(
        1 for r in rows if r.get("lens_id") in {"sasang", "myeongni", "logos"} and r.get("present")
    )
    streams_present = sum(1 for r in rows if r.get("lens_id") in {"news", "macro"} and r.get("present"))

    exit_criteria = {
        "phase1_promote_gate": p1_ok,
        "P2-S1_matrix_json": MATRIX.is_file(),
        "P2-S2_matrix_md": (ART / "saving_the_news_phase2_matrix_view_v1_latest.md").is_file(),
        "P2-S3_official_lenses_present": official_present >= 3,
        "P2-S4_streams_present": streams_present >= 2,
        "P2-S5_conflict_resolver": bool(matrix.get("conflict_resolver")),
        "P2-S6_final_action_labeled": bool((matrix.get("final_action") or {}).get("action")),
        "promote_to_phase3": (
            p1_ok
            and MATRIX.is_file()
            and official_present >= 3
            and streams_present >= 2
            and bool((matrix.get("final_action") or {}).get("action"))
        ),
    }

    return {
        "schema": "saving_the_news_phase2_poc_status_v1",
        "phase": "Phase 2 — Multi-Lens Matrix View",
        "status": "POC_COMPLETE" if exit_criteria["promote_to_phase3"] else "POC_IN_PROGRESS",
        "lane": "research_only",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "exit_criteria": exit_criteria,
        "matrix_snapshot": {
            "final_action": (matrix.get("final_action") or {}).get("action"),
            "conflict": (matrix.get("conflict_resolver") or {}).get("conflict"),
            "headline": (matrix.get("headline_anchor") or {}).get("headline", "")[:120],
        },
        "explicit_gaps": [
            "Not a consumer news portal or engagement feed.",
            "Per-headline streaming matrix not wired to CMS.",
            "Logos remains [NON_GATING] — no price prophecy from scripture lane.",
        ],
        "refs": {
            "matrix_json": "docs/final/artifacts/saving_the_news_phase2_matrix_view_v1_latest.json",
            "phase1_status": "docs/final/artifacts/saving_the_news_phase1_poc_status_v1_latest.json",
        },
    }


def main() -> int:
    doc = build_status()
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON.name} status={doc['status']} promote_to_phase3={doc['exit_criteria']['promote_to_phase3']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
