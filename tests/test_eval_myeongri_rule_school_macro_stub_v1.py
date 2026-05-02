# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.eval_myeongri_rule_school_macro_stub_v1 import run_stub


def test_run_stub_empty_rows():
    r = run_stub([])
    assert r["gate"] == "EMPTY"
    assert r["n_rows"] == 0


def test_run_stub_two_rows():
    rows = [
        {"year": 2000, "month": 6, "day": 15, "hour": 12, "is_male": True},
        {"year": 1990, "month": 1, "day": 1, "hour": 0, "is_male": False},
    ]
    r = run_stub(rows)
    assert r["schema"] == "myeongri_rule_school_macro_stub_v1"
    assert r["n_rows"] == 2
    assert r["gate"] == "PASS"
    m = r["mean_vector_4d_rule_school_v1"]
    for k in ("S", "L", "K", "M"):
        assert k in m
        assert 0.0 <= m[k] <= 1.0


def test_cli_writes_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    jl = tmp_path / "in.jsonl"
    jl.write_text(
        json.dumps(
            {"year": 2000, "month": 6, "day": 15, "hour": 12, "is_male": True},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    import scripts.eval_myeongri_rule_school_macro_stub_v1 as mod

    monkeypatch.setattr(
        "sys.argv",
        ["eval_myeongri_rule_school_macro_stub_v1.py", "--in-jsonl", str(jl), "--out-json", str(out)],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["gate"] == "PASS"
