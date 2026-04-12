# -*- coding: utf-8 -*-
"""Smoke tests for log vs Myeongri correlation spike (B-track)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.spike_log_myeongri_correlation_v1 import (
    MIN_VALID_WINDOWS_DEFAULT,
    run_correlation,
)


def _row(
    *,
    hour: int,
    total_requests: int,
    error_count: int,
    unique_trace_ids: int,
    run_id: str = "pytest_spike_log_myeongri_v1",
) -> dict:
    base = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc) + timedelta(hours=hour)
    return {
        "schema": "log_myeongri_correlation_input_row_v1",
        "run_metadata": {
            "run_id": run_id,
            "source": "api_gateway_auth",
            "environment": "staging",
        },
        "window_start_utc": base.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_minutes": 5,
        "metrics": {
            "total_requests": total_requests,
            "error_count": error_count,
            "unique_trace_ids": unique_trace_ids,
        },
    }


def test_run_correlation_aborts_below_min_windows() -> None:
    rows = [_row(hour=i, total_requests=100 + i, error_count=i, unique_trace_ids=90 + i) for i in range(10)]
    doc = run_correlation(rows, min_valid_windows=30, is_solar=True, is_male=True)
    assert doc["schema"] == "log_myeongri_correlation_output_v0"
    assert doc["boundary_ack"] is True
    r = doc["results"]["L_axis_vs_error_rate"]
    assert r["pearson"] is None
    assert r["aborted_reason"] is not None


def test_run_correlation_produces_metrics_with_enough_rows() -> None:
    rows = [_row(hour=i, total_requests=200 + i * 3, error_count=i % 5, unique_trace_ids=150 + i) for i in range(35)]
    doc = run_correlation(
        rows,
        min_valid_windows=MIN_VALID_WINDOWS_DEFAULT,
        is_solar=True,
        is_male=True,
    )
    assert doc["hypothesis_tier"] == "B"
    for key in ("L_axis_vs_error_rate", "M_axis_vs_diversity", "L2_norm_vs_total_requests"):
        block = doc["results"][key]
        assert block["valid_windows"] == 35
        assert block["skipped_windows_zero_requests"] == 0
        assert block["pearson"] is not None or block["spearman"] is not None
        assert block["aborted_reason"] is None


def test_zero_total_requests_skipped() -> None:
    rows = [_row(hour=i, total_requests=100, error_count=1, unique_trace_ids=99) for i in range(40)]
    rows[0]["metrics"]["total_requests"] = 0
    doc = run_correlation(rows, min_valid_windows=30, is_solar=True, is_male=True)
    assert doc["results"]["L_axis_vs_error_rate"]["valid_windows"] == 39
    assert doc["results"]["L_axis_vs_error_rate"]["skipped_windows_zero_requests"] == 1
