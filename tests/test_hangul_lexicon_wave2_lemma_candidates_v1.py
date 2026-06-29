"""Wave-2 lemma candidates manifest (offline)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_wave2_candidates_respect_cap_and_exclude_v1() -> None:
    v1_path = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json"
    out_path = ROOT / "docs/final/artifacts/hangul_lexicon_wave2_lemma_candidates_v1.json"
    if not v1_path.is_file() or not out_path.is_file():
        return
    v1 = {str(x["form"]) for x in json.loads(v1_path.read_text(encoding="utf-8")).get("lemmas", [])}
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc.get("apply_forbidden") is True
    cands = doc.get("candidates") or []
    forms = {str(c["form"]) for c in cands}
    assert forms.isdisjoint(v1)
    assert doc["wave1_lemma_count"] + doc["wave2_candidate_count"] <= doc["max_total_lemma_cap"]
