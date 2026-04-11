from __future__ import annotations

from scripts.l1_codebook_bypass import build_codebook, extract_literals, restore_from_codebook


def test_extract_restore_roundtrip() -> None:
    text = "Patient ID A123 visited on 2026-04-09 with glucose 128.5 and email ops@example.com"
    masked, slots = extract_literals(text)
    cb = build_codebook(slots)
    out = restore_from_codebook(masked, cb)
    assert out == text
    assert "{{L1_SLOT_" in masked
