# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_protocol_ablation_smoke(tmp_path: Path) -> None:
    out = tmp_path / "ablation.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_sasang_4agent_protocol_ablation_v1.py"),
            "--out-json",
            str(out),
            "--bootstrap-trials",
            "80",
            "--ticks",
            "400",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "sasang_4agent_protocol_ablation_v1"
    assert doc["n_variants"] == 12
    assert doc["data_policy"]["ohlcv_tuning_forbidden"] is True
    assert doc["track_wall"]["track_a_promotion"] is False
    assert doc["verdict"] in {"null_under_preregistered_gates", "exploratory_pass_candidate"}
    control = [v for v in doc["variants"] if v.get("is_control")]
    assert len(control) == 1
