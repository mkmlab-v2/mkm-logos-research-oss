# @MKM12-METADATA
# Type: Logic
# Purpose: MKM 4AI max evolution forecast inject smoke (offline deterministic).

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_parse_forecast_probability_map_object_and_list() -> None:
    from scripts.inject_mkm_4ai_forecasts_max_evolution_v1 import parse_forecast_probability_map

    obj = {
        "forecasts": [
            {"question_id": "max.fx.test", "probability_0_1": 0.61},
            {"question_id": "max.eq.test", "probability_0_1": 0.39},
        ]
    }
    m = parse_forecast_probability_map(obj)
    assert m["max.fx.test"] == 0.61
    assert m["max.eq.test"] == 0.39

    m2 = parse_forecast_probability_map(obj["forecasts"])
    assert m2 == m


def test_hybrid_llm_mock_azure_first(monkeypatch) -> None:
    from scripts.inject_mkm_4ai_forecasts_max_evolution_v1 import build_inject_rows
    from scripts.mkm_max_prophecy_4ai_forecast_lib_v1 import SignalContext, load_signal_context

    def fake_llm_once(questions, *, billing, timeout_sec, flash_model, azure_deployment):
        assert billing == "azure"
        return (
            {"max.fx.usdkrw_close_ge_1400_20260731": 0.55},
            {"billing_resolved": "azure", "model_label": "gpt-4o-mini"},
        )

    monkeypatch.setattr(
        "scripts.inject_mkm_4ai_forecasts_max_evolution_v1._llm_batch_probs_once",
        lambda questions, **kw: (
            {"max.fx.usdkrw_close_ge_1400_20260731": 0.55},
            {"billing_resolved": "azure", "model_label": "gpt-4o-mini"},
        )
        if kw.get("billing") == "azure"
        else ({}, {"billing_resolved": "developer", "model_label": "gemini-2.5-flash"}),
    )

    ctx = load_signal_context(_ROOT)
    q = {
        "question_id": "max.fx.usdkrw_close_ge_1400_20260731",
        "domain_tags": ["fx"],
        "prophecy_track": "financial",
    }
    rows, meta = build_inject_rows(
        [q],
        ctx,
        mode="hybrid",
        billing="auto",
        flash_model="gemini-2.5-flash",
        timeout_sec=30,
        azure_deployment=None,
    )
    assert meta["azure_applied_count"] == 1
    assert rows[0]["forecasts"][0]["source_detail"] == "mkm_4ai_coordinator_v1:azure_refine"


def test_fuse_4ai_deterministic_bounds() -> None:
    from scripts.mkm_max_prophecy_4ai_forecast_lib_v1 import (
        SignalContext,
        fuse_4ai_probability,
        load_signal_context,
    )

    ctx = load_signal_context(_ROOT)
    q = {
        "question_id": "max.fx.usdkrw_close_ge_1400_20260731",
        "domain_tags": ["fx", "korea"],
        "prophecy_track": "financial",
    }
    out = fuse_4ai_probability(q, ctx)
    p = out["probability_0_1"]
    assert 0.05 <= p <= 0.95
    assert "legs" in out
    assert out["coordinator_mode"] == "absolute_balance_v1"


def test_apply_forecasts_jsonl_roundtrip() -> None:
    gen = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/generate_general_prophecy_v1.py"),
            "--output",
            "docs/final/artifacts/general_prophecy_latest.json",
            "--stub-forecasts",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert gen.returncode == 0, gen.stderr

    inj = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/inject_mkm_4ai_forecasts_max_evolution_v1.py"),
            "--mode",
            "deterministic",
            "--question-id-prefix",
            "max.",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert inj.returncode == 0, inj.stdout + inj.stderr

    report = _ROOT / "reports/mkm_max_prophecy_4ai_forecast_inject_v1_latest.json"
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["n_rows"] >= 20
    assert doc["send_gate"] == "HOLD"

    reg = json.loads((_ROOT / "docs/final/artifacts/general_prophecy_latest.json").read_text(encoding="utf-8"))
    sample = next(q for q in reg["questions"] if q["question_id"].startswith("max."))
    details = [f.get("source_detail", "") for f in sample.get("forecasts") or []]
    assert any(d.startswith("mkm_4ai_coordinator_v1") for d in details)


def test_apply_general_prophecy_forecasts_jsonl_dry_run() -> None:
    jsonl = _ROOT / "docs/final/artifacts/mkm_max_prophecy_4ai_forecasts_v1_latest.jsonl"
    if not jsonl.is_file():
        subprocess.run(
            [
                sys.executable,
                str(_ROOT / "scripts/inject_mkm_4ai_forecasts_max_evolution_v1.py"),
                "--skip-apply",
            ],
            cwd=str(_ROOT),
            check=True,
            timeout=60,
        )
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/apply_general_prophecy_forecasts_jsonl_v1.py"),
            "--jsonl",
            str(jsonl),
            "--dry-run",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert '"applied"' in r.stdout
