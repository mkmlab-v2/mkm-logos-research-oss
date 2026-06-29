# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_WIDE = _ROOT / "scripts" / "build_rq025_flow_fred_wide_join_hypo_v1.py"
_NF5 = _ROOT / "scripts" / "build_rq024_nf5_wf_v2_vs_v1_recheck_v1.py"
_SHADOW = _ROOT / "scripts" / "build_rq025_gbdt_shadow_hypo_v1.py"


@pytest.mark.parametrize("script,needs", [(_WIDE, []), (_NF5, []), (_SHADOW, [_WIDE])])
def test_rq025_chain_scripts_exit_zero(tmp_path: Path, script: Path, needs: list[Path]) -> None:
    for dep in needs:
        if not dep.is_file():
            pytest.skip(f"missing {dep.name}")
    out = tmp_path / f"{script.stem}.json"
    cmd = [sys.executable, str(script), "--output", str(out)]
    if script == _NF5:
        cmd = [sys.executable, str(script), "--output", str(out)]
    if script == _SHADOW:
        wide_default = _ROOT / "reports" / "rq025_flow_fred_wide_join_hypo_v1_latest.json"
        causal_default = _ROOT / "reports" / "rq025_causal_feature_filter_poc_v1_latest.json"
        if not wide_default.is_file() or not causal_default.is_file():
            pytest.skip("prerequisite artifacts missing")
        cmd = [
            sys.executable,
            str(script),
            "--wide-join-json",
            str(wide_default),
            "--causal-json",
            str(causal_default),
            "--output",
            str(out),
        ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("research_only") is True
    assert doc.get("track_wall", {}).get("live_trading") is False
