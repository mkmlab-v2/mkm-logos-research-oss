# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.2, L:0.7, K:0.5, M:0.3}
# Balance: 82
# Purpose: Logos corpus loader + batch encoder + nearest-neighbor smoke tests (CPU, small limit).
# Keywords: Logos, pytest, torch, gematria

"""Smoke tests for Logos corpus batch path (CPU). Skips if torch or JSONL missing."""

from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from tools.core.logos_corpus_loader import default_hebrew_greek_jsonl, load_verse_slice
from tools.core.logos_encoder_gpu import LogosEncoder, nearest_logos_neighbors

_MINI_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "logos_mini.jsonl"


def _corpus_path():
    p = default_hebrew_greek_jsonl()
    if not p.is_file():
        pytest.skip(f"Hebrew/Greek JSONL not found: {p}")
    return p


def test_load_verse_slice_limit():
    path = _corpus_path()
    ids, texts = load_verse_slice(path=path, limit=5)
    assert len(ids) == len(texts)
    assert len(ids) <= 5
    assert all(isinstance(t, str) for t in texts)


def test_batch_encode_shape():
    path = _corpus_path()
    _ids, texts = load_verse_slice(path=path, limit=8)
    texts = [t for t in texts if t.strip()]
    if len(texts) < 2:
        pytest.skip("not enough non-empty verse texts")
    enc = LogosEncoder()
    emb = enc.encode_texts_batch_to_logos_embeddings(texts)
    assert emb.shape == (len(texts), 4)
    assert emb.dtype == torch.float32


def test_nearest_neighbors_top1():
    path = _corpus_path()
    _ids, texts = load_verse_slice(path=path, limit=20)
    texts = [t for t in texts if t.strip()]
    if len(texts) < 3:
        pytest.skip("need at least 3 verses")
    enc = LogosEncoder()
    # CPU keeps batch vs single-query encodings aligned; GPU top-k can differ on ties / fp noise.
    dev = "cpu"
    corpus = enc.encode_texts_batch_to_logos_embeddings(texts, device=dev)
    q = enc.encode_texts_batch_to_logos_embeddings([texts[0]], device=dev)
    vals, idx = nearest_logos_neighbors(q.squeeze(0), corpus, k=3)
    assert vals.shape[0] == 3
    assert idx.shape[0] == 3
    assert int(idx[0].item()) == 0


def test_nearest_empty_corpus():
    enc = LogosEncoder()
    q = enc.encode_texts_batch_to_logos_embeddings(["א"])
    empty = torch.zeros(0, 4, dtype=torch.float32)
    vals, idx = nearest_logos_neighbors(q.squeeze(0), empty, k=5)
    assert vals.numel() == 0 and idx.numel() == 0


def test_load_verse_slice_mini_fixture():
    assert _MINI_FIXTURE.is_file(), f"missing fixture: {_MINI_FIXTURE}"
    ids, texts = load_verse_slice(path=_MINI_FIXTURE, limit=10)
    assert len(ids) == len(texts)
    assert len(ids) >= 3
    assert all(isinstance(t, str) and t.strip() for t in texts)


def test_batch_encode_and_neighbors_mini_fixture():
    assert _MINI_FIXTURE.is_file()
    _ids, texts = load_verse_slice(path=_MINI_FIXTURE, limit=10)
    enc = LogosEncoder()
    emb = enc.encode_texts_batch_to_logos_embeddings(texts)
    assert emb.shape == (len(texts), 4)
    q = enc.encode_texts_batch_to_logos_embeddings([texts[0]])
    vals, idx = nearest_logos_neighbors(q.squeeze(0), emb, k=3)
    assert vals.shape[0] == 3 and idx.shape[0] == 3
    assert int(idx[0].item()) == 0


def test_nearest_k_larger_than_corpus_uses_min():
    enc = LogosEncoder()
    assert _MINI_FIXTURE.is_file()
    _ids, texts = load_verse_slice(path=_MINI_FIXTURE, limit=10)
    corpus = enc.encode_texts_batch_to_logos_embeddings(texts)
    n = corpus.shape[0]
    q = enc.encode_texts_batch_to_logos_embeddings([texts[0]])
    vals, idx = nearest_logos_neighbors(q.squeeze(0), corpus, k=99)
    assert vals.shape[0] == n and idx.shape[0] == n
