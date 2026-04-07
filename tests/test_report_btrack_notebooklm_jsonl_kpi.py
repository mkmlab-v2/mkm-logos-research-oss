"""Tests for report_btrack_notebooklm_jsonl_kpi."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_scripts = str(ROOT / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from report_btrack_notebooklm_jsonl_kpi import run_kpi  # noqa: E402


def _row(**kwargs):
    base = {
        "schema": "btrack_notebooklm_mega_insight_row_v1",
        "query_id": "q1",
        "notebook_id": "nb1",
        "answer": "Hello [HYPO] B-Track",
        "sources_used": ["s1", "s2"],
        "citations": {"a": 1},
        "references": [{"id": "r1"}],
        "tags": ["t1", "t2"],
    }
    base.update(kwargs)
    return base


def test_run_kpi_counts_and_guardrails():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as tf:
        for r in (
            _row(),
            _row(
                answer="No markers",
                sources_used=[],
                citations={},
                references=[],
                tags=["t1"],
            ),
        ):
            tf.write(json.dumps(r, ensure_ascii=False) + "\n")
        path = Path(tf.name)
    try:
        out = run_kpi(path)
        assert out["schema"] == "btrack_notebooklm_jsonl_kpi_v1"
        assert out["rows_total_valid"] == 2
        assert out["rows_skipped"] == 0
        assert out["distributions"]["n_sources_used"]["max"] == 2
        assert out["distributions"]["answer_char_len"]["count"] == 2
        assert out["guardrail_keyword_rates"]["[HYPO]"] == 0.5
        assert any(t["tag"] == "t1" for t in out["tag_counts_top"])
    finally:
        path.unlink(missing_ok=True)


def test_run_kpi_skips_bad_lines():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as tf:
        tf.write("not json\n")
        tf.write(json.dumps(_row()) + "\n")
        path = Path(tf.name)
    try:
        out = run_kpi(path)
        assert out["rows_total_valid"] == 1
        assert out["rows_skipped"] == 1
    finally:
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
