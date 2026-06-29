from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_lexicon_lookup_exception_audit_v1 import (
    INPUT_V2,
    _classify_case,
    main,
)


def test_classify_hangul_case_zero_hit_default(tmp_path: Path) -> None:
    p = tmp_path / "master_codebook_lexicon_v1_1_rows_latest.json"
    p.write_text(
        json.dumps(
            {
                "schema": "master_codebook_lexicon_v1",
                "row_count": 1,
                "entries": [
                    {
                        "atom_id": "a1",
                        "lang": "ko",
                        "normalized_form": "소양",
                        "lexicon_match_method": "test",
                        "morphhb_match_method": "test",
                    }
                ],
                "inputs": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    raw = "소양인에게는 열이 위로 치밀 때 수분 보충이 필요하다."
    row = _classify_case("cmp2_011", raw, cb_path=p)
    assert row["exception_bucket"] in (
        "EXC_HANGUL_DOMINANT_ZERO_HIT",
        "EXC_HANGUL_CJK_BIGRAM_PARTIAL",
        "EXC_OK_DOMAIN_TERM_HITS",
    )


def test_main_writes_audit_when_bench_present() -> None:
    if not INPUT_V2.is_file():
        pytest.skip("bench input missing")
    rc = main()
    assert rc == 0
    out = Path("reports/lexicon_lookup_exception_audit_v1_latest.json")
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lexicon_lookup_exception_audit_v1"
    assert doc["research_only"] is True
    assert doc["track_a_active_write"] is False
    assert doc["case_count"] == 40
