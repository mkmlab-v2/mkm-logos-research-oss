from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_master_codebook_hangul_bench_overlay_v1 import build_overlay, _ko_entry


def test_ko_entry_schema() -> None:
    e = _ko_entry("소양")
    assert e["lang"] == "ko"
    assert e["normalized_form"] == "소양"
    assert e["atom_id"].startswith("hangul_bench_hypo_v1::")


def test_build_overlay_adds_ko(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    base.write_text(
        json.dumps(
            {
                "schema": "master_codebook_lexicon_v1",
                "row_count": 1,
                "entries": [
                    {
                        "atom_id": "greek::test",
                        "lang": "greek",
                        "normalized_form": "test",
                        "lexicon_match_method": "x",
                        "morphhb_match_method": "x",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "overlay.json"
    meta = build_overlay(base, ["소양", "수분"], out)
    assert meta["atom_ids_added_count"] == 2
    doc = json.loads(out.read_text(encoding="utf-8"))
    forms = {e["normalized_form"] for e in doc["entries"] if e.get("lang") == "ko"}
    assert "소양" in forms
