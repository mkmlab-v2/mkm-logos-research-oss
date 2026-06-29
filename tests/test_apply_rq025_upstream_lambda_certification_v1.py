# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.apply_rq025_upstream_lambda_certification_v1 import _diff_rows, _row_date


def test_diff_rows_basic(tmp_path: Path) -> None:
    left = {"2025-07-01": {"S": "1.0", "L": "2.0", "K": "3.0", "M": "4.0", "lambda_t": "5.0", "lambda_ma": "5.0", "lambda_std": "1.0", "z_score": "0.1", "gradient": "0.01", "": "2025-07-01"}}
    right = dict(left)
    right["2025-07-01"] = dict(left["2025-07-01"])
    right["2025-07-01"]["lambda_t"] = "5.5"
    out = _diff_rows(left, right, dates=["2025-07-01"])
    assert out["n_compared"] == 1
    assert float(out["max_abs_delta_any"]) == 0.5


def test_cert_gate_dry_run(tmp_path: Path) -> None:
    vault = tmp_path / "vault.csv"
    preview = tmp_path / "preview.csv"
    batch = tmp_path / "batch.json"
    fields = ["", "S", "L", "K", "M", "lambda_t", "lambda_ma", "lambda_std", "z_score", "gradient", "alert_level"]
    row = {
        "": "2026-03-16",
        "S": "1",
        "L": "1",
        "K": "1",
        "M": "1",
        "lambda_t": "1",
        "lambda_ma": "1",
        "lambda_std": "1",
        "z_score": "0",
        "gradient": "0",
        "alert_level": "L0",
    }
    for p in (vault, preview):
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerow(row)
    batch.write_text(
        json.dumps(
            {
                "new_date_min": "2026-03-16",
                "new_date_max": "2026-03-16",
                "implementation": "test",
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "cert.json"
    from scripts.apply_rq025_upstream_lambda_certification_v1 import main

    rc = main(
        [
            "--vault-csv",
            str(vault),
            "--proxy-preview-csv",
            str(preview),
            "--batch-log-json",
            str(batch),
            "--certified-csv",
            str(tmp_path / "missing.csv"),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "awaiting_certified_csv"
    assert doc["certification_pass"] is False
