"""CSV ingest for Phase 3 leading sensors."""
from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from scripts.ingest_btrack_phase3_leading_sensor_feed_v1 import _read_csv, _row_from_csv


def test_row_from_csv() -> None:
    row = _row_from_csv(
        "onchain_exchange_netflow",
        {"eval_date": "2026-05-01", "signed_flow_z": "0.25", "raw_netflow_btc": "-100"},
    )
    assert row is not None
    assert row["eval_date"] == "2026-05-01"
    assert row["features"]["signed_flow_z"] == 0.25


def test_read_csv_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "feed.csv"
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["eval_date", "signed_flow_z"])
            w.writeheader()
            w.writerow({"eval_date": "2026-05-02", "signed_flow_z": "-0.1"})
        rows, warns = _read_csv(p, "onchain_exchange_netflow")
        assert len(rows) == 1
        assert not warns
