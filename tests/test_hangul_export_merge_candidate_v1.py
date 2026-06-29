import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41687_hangul_curated_export_candidate_v1.json"
)


def test_export_candidate_has_ko_and_meta_when_present():
    if not CANDIDATE.is_file():
        return
    doc = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    meta = doc.get("export_candidate_meta") or {}
    assert meta.get("production_ssot_swap") is False
    ko = sum(1 for e in doc.get("entries") or [] if str(e.get("lang", "")).lower() == "ko")
    assert ko >= 1
    assert doc.get("row_count") == len(doc.get("entries") or [])
