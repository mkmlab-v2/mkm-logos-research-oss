from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.core.hangul_lexicon_tokenizer_harness_v1 import (
    hangul_harness_token_set,
    hangul_stem_candidates,
    hangul_syllable_tokens,
    zone_c_hangul_overlay_forms,
)
from scripts.core.master_codebook_lexicon_v1_bridge import lexicon_hits_for_text
from scripts.build_lexicon_hangul_tokenizer_harness_v1 import main as build_main


def test_hangul_syllable_and_stem_expand() -> None:
    raw = "소양인에게는 열이 위로 치밀 때 수분 보충이 필요하다."
    syll = hangul_syllable_tokens(raw)
    assert "소" in syll
    assert "양" in syll
    stems = hangul_stem_candidates(raw)
    assert "소양" in stems or "소양인" in stems
    harness = hangul_harness_token_set(raw)
    assert len(harness) >= len(syll)


def test_lexicon_hits_with_ko_entry_and_harness(tmp_path: Path) -> None:
    p = tmp_path / "master_codebook_lexicon_v1_1_rows_latest.json"
    p.write_text(
        json.dumps(
            {
                "schema": "master_codebook_lexicon_v1",
                "row_count": 2,
                "entries": [
                    {
                        "atom_id": "k1",
                        "lang": "ko",
                        "normalized_form": "소양",
                        "lexicon_match_method": "test",
                        "morphhb_match_method": "test",
                    },
                    {
                        "atom_id": "k2",
                        "lang": "ko",
                        "normalized_form": "수분",
                        "lexicon_match_method": "test",
                        "morphhb_match_method": "test",
                    },
                ],
                "inputs": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    raw = "소양인에게는 수분 보충이 필요하다."
    d_hits, _ = lexicon_hits_for_text(raw, p)
    h_hits, _ = lexicon_hits_for_text(raw, p, include_hangul_tokenizer_harness=True)
    assert len(h_hits) >= len(d_hits)
    assert "소양" in h_hits or "수분" in h_hits


def test_zone_c_overlay_forms_non_empty() -> None:
    forms = zone_c_hangul_overlay_forms()
    assert "소양" in forms or "소양인" in forms


def test_build_main_writes_report() -> None:
    inp = Path("docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json")
    if not inp.is_file():
        pytest.skip("bench input missing")
    rc = build_main()  # noqa: uses argv=[] when not __main__
    assert rc == 0
    out = Path("reports/lexicon_hangul_tokenizer_harness_v1_latest.json")
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lexicon_hangul_tokenizer_harness_v1"
    assert doc["research_only"] is True
    assert doc["track_a_active_write"] is False
    assert doc["hangul_case_count"] == 30
