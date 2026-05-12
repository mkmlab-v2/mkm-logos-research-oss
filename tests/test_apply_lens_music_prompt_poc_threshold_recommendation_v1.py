from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apply_lens_music_prompt_poc_threshold_recommendation_v1(tmp_path):
    sweep_json = tmp_path / "sweep.json"
    sweep_json.write_text(
        json.dumps(
            {
                "schema": "lens_music_prompt_poc_threshold_sweep_v1",
                "summary": {"decision": "GO_RECOMMENDED"},
                "recommended_policy": {
                    "min_samples": 36,
                    "style_delta_rate_min": 0.5,
                    "overlay_style_match_rate_min": 0.85,
                },
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "recommended.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/apply_lens_music_prompt_poc_threshold_recommendation_v1.py"),
            "--sweep-json",
            str(sweep_json),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_prompt_poc_threshold_recommended_v1"
    assert doc["decision"] == "GO_RECOMMENDED"
    assert doc["policy_targets"]["min_samples"] == 36
