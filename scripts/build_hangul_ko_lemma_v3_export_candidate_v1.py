#!/usr/bin/env python3
"""Formalize v3 Golden-40 evidence export candidate (41676 rows, promotion: HOLD)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT = ROOT / "reports/constitution/btrack_pilot"
MANIFEST = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v3_golden40_evidence.json"
OVERLAY = PILOT / "master_codebook_lexicon_v1_41676_hangul_curated_overlay_v3_golden40_evidence.json"
BASE = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
PROD_POINTER = PILOT / "master_codebook_bench_lexicon_pointer_v1_latest.json"
V3_PILOT = ROOT / "reports/lexicon_hangul_curated_pilot_v3_golden40_evidence_latest.json"
CANDIDATE_OUT = PILOT / "master_codebook_lexicon_v1_41676_hangul_curated_export_candidate_v3_golden40_evidence.json"
REPORT_OUT = ROOT / "reports/hangul_ko_lemma_v3_export_candidate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _ko_count(doc: dict[str, Any]) -> int:
    return sum(1 for e in doc.get("entries") or [] if str(e.get("lang", "")).lower() == "ko")


def main() -> int:
    missing = [p for p in (MANIFEST, OVERLAY, BASE, V3_PILOT) if not p.is_file()]
    if missing:
        print("ABORT: missing inputs:", ", ".join(_rel(p) for p in missing))
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    pilot = json.loads(V3_PILOT.read_text(encoding="utf-8"))
    base_doc = json.loads(BASE.read_text(encoding="utf-8"))
    prod_pointer = json.loads(PROD_POINTER.read_text(encoding="utf-8")) if PROD_POINTER.is_file() else {}

    ko_n = _ko_count(overlay)
    row_count = int(overlay.get("row_count") or len(overlay.get("entries") or []))
    base_n = int(base_doc.get("row_count") or 41658)
    overlay_meta = overlay.get("overlay_meta") or {}

    payload = dict(overlay)
    payload["generated_at_utc"] = _utc()
    payload["export_candidate_meta"] = {
        "schema": "master_codebook_hangul_curated_export_candidate_v3_golden40_evidence",
        "wave": 3,
        "research_only": True,
        "track_a_active_write": False,
        "production_ssot_swap": False,
        "promotion": "HOLD",
        "promotion_note": "Evidence-only 18-ko Golden-40 hit subset; production pointer remains 41708/ko42 until commander signoff chain.",
        "source_overlay": _rel(OVERLAY),
        "source_manifest": _rel(MANIFEST),
        "pilot_report": _rel(V3_PILOT),
        "base_production_lexicon": _rel(BASE),
        "production_lexicon_pointer": _rel(PROD_POINTER) if PROD_POINTER.is_file() else None,
        "production_pointer_lexicon_file": prod_pointer.get("lexicon_file"),
        "base_row_count": base_n,
        "ko_rows_merged": ko_n,
        "candidate_row_count": row_count,
        "selection_policy": manifest.get("selection_policy"),
        "lemma_count_manifest": manifest.get("lemma_count"),
        "atom_ids_added": overlay_meta.get("atom_ids_added") or [],
        "double_gate_pilot": pilot.get("double_gate"),
        "golden40_compare_curated": (pilot.get("golden40_compare") or {}).get("curated_overlay"),
    }
    payload["row_count"] = row_count

    CANDIDATE_OUT.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATE_OUT.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    gate = pilot.get("double_gate") or {}
    g40 = (pilot.get("golden40_compare") or {}).get("curated_overlay") or {}
    report = {
        "schema": "hangul_ko_lemma_v3_export_candidate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "promotion": "HOLD",
        "send_gate": "HOLD",
        "reproduce": "py scripts/build_hangul_ko_lemma_v3_export_candidate_v1.py",
        "candidate_path": _rel(CANDIDATE_OUT),
        "row_count": row_count,
        "ko_rows": ko_n,
        "lang_distribution": (pilot.get("lexicon_corpus_fact_curated") or {}).get("lang_distribution"),
        "export_candidate_meta": payload["export_candidate_meta"],
        "production_ssot": {
            "pointer_path": _rel(PROD_POINTER) if PROD_POINTER.is_file() else None,
            "lexicon_file": prod_pointer.get("lexicon_file"),
            "note": "41708 file / ko 42 — unchanged; v3 candidate is sealed evidence box only.",
        },
        "verdict": {
            "ready_for_pilot_recheck": True,
            "promote_production_ssot": False,
            "both_pass_from_pilot": bool(gate.get("both_pass")),
        },
        "metrics_snapshot": {
            "global_token_saving_rate": g40.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": g40.get("avg_reconstruction_fidelity_jaccard"),
            "gate1_actual": gate.get("gate1_actual"),
            "gate2_actual_delta_saving": gate.get("gate2_actual_delta_saving"),
        },
        "reproduce_pilot_recheck": (
            "py scripts/run_hangul_curated_ingest_pilot_v1.py "
            f"--manifest {_rel(MANIFEST)} "
            f"--overlay-path {_rel(CANDIDATE_OUT)} "
            "--skip-rebuild-overlay "
            "--out-json reports/lexicon_hangul_curated_pilot_v3_export_candidate_recheck_latest.json"
        ),
    }
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote": _rel(CANDIDATE_OUT),
                "report": _rel(REPORT_OUT),
                "row_count": row_count,
                "ko_rows": ko_n,
                "promotion": "HOLD",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
