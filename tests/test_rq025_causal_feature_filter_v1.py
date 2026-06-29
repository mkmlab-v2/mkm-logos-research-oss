# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_LIB = _ROOT / "scripts" / "rq025_causal_feature_filter_v1.py"
_BUILD = _ROOT / "scripts" / "build_rq025_causal_feature_filter_poc_v1.py"


def _import_lib():
    sys.path.insert(0, str(_ROOT))
    from scripts import rq025_causal_feature_filter_v1 as mod

    return mod


def test_correlation_prune_drops_collinear_pair() -> None:
    mod = _import_lib()
    rng = np.random.default_rng(0)
    base = rng.normal(size=40)
    x = np.column_stack([base, base * 1.01 + 1e-6, rng.normal(size=40)])
    names = ["a", "b", "noise"]
    x1, n1, dropped = mod.prune_high_correlation(x, names, threshold=0.85)
    assert len(n1) == 2
    assert any(d["feature"] in {"a", "b"} for d in dropped)


def test_pcmci_stub_keeps_lagged_driver_on_synthetic() -> None:
    mod = _import_lib()
    rng = np.random.default_rng(1)
    n = 80
    driver = rng.normal(size=n)
    y = np.zeros(n)
    for t in range(1, n):
        y[t] = 0.8 * driver[t - 1] + 0.1 * rng.normal()
    noise = rng.normal(size=n)
    x = np.column_stack([driver, noise])
    res = mod.run_causal_feature_filter(
        x,
        ["driver", "noise"],
        y,
        mod.CausalFilterConfig(te_min=0.0, pcmci_min_abs_partial=0.15),
    )
    assert "driver" in res.selected_features
    assert "noise" not in res.selected_features


def test_build_poc_on_flow_join_smoke(tmp_path: Path) -> None:
    flow = _ROOT / "reports" / "rq024_a_flow_eval_date_join_poc_v1_latest.json"
    if not flow.is_file():
        pytest.skip("flow join artifact missing")
    out = tmp_path / "rq025.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_BUILD),
            "--flow-join-json",
            str(flow),
            "--fred-join-json",
            str(_ROOT / "reports" / "nonexistent_fred.json"),
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "rq025_causal_feature_filter_poc_v1"
    assert doc["rq_id"] == "RQ-025"
    assert doc["research_only"] is True
    assert doc["track_wall"]["live_trading"] is False
    assert doc["inputs"]["n_rows"] >= 1
    assert isinstance(doc["selected_features"], list)
