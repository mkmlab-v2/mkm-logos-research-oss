# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_POLICY = _ROOT / "data" / "market_sasang" / "market_sasang_lens_policy_v1.json"


def _load_engine():
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    path = _ROOT / "scripts" / "market_sasang_lens_engine_v1.py"
    spec = importlib.util.spec_from_file_location("market_sasang_lens_engine_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_softmax_sums_one_and_payload_schema_keys():
    mod = _load_engine()
    policy = mod.load_policy(_POLICY)
    upstream = {
        "schema": "sasang_independent_lens_v0",
        "scores": {"direction_score": 0.1, "confidence": 0.7},
        "sasang_stream_outputs": {
            "machine_readables": {"heat_proxy": 0.6, "cold_proxy": 0.4, "volatility_rarefaction_proxy": 0.5}
        },
    }
    out = mod.build_market_sasang_lens_payload(
        sasang_lens_doc=upstream,
        policy=policy,
        policy_path=str(_POLICY),
        source_input_path="test://upstream",
    )
    assert out["schema"] == "market_sasang_lens_v1"
    sv = out["state_vector_sasang_softmax"]
    s = sum(sv[k] for k in ("taeyang", "soyang", "taeeum", "soeum"))
    assert s == pytest.approx(1.0, abs=1e-6)
    assert "veto" in out and "uncertainty" in out and "fusion_bridge" in out
    assert out["clinical_bridge_forbidden"] is True
    gate = out.get("human_commander_gate_v1") or {}
    assert gate.get("final_authority") == "human_commander"
    assert gate.get("track") == "B"
    assert "[TRACK B / HYPO]" in str(gate.get("banner_ko", ""))


def test_runner_writes_valid_json(tmp_path: Path) -> None:
    upstream = tmp_path / "up.json"
    upstream.write_text(
        json.dumps(
            {
                "schema": "sasang_independent_lens_v0",
                "scores": {"direction_score": 0.0, "confidence": 0.55},
                "sasang_stream_outputs": {
                    "machine_readables": {
                        "heat_proxy": 0.5,
                        "cold_proxy": 0.5,
                        "volatility_rarefaction_proxy": 0.5,
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    pol = tmp_path / "pol.json"
    pol.write_text(_POLICY.read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "out.json"
    import subprocess

    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "run_market_sasang_lens_v1.py"),
            "--policy",
            str(pol),
            "--upstream",
            str(upstream),
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "market_sasang_lens_v1"
    assert doc.get("ts_utc")
