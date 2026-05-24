"""lexicon_atom_sequence_for_text bridge smoke."""

from __future__ import annotations

from scripts.core.master_codebook_lexicon_v1_bridge import (
    clear_codebook_cache,
    lexicon_atom_sequence_for_text,
    resolve_latest_codebook_path,
)


def test_lexicon_atom_sequence_returns_ordered_ids():
    clear_codebook_cache()
    path = resolve_latest_codebook_path()
    if path is None:
        return
    seq, meta = lexicon_atom_sequence_for_text("demo strong morph reference", path)
    assert meta.get("status") == "ok"
    assert isinstance(seq, list)
    assert len(seq) >= 1
    assert all("::" in x or len(x) > 0 for x in seq)
