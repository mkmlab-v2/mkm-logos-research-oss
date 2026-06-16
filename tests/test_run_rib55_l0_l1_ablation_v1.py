"""[HYPO] rib55 L0 vs L1 ablation smoke."""
from __future__ import annotations

import json
from pathlib import Path

from scripts import run_rib55_l0_l1_ablation_v1 as ablation_mod

ROOT = Path(__file__).resolve().parents[1]


def test_rib55_l0_l1_ablation_exit_zero(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["run_rib55_l0_l1_ablation_v1.py"])
    assert ablation_mod.main() == 0
    doc = json.loads(ablation_mod.OUT_ART.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["adjudication_required"] is True
    assert doc["ready_for_external_send"] is False
    assert doc["pixels_differ"] is True
    assert doc["l1"]["angle_delta"] != 0

    l0_path = ROOT / doc["l0"]["output"]
    l1_path = ROOT / doc["l1"]["output"]
    assert l0_path.is_file()
    assert l1_path.is_file()
