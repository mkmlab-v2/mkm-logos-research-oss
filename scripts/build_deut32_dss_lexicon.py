#!/usr/bin/env python3
"""Build DSS-oriented lexical evidence for Deut 32:8 pilot."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "dss_variant_lexicon_deut32_8_latest.json"


def main() -> int:
    payload = {
        "schema": "dss_variant_lexicon_deut32_8_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "Deut.32:8",
        "term_map": {
            # English semantic hooks mapped to DSS/Hebrew variant families.
            "god": {"dss_weight": 1.0, "hebrew_candidates": ["אלהים", "אל"], "concept": "bene_elohim_family"},
            "sons": {"dss_weight": 0.9, "hebrew_candidates": ["בני"], "concept": "sons_marker"},
            "israel": {"dss_weight": 0.9, "hebrew_candidates": ["ישראל"], "concept": "bene_yisrael_family"},
            "nations": {"dss_weight": 0.8, "hebrew_candidates": ["גוים", "עמים"], "concept": "nations_family"},
            "inheritance": {"dss_weight": 0.8, "hebrew_candidates": ["נחלה"], "concept": "inheritance_family"},
            "boundary": {"dss_weight": 0.8, "hebrew_candidates": ["גבול"], "concept": "boundary_family"},
            "divine": {"dss_weight": 0.7, "hebrew_candidates": ["עליון"], "concept": "elyon_family"},
            "nation": {"dss_weight": 0.6, "hebrew_candidates": ["גוי"], "concept": "nation_family"},
            "tribes": {"dss_weight": 0.5, "hebrew_candidates": ["שבט", "שבטים"], "concept": "tribe_family"},
            "heaven": {"dss_weight": 0.4, "hebrew_candidates": ["שמים"], "concept": "cosmic_scope"},
        },
        "evidence_refs": [
            "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json",
            "reports/constitution/btrack_pilot/btrack_anchor_matrix_latest.json",
        ],
        "boundaries": {
            "fact": [
                "Lexicon is used only as DSS-oriented semantic evidence overlay for pilot scoring.",
            ],
            "hypothesis": [
                "Weights are heuristic and require future alignment with verse-level DSS witness extraction.",
            ],
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: Deut 32:8 DSS lexicon generated")
    print(f"out={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
