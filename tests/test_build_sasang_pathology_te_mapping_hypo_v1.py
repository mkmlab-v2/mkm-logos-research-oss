"""sasang_pathology_te_mapping_hypo_v1 — sandbox contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_sasang_pathology_te_mapping_hypo_v1.py"


def test_pathology_te_mapping_hypo_zero_weight(tmp_path: Path) -> None:
    interpretive = tmp_path / "interpretive.json"
    interpretive.write_text(
        json.dumps(
            {
                "schema": "sasang_interpretive_insight_bundle_v1",
                "decision_authority": "human_only",
                "sections": [
                    {
                        "axis_id": "byeongjeung_yakri",
                        "title_ko": "병증",
                        "availability": "partial",
                        "summary_ko": "x",
                    }
                ],
                "synthesis_v1": {"forbidden_synthesis_ko": "no merge"},
            }
        ),
        encoding="utf-8",
    )
    te = tmp_path / "te.json"
    te.write_text(json.dumps({"transfer_entropy": 2.5}), encoding="utf-8")
    out = tmp_path / "out.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--interpretive",
            str(interpretive),
            "--te-json",
            str(te),
            "--bundle",
            str(tmp_path / "missing_bundle.json"),
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "sasang_pathology_te_mapping_hypo_v1"
    assert doc["hypothesis_tier"] == "B"
    assert doc["auto_weight_adjustment_forbidden"] is True
    assert all(r.get("weight_hint") == 0.0 for r in doc["mapping_rows"])
    assert doc["mapping_grid_v1"]["all_weight_hint_zero"] is True
    assert doc["inputs"]["te_band"] == "elevated"
    assert doc["mapping_rows"][0].get("active") is True
