#!/usr/bin/env python3
"""Phase 1 — patient_care_bundle text via evaluate_report (ACTIVE profile, [HYPO])."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.hangul_curated_eval_config_v1 import evaluate_with_active_profile  # noqa: E402
from scripts.run_hangul_curated_clinical_snippet_lexicon_smoke_v1 import (  # noqa: E402
    DEFAULT_BUNDLES,
    _extract_bundle_text,
)

PILOT = ROOT / "reports/constitution/btrack_pilot"
P41687 = PILOT / "master_codebook_lexicon_v1_41687_rows_latest.json"
OVERLAY_V2 = PILOT / "master_codebook_lexicon_v1_41658_hangul_curated_overlay_v2.json"
OUT = ROOT / "reports/hangul_curated_clinical_evaluate_report_smoke_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _resolve_archived_41658() -> Path | None:
    candidates = sorted(
        PILOT.glob("master_codebook_lexicon_v1_41658_rows_archived_*_pre_hangul_curated.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _bundle_input_doc(bundles: list[tuple[str, str]]) -> dict[str, Any]:
    cases = []
    for i, (ref, text) in enumerate(bundles, start=1):
        cases.append(
            {
                "id": f"clinical_bundle_{i:03d}",
                "lane_id": "zone_c",
                "domain": "medical_ko",
                "raw_text": text,
                "compressed_text": "",
                "reconstructed_text": "",
                "provenance_encounter_ref": ref,
            }
        )
    return {
        "schema": "hangul_curated_clinical_eval_input_v1",
        "description": "Synthetic compression_cases from patient_care_bundle SOAP/slots.",
        "compression_cases": cases,
    }


def _arm_metrics(report: dict[str, Any]) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    cases = cm.get("cases") or []
    n = len(cases)
    if n == 0:
        return {"case_count": 0}
    sav = sum(float(c.get("token_saving_rate") or 0.0) for c in cases) / n
    jac = sum(float(c.get("reconstruction_fidelity_jaccard") or 0.0) for c in cases) / n
    hits = sum(
        1
        for c in cases
        if int((c.get("route") or {}).get("master_codebook_lexicon_v1", {}).get("hit_count") or 0) > 0
    )
    return {
        "case_count": n,
        "avg_token_saving_rate": sav,
        "avg_reconstruction_fidelity_jaccard": jac,
        "cases_with_lexicon_hit_gt_0": hits,
        "sensitive_violation_count": int(cm.get("sensitive_violation_count") or 0),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--include-overlay-v2", action="store_true", help="Also evaluate overlay_v2 arm.")
    args = ap.parse_args()

    p658 = _resolve_archived_41658()
    if p658 is None or not P41687.is_file():
        print("ABORT: lexicon paths missing", file=sys.stderr)
        return 1

    bundles: list[tuple[str, str]] = []
    for bpath in DEFAULT_BUNDLES:
        if not bpath.is_file():
            continue
        doc = json.loads(bpath.read_text(encoding="utf-8"))
        text = _extract_bundle_text(doc)
        if len(text.strip()) < 80:
            continue
        ref = str((doc.get("provenance") or {}).get("encounter_ref") or bpath.stem)
        bundles.append((ref, text))

    if not bundles:
        print("ABORT: no patient bundles with text", file=sys.stderr)
        return 1

    src = _bundle_input_doc(bundles)
    arms: list[tuple[str, Path]] = [
        ("archived_41658", p658),
        ("production_41687", P41687),
    ]
    if args.include_overlay_v2 and OVERLAY_V2.is_file():
        arms.append(("overlay_v2_41658_plus_50", OVERLAY_V2.resolve()))

    arm_results: dict[str, Any] = {}
    for label, lex_path in arms:
        report = evaluate_with_active_profile(src, lexicon_path=lex_path)
        arm_results[label] = {
            "lexicon_path": _rel(lex_path),
            "metrics": _arm_metrics(report),
            "per_case": [
                {
                    "id": c.get("id"),
                    "token_saving_rate": c.get("token_saving_rate"),
                    "reconstruction_fidelity_jaccard": c.get("reconstruction_fidelity_jaccard"),
                    "lexicon_hit_count": (c.get("route") or {})
                    .get("master_codebook_lexicon_v1", {})
                    .get("hit_count"),
                }
                for c in (report.get("compression_metrics") or {}).get("cases") or []
            ],
        }

    m658 = arm_results["archived_41658"]["metrics"]
    m687 = arm_results["production_41687"]["metrics"]
    delta = {
        "avg_token_saving_rate": (m687.get("avg_token_saving_rate") or 0)
        - (m658.get("avg_token_saving_rate") or 0),
        "avg_reconstruction_fidelity_jaccard": (m687.get("avg_reconstruction_fidelity_jaccard") or 0)
        - (m658.get("avg_reconstruction_fidelity_jaccard") or 0),
        "cases_with_lexicon_hit_gt_0": (m687.get("cases_with_lexicon_hit_gt_0") or 0)
        - (m658.get("cases_with_lexicon_hit_gt_0") or 0),
    }

    doc = {
        "schema": "hangul_curated_clinical_evaluate_report_smoke_v1",
        "generated_at_utc": _utc(),
        "hypo_label": "[HYPO]",
        "research_only": True,
        "ms_paste_headline": "HOLD",
        "bundle_count": len(bundles),
        "arms": arm_results,
        "delta_production_minus_archived": delta,
        "verdict": {
            "promote_production_ssot": False,
            "promote_track_a": False,
            "note": "Clinical bundle evaluate_report smoke; not Golden-40 gate.",
        },
    }
    if "overlay_v2_41658_plus_50" in arm_results:
        mv2 = arm_results["overlay_v2_41658_plus_50"]["metrics"]
        doc["delta_v2_minus_archived"] = {
            "avg_token_saving_rate": (mv2.get("avg_token_saving_rate") or 0)
            - (m658.get("avg_token_saving_rate") or 0),
            "avg_reconstruction_fidelity_jaccard": (mv2.get("avg_reconstruction_fidelity_jaccard") or 0)
            - (m658.get("avg_reconstruction_fidelity_jaccard") or 0),
        }

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "bundles": len(bundles),
                "delta": delta,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
