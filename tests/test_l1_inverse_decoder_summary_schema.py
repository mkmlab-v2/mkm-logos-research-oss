"""Fast Fact-Lock: committed summary JSON shape (no full sweep)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "docs" / "final" / "artifacts" / "l1_inverse_decoder_spike_test_summary_latest.json"


def test_l1_inverse_decoder_summary_schema_and_aggregate() -> None:
    assert SUMMARY.is_file(), f"missing SSOT artifact: {SUMMARY}"
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert data.get("schema") == "l1_inverse_decoder_spike_test_summary_v1"
    agg = data.get("aggregate") or {}
    for key in (
        "avg_exact_restore_rate",
        "min_exact_restore_rate",
        "max_exact_restore_rate",
        "determinism_delta",
    ):
        assert key in agg, f"aggregate missing {key}"
    assert isinstance(data.get("cells"), list)
