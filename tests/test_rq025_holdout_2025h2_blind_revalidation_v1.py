# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.build_rq025_holdout_2025h2_blind_revalidation_v1 import _eval_split


def test_eval_split_ok() -> None:
    import numpy as np

    labeled = [
        ("2025-05-21", np.array([1.0, 0.0]), 1.0),
        ("2025-06-02", np.array([0.5, 0.5]), 0.0),
        ("2025-07-01", np.array([1.0, 1.0]), 1.0),
        ("2025-08-01", np.array([0.0, 1.0]), 0.0),
    ]
    # duplicate to get enough rows
    labeled = labeled * 5
    train = {d for d, _, _ in labeled if d < "2025-07-01"}
    test = {d for d, _, _ in labeled if "2025-07-01" <= d <= "2025-12-31"}
    out = _eval_split(labeled, train_dates=train, test_dates=test)
    assert out["status"] == "ok"
    assert 0.0 <= float(out["test_accuracy"]) <= 1.0
