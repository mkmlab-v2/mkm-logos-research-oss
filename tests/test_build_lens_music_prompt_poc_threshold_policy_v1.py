from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_lens_music_prompt_poc_threshold_policy_v1(tmp_path):
    metric_json = tmp_path / "metric.json"
    metric_json.write_text(
        json.dumps(
            {
                "schema": "lens_music_prompt_poc_metric_v1",
                "samples_count": 36,
                "kpi": {"style_delta_rate": 0.6, "overlay_style_match_rate": 0.9},
                "targets": {"min_samples": 30, "style_delta_rate_min": 0.3, "overlay_style_match_rate_min": 0.67},
                "result": {"passed": True, "state": "GO"},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "policy.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_prompt_poc_threshold_policy_v1.py"),
            "--poc-json",
            str(metric_json),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_prompt_poc_threshold_policy_v1"
    assert doc["state"] == "GO"
    assert doc["checks"]["samples_pass"] is True
    assert doc["checks"]["style_delta_pass"] is True
    assert doc["checks"]["style_match_pass"] is True
