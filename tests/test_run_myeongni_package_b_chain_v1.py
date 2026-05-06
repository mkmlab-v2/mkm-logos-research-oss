from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_myeongni_package_b_chain_v1.py"


def _run(mode: str, tmp_path: Path) -> dict:
    adv = tmp_path / f"adv_{mode}.json"
    lens = tmp_path / f"lens_{mode}.json"
    v2_bal = tmp_path / f"v2_bal_{mode}.json"
    v2_atk = tmp_path / f"v2_atk_{mode}.json"
    summary = tmp_path / f"summary_{mode}.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mode",
            mode,
            "--advanced-output",
            str(adv),
            "--lens-output",
            str(lens),
            "--v2-balanced-output",
            str(v2_bal),
            "--v2-attack-output",
            str(v2_atk),
            "--summary-output",
            str(summary),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    return json.loads(summary.read_text(encoding="utf-8"))


def test_chain_mode_both_writes_balanced_and_attack_margins(tmp_path: Path):
    doc = _run("both", tmp_path)
    assert doc["mode"] == "both"
    assert doc["snapshot"]["decision_balanced"] in {"WATCH", "HOLD", "REDUCE"}
    assert doc["snapshot"]["decision_attack"] in {"WATCH", "HOLD", "REDUCE"}
    assert isinstance(doc["margins"]["balanced"], dict)
    assert isinstance(doc["margins"]["attack"], dict)
    assert "direction_minus_reduce_cut" in doc["margins"]["balanced"]
    assert "direction_minus_reduce_cut" in doc["margins"]["attack"]


def test_chain_mode_attack_omits_balanced_outputs(tmp_path: Path):
    doc = _run("attack", tmp_path)
    assert doc["mode"] == "attack"
    assert doc["inputs"]["v2_balanced_output"] is None
    assert doc["snapshot"]["decision_balanced"] is None
    assert doc["margins"]["balanced"] is None
    assert doc["snapshot"]["decision_attack"] in {"WATCH", "HOLD", "REDUCE"}
