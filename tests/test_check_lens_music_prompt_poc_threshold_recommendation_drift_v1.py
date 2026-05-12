from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_check_lens_music_prompt_poc_threshold_recommendation_drift_v1(tmp_path):
    recommended = tmp_path / "recommended.json"
    state = tmp_path / "state.json"
    log_jsonl = tmp_path / "drift_log.jsonl"

    recommended.write_text(
        json.dumps(
            {
                "schema": "lens_music_prompt_poc_threshold_recommended_v1",
                "policy_targets": {
                    "min_samples": 36,
                    "style_delta_rate_min": 0.5,
                    "overlay_style_match_rate_min": 0.85,
                },
            }
        ),
        encoding="utf-8",
    )

    # First run should initialize state.
    r1 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_lens_music_prompt_poc_threshold_recommendation_drift_v1.py"),
            "--recommended-json",
            str(recommended),
            "--state-json",
            str(state),
            "--log-jsonl",
            str(log_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r1.returncode == 0, r1.stdout + r1.stderr
    first = json.loads(state.read_text(encoding="utf-8"))
    assert first["state"] == "INIT"

    # Second run with large drift should trigger WATCH.
    recommended.write_text(
        json.dumps(
            {
                "schema": "lens_music_prompt_poc_threshold_recommended_v1",
                "policy_targets": {
                    "min_samples": 80,
                    "style_delta_rate_min": 0.9,
                    "overlay_style_match_rate_min": 0.2,
                },
            }
        ),
        encoding="utf-8",
    )
    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_lens_music_prompt_poc_threshold_recommendation_drift_v1.py"),
            "--recommended-json",
            str(recommended),
            "--state-json",
            str(state),
            "--log-jsonl",
            str(log_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr
    second = json.loads(state.read_text(encoding="utf-8"))
    assert second["state"] == "WATCH"
    assert second["reason"] == "drift_exceeds_bounds"
