#!/usr/bin/env python3
"""Build human-picked manifest v2: wave1 (29) + wave2 picks marked Y only ([HYPO])."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V1 = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json"
PICK = ROOT / "docs/final/artifacts/hangul_lexicon_wave2_human_pick_v1_latest.json"
WAVE2 = ROOT / "docs/final/artifacts/hangul_lexicon_wave2_lemma_candidates_v1.json"
OUT = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2_human.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    for path in (V1, PICK, WAVE2):
        if not path.is_file():
            print(f"ABORT: missing {path}", file=sys.stderr)
            return 1
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    pick_doc = json.loads(PICK.read_text(encoding="utf-8"))
    w2 = json.loads(WAVE2.read_text(encoding="utf-8"))
    cand_by_form = {
        str(c.get("form", "")).strip(): c for c in (w2.get("candidates") or []) if c.get("form")
    }
    picked_forms = [
        str(p.get("form", "")).strip()
        for p in (pick_doc.get("picks") or [])
        if str(p.get("pick", "")).upper() == "Y" and str(p.get("form", "")).strip()
    ]
    lemmas: list[dict] = list(v1.get("lemmas") or [])
    seen = {str(x.get("form", "")).strip() for x in lemmas if x.get("form")}
    added: list[str] = []
    for form in picked_forms:
        if form in seen:
            continue
        cand = cand_by_form.get(form) or {}
        lemmas.append(
            {
                "form": form,
                "tier": cand.get("tier", "D_health_clinical"),
                "source": cand.get("source", "wave2_human_pick"),
            }
        )
        seen.add(form)
        added.append(form)
    cap = int(v1.get("max_lemma_count") or 50)
    if len(lemmas) > cap:
        print(f"ABORT: lemma count {len(lemmas)} > cap {cap}", file=sys.stderr)
        return 1
    doc = dict(v1)
    doc["schema"] = "hangul_lexicon_curated_ingest_v2_human"
    doc["generated_at_utc"] = _utc()
    doc["wave"] = "2_human_pick"
    doc["parent_manifest_v1"] = str(V1.relative_to(ROOT)).replace("\\", "/")
    doc["human_pick_ssot"] = str(PICK.relative_to(ROOT)).replace("\\", "/")
    doc["wave2_picked_forms"] = picked_forms
    doc["wave2_picked_count"] = len(picked_forms)
    doc["lemma_count"] = len(lemmas)
    doc["lemmas"] = lemmas
    doc["apply_forbidden"] = True
    doc["track_a_active_write"] = False
    doc["pilot_baseline_lexicon"] = (
        "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json"
    )
    doc["overlay_output_role_v2_human"] = (
        "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_hangul_curated_overlay_v2_human.json"
    )
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": str(OUT), "lemma_count": len(lemmas), "wave2_added": added},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
