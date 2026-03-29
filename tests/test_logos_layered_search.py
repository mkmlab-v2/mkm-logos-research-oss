# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.2, L:0.7, K:0.5, M:0.2}
# Balance: 84
# Purpose: Unit tests for logos_layered_search helpers and secondary global cap (no regime/finance).
# Keywords: Logos, pytest, layered search

"""Tests for ``tools.core.logos_layered_search`` (CPU, no GPU required for helpers)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tools.core.logos_layered_search import (
    LayeredHit,
    _cosine_scores_batch,
    layered_search,
)


def test_cosine_scores_batch_orthogonal():
    q = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    rows = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
    s = _cosine_scores_batch(q, rows)
    assert s.shape == (2,)
    assert s[0] > 0.99
    assert s[1] < 0.01


@patch("tools.core.logos_layered_search.search_manuscript_file_topk")
@patch("tools.core.logos_layered_search.search_canon_topk")
def test_secondary_global_cap_after_merge(mock_canon, mock_ms):
    """DSS + apocrypha may each return up to secondary_top_k; result must cap globally."""
    mock_canon.return_value = ([], np.ones(4, dtype=np.float64))

    def _fake_ms(_enc, _qemb, _path, **kwargs):
        k = int(kwargs.get("top_k", 5))
        return [
            LayeredHit(
                verse_id=f"v{i}",
                score=float(1.0 - i * 0.01),
                source="dss",
                text_preview="",
                meta={},
            )
            for i in range(k)
        ]

    mock_ms.side_effect = _fake_ms
    r = layered_search(
        "query",
        encoder=MagicMock(),
        canon_top_k=5,
        secondary_top_k=3,
        manuscript_paths={
            "dss": Path("dummy_dss.jsonl"),
            "apocrypha": Path("dummy_apo.jsonl"),
        },
    )
    assert len(r.secondary_hits) == 3
    assert r.secondary_hits[0].score >= r.secondary_hits[1].score >= r.secondary_hits[2].score
