from __future__ import annotations

import json
from pathlib import Path

from scripts.run_btrack_phase3_multilens_aux_eval_v1 import main

ROOT = Path(__file__).resolve().parents[1]


def test_multilens_aux_eval_on_disk_artifacts() -> None:
    joined = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.jsonl"
    panel = ROOT / "reports/btrack_phase3_per_date_lens_panel_v1_latest.jsonl"
    if not joined.is_file() or not panel.is_file():
        return
    out = ROOT / "reports/btrack_phase3_multilens_aux_eval_v1_latest.json"
    rc = main(["--output", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_phase3_multilens_aux_eval_v1"
    assert doc.get("verdict", {}).get("apply_prod") is False
    assert "headline_unchanged" in doc
