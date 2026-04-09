"""Regression tests for lexical semantic metrics in scripts/track_b_semantic_eval.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "track_b_semantic_eval.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("track_b_semantic_eval", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_jaccard_identical_and_disjoint():
    m = _load_mod()
    assert m._jaccard("hello world", "hello world") == pytest.approx(1.0)
    assert m._jaccard("aaa bbb", "ccc ddd") == 0.0


def test_cosine_tokens_identical_and_symmetric():
    m = _load_mod()
    assert m._cosine_token_counts("same words here", "same words here") == pytest.approx(1.0)
    a = m._cosine_token_counts("alpha beta gamma", "beta gamma delta")
    b = m._cosine_token_counts("beta gamma delta", "alpha beta gamma")
    assert a == pytest.approx(b)


def test_semantic_fn_accepts_aliases():
    m = _load_mod()
    assert m._semantic_fn("jaccard") is m._jaccard
    assert m._semantic_fn("cosine_tokens") is m._cosine_token_counts


def test_semantic_fn_unknown():
    m = _load_mod()
    with pytest.raises(ValueError, match="unknown"):
        m._semantic_fn("bertscore")
