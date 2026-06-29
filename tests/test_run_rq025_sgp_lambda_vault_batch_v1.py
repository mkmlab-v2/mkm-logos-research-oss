# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.run_rq025_sgp_lambda_vault_batch_v1 import (  # noqa: E402
    _build_extension_rows,
    _fit_models,
    _read_vault,
    _row_date,
)


def test_extension_rows_increase_dates(tmp_path: Path) -> None:
    vault = tmp_path / "vault.csv"
    rows = [
        {
            "": "2026-03-11",
            "S": "0.44",
            "L": "0.33",
            "K": "0.5641",
            "M": "0.6389",
            "lambda_t": "0.5399",
            "lambda_ma": "0.522",
            "lambda_std": "0.015",
            "z_score": "1.33",
            "gradient": "0.003",
            "alert_level": "L1",
        },
        {
            "": "2026-03-12",
            "S": "0.48",
            "L": "0.31",
            "K": "0.5640",
            "M": "0.6388",
            "lambda_t": "0.5525",
            "lambda_ma": "0.523",
            "lambda_std": "0.015",
            "z_score": "2.05",
            "gradient": "0.003",
            "alert_level": "L2",
        },
    ]
    with vault.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    _, base = _read_vault(vault)
    kospi = {"2026-03-12": 100.0, "2026-03-13": 101.0, "2026-03-16": 99.0}
    models = _fit_models(base, kospi)
    ext = _build_extension_rows(
        base_rows=base,
        new_dates=["2026-03-13", "2026-03-16"],
        kospi=kospi,
        models=models,
    )
    assert len(ext) == 2
    assert _row_date(ext[0]) == "2026-03-13"
    assert float(ext[0]["lambda_t"]) > 0
