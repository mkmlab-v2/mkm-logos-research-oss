#!/usr/bin/env python3
"""Materialize hangul_lexicon_curated_lemma_manifest_v1.json (≤50 lemmas, no w+ harvest)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.hangul_lexicon_tokenizer_harness_v1 import zone_c_hangul_overlay_forms  # noqa: E402

OUT = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json"
ZONE_C = ROOT / "codebook" / "shards" / "zone_c_hangul.json"
MAX_LEMMAS = 50

# Tier B: sasang / compression domain core (not full cmp2 token harvest)
TIER_B_CORE = [
    "사상의학",
    "사상",
    "체질",
    "소양",
    "태음",
    "소음",
    "태양",
    "소양인",
    "태음인",
    "소음인",
    "태양인",
    "수분",
    "호흡",
    "한글",
    "압축",
    "복원",
]

# Tier C: bench anchor phrases (short, high signal)
TIER_C = [
    "사상의학을",
    "체질에",
    "소양인에게는",
    "태음인은",
    "소음인의",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    lemmas: list[dict] = []
    seen: set[str] = set()

    def add(form: str, tier: str, source: str) -> None:
        if len(lemmas) >= MAX_LEMMAS or not form or form in seen:
            return
        seen.add(form)
        lemmas.append({"form": form, "tier": tier, "source": source})

    for t in sorted(zone_c_hangul_overlay_forms()):
        add(t, "A_zone_c_hard", str(ZONE_C.relative_to(ROOT)).replace("\\", "/"))
    for t in TIER_B_CORE:
        add(t, "B_sasang_core", "MISSION_LOG_hangul_curated_p0")
    for t in TIER_C:
        add(t, "C_domain_anchor", "cmp2_bench_anchor_phrases")

    doc = {
        "schema": "hangul_lexicon_curated_ingest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "max_lemma_count": MAX_LEMMAS,
        "base_lexicon_role": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json",
        "overlay_output_role": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_hangul_curated_overlay.json",
        "tokenizer_harness_flag": "include_hangul_tokenizer_harness",
        "lemmas": lemmas,
        "forbidden_harvest_policy": {
            "auto_w_plus_harvest_from_cmp2": True,
            "note": "392-row harvest overlay is research anti-pattern; see lexicon_hangul_overlay_pilot_v1_latest.json",
        },
        "acceptance_gates": {
            "gate1_cmp2_cases_with_hit_gt_0": 25,
            "gate2_golden40_delta_saving_pp_min": -0.02,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "lemma_count": len(lemmas)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
