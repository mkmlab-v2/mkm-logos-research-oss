# -*- coding: utf-8 -*-
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_train_weather_fusion_profile_smoke(tmp_path: Path):
    out = tmp_path / "wf_profile.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "train_myeongni_weather_fusion_profile_v1.py"),
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "myeongni_weather_fusion_profile_v1"
    assert "recommended" in doc
    assert "weight_direct" in doc["recommended"]

