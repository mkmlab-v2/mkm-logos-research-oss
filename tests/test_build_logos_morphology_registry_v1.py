from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_morphology_registry_v1.py"


def test_build_morphology_registry_smoke(tmp_path: Path) -> None:
    out = tmp_path / "morph_registry.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_morphology_registry_v1"
    layer = doc["morphology_layer"]
    assert layer["registry_id"] == "morphhb_hebrew_core_v1"
    assert 0.0 <= float(layer["coverage_ratio_0_1"]) <= 1.0
    assert layer["non_gating_only"] is True
    assert layer["price_mapping_forbidden"] is True
    policy = layer["sampling_policy"]
    assert policy["max_scan_lines"] == 400000
    assert policy["target_matched_samples"] == 5000
