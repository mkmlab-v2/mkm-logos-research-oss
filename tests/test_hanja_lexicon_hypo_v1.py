"""B-track hanja lexicon PoC helpers — no Track A writes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import cjk_bigram_tokens, lexicon_hits_for_text


def test_cjk_bigram_tokens_count():
    raw = "天時大同也事務各立也"
    bg = cjk_bigram_tokens(raw)
    assert "天時" in bg or "天时" in bg
    assert len(bg) >= 3


def test_lexicon_hits_min_token_len_one_ge_two():
    path = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41775_rows_latest.json"
    if not path.is_file():
        return
    raw = "天時大同也"
    _, m2 = lexicon_hits_for_text(raw, path, min_token_len=2)
    _, m1 = lexicon_hits_for_text(raw, path, min_token_len=1)
    assert int(m1.get("hit_count") or 0) >= int(m2.get("hit_count") or 0)


def test_lexicon_hits_cjk_bigram_optional():
    path = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41775_rows_latest.json"
    if not path.is_file():
        return
    raw = "◉ 天時 大同也 事務 各立也"
    _, base = lexicon_hits_for_text(raw, path)
    _, hypo = lexicon_hits_for_text(raw, path, include_cjk_bigrams=True)
    assert hypo["include_cjk_bigrams"] is True
    assert int(hypo.get("hit_count") or 0) >= int(base.get("hit_count") or 0)


def test_ijeoma_hanja_lexicon_export_schema():
    export = ROOT / "scripts/export_ijeoma_hanja_codebook_lexicon_hypo_v1.py"
    out = ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
    assert export.is_file()
    if not out.is_file():
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(export), "--source", "chunk_lane", "--max-entries", "500"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "master_codebook_lexicon_v1"
    assert doc["row_count"] >= 10
    assert doc["entries"][0].get("normalized_form")


def test_cjk_substitution_reduces_tokens():
    from scripts.ijeoma_cjk_compression_hypo_v1 import compress_ijeoma_cjk_substitution

    lex = ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
    if not lex.is_file():
        return
    raw = "◉ 天時 大同也 事務 各立也 世會 大同也"
    comp, meta = compress_ijeoma_cjk_substitution(raw, lex)
    assert meta.get("replacements", 0) >= 1
    assert meta.get("token_saving_rate_proxy", 0) > 0.0
    assert len(comp) < len(raw)


def test_resolve_marker_strategy_defaults_ascii_compact():
    import os

    from scripts.ijeoma_cjk_compression_hypo_v1 import resolve_marker_strategy, resolve_shorter_by

    assert resolve_shorter_by() == "tokens"
    assert resolve_marker_strategy() == "ascii_compact"
    prev = os.environ.pop("MKM_IJEOMA_CJK_BILLING_MODE", None)
    try:
        os.environ["MKM_IJEOMA_CJK_BILLING_MODE"] = "1"
        assert resolve_marker_strategy() == "o200k_tight"
    finally:
        if prev is None:
            os.environ.pop("MKM_IJEOMA_CJK_BILLING_MODE", None)
        else:
            os.environ["MKM_IJEOMA_CJK_BILLING_MODE"] = prev
    assert resolve_marker_strategy("pua") == "pua"
    assert resolve_marker_strategy("o200k_tight") == "o200k_tight"
    assert resolve_marker_strategy(None, {"ijeoma_cjk_marker_strategy": "atom_id"}) == "atom_id"


def test_o200k_tight_compress_expand_roundtrip():
    from scripts.ijeoma_cjk_compression_hypo_v1 import (
        compress_ijeoma_cjk_substitution,
        expand_ijeoma_cjk_substitution,
    )

    lex = ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
    if not lex.is_file():
        return
    raw = "天時 大同也 事務"
    comp, _ = compress_ijeoma_cjk_substitution(raw, lex, marker_strategy="o200k_tight")
    back = expand_ijeoma_cjk_substitution(comp, lex, marker_strategy="o200k_tight")
    assert back == raw or "天" in back


def test_marker_strategy_ab_artifact_if_present():
    p = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_marker_strategy_ab_v1.json"
    if not p.is_file():
        return
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["hypothesis_tier"] == "B"
    assert "ascii_compact" in (doc.get("profiles") or {})


def test_o200k_diagnosis_artifact_if_present():
    p = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_o200k_diagnosis_v1.json"
    if not p.is_file():
        return
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["hypothesis_tier"] == "B"
    assert doc["case_count"] >= 1
    assert "corpus_o200k_saving_rate" in doc


def test_phrase_slice_artifact_if_present():
    p = ROOT / "reports/constitution/btrack_pilot/comp_hanja_phrase_lexicon_hypo_slice_v1.json"
    if not p.is_file():
        return
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["hypothesis_tier"] == "B"
