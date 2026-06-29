#!/usr/bin/env python3
"""Wave-2 curated lemma candidates (≤50 total cap) — manifest only, no apply ([HYPO])."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
V1_MANIFEST = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json"
OUT = ROOT / "docs/final/artifacts/hangul_lexicon_wave2_lemma_candidates_v1.json"
MAX_TOTAL = 50

# Tier D: health / clinical (zone_g_health)
TIER_D_HEALTH = [
    ("건강", "zone_g_health"),
    ("수면", "zone_g_health"),
    ("식사", "zone_g_health"),
    ("증상", "zone_g_health"),
    ("환자", "zone_g_health"),
    ("임상", "zone_g_health"),
    ("진단", "zone_g_health"),
    ("피로", "zone_g_health"),
    ("회복", "zone_g_health"),
    ("체온", "zone_g_health"),
    ("건강검진", "zone_g_health"),
]

# Tier E: myeongni deterministic anchors (not patient-specific predictions)
TIER_E_MYEONGNI = [
    ("명리", "myeongni_lens_core"),
    ("만세력", "myeongni_lens_core"),
    ("사주", "myeongni_lens_core"),
    ("오행", "myeongni_lens_core"),
    ("간지", "myeongni_lens_core"),
    ("일주", "myeongni_lens_core"),
    ("시주", "myeongni_lens_core"),
    ("용신", "myeongni_lens_core"),
    ("십신", "myeongni_lens_core"),
    ("대운", "myeongni_lens_core"),
    ("세운", "myeongni_lens_core"),
    ("절기", "myeongni_lens_core"),
    ("입춘", "myeongni_lens_core"),
]

# Tier F: scm clinical ops (zone_a_scm) — complements sasang
TIER_F_SCM = [
    ("처방", "zone_a_scm"),
    ("금칙", "zone_a_scm"),
    ("처방전", "zone_a_scm"),
    ("한약", "zone_a_scm"),
    ("침구", "zone_a_scm"),
]

SHARD_PATHS = {
    "zone_g_health": "codebook/shards/zone_g_health.json",
    "zone_a_scm": "codebook/shards/zone_a_scm.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_v1_forms() -> set[str]:
    if not V1_MANIFEST.is_file():
        return set()
    doc = json.loads(V1_MANIFEST.read_text(encoding="utf-8"))
    return {str(x.get("form", "")).strip() for x in (doc.get("lemmas") or []) if x.get("form")}


def main() -> int:
    v1_forms = _load_v1_forms()
    v1_count = len(v1_forms)
    slots_remaining = max(0, MAX_TOTAL - v1_count)

    candidates: list[dict[str, Any]] = []
    seen = set(v1_forms)

    def add(form: str, tier: str, source_key: str) -> None:
        if not form or form in seen or len(candidates) >= slots_remaining:
            return
        seen.add(form)
        source = SHARD_PATHS.get(source_key, source_key)
        candidates.append(
            {
                "form": form,
                "tier": tier,
                "source": source,
                "status": "candidate_only",
            }
        )

    for form, sk in TIER_D_HEALTH:
        add(form, "D_health_clinical", sk)
    for form, sk in TIER_E_MYEONGNI:
        add(form, "E_myeongni_core", sk)
    for form, sk in TIER_F_SCM:
        add(form, "F_scm_clinical", sk)

    doc = {
        "schema": "hangul_lexicon_wave2_lemma_candidates_v1",
        "generated_at_utc": _utc(),
        "hypo_label": "[HYPO]",
        "research_only": True,
        "apply_forbidden": True,
        "max_total_lemma_cap": MAX_TOTAL,
        "wave1_manifest": str(V1_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "wave1_lemma_count": v1_count,
        "slots_remaining_under_cap": slots_remaining,
        "wave2_candidate_count": len(candidates),
        "candidates": candidates,
        "next_steps": [
            "Merge selected candidates into hangul_lexicon_curated_lemma_manifest_v2 (human pick).",
            "Run run_hangul_curated_ingest_pilot_v1.py on overlay before any export/apply.",
            "MS/CENTRAL headline remains HOLD.",
        ],
        "forbidden": [
            "392-row w+ harvest from cmp2 token scrape",
            "Auto export to 41687 production without double gate",
            "MS paste headline update from candidate list alone",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "wave1": v1_count,
                "wave2_candidates": len(candidates),
                "slots_remaining": slots_remaining,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
