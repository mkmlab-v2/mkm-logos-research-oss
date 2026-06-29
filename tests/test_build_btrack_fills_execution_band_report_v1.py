"""Tests for fills-only execution band report."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_btrack_fills_execution_band_report_v1.py"


def _import_main():
    import importlib.util

    spec = importlib.util.spec_from_file_location("fills_band", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.main


def test_fills_only_band_counts(tmp_path: Path) -> None:
    wide = tmp_path / "wide.csv"
    with wide.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "utc_date",
                "has_fills",
                "has_prophecy",
                "fill_fill_count",
                "fill_realized_pnl_sum",
                "fill_quote_qty_sum",
                "fill_commission_sum",
            ]
        )
        w.writerow(["2026-01-01", "1", "0", "5", "10.5", "1000", "1.2"])
        w.writerow(["2026-01-02", "1", "1", "3", "2.0", "500", "0.5"])
        w.writerow(["2026-01-03", "1", "0", "2", "-1.0", "200", "0.1"])

    out = tmp_path / "band.json"
    main = _import_main()
    rc = main(["--wide-csv", str(wide), "--out-json", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["counts"]["n_fills_only_days"] == 2
    assert doc["aggregates_fills_only_band"]["realized_pnl_sum"] == 9.5
    assert len(doc["days"]) == 2
