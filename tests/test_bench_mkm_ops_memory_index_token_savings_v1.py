"""Token bench smoke for ops memory index ([HYPO])."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bench_mkm_ops_memory_index_token_savings_v1 import _count_tokens  # noqa: E402


def test_count_tokens_returns_method_and_positive_count() -> None:
    result = _count_tokens("abcd")
    assert result["tokens"] >= 1
    assert "method" in result
