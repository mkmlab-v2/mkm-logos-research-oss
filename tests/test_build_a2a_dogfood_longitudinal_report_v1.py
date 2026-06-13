"""Dogfood longitudinal report smoke."""

from __future__ import annotations

from pathlib import Path

from scripts.build_a2a_dogfood_longitudinal_report_v1 import build_report


def test_dogfood_report_ok_with_existing_logs():
    doc = build_report(Path(__file__).resolve().parents[1])
    assert doc["schema"] == "a2a_dogfood_longitudinal_report_v1"
    assert doc["report_ok"] is True
    assert doc["log_row_counts"]["l1_l2_chain"] >= 1
