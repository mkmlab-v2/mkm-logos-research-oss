from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dispatch_lens_music_prompt_poc_threshold_drift_webhook_v1_best_effort(tmp_path):
    drift_json = tmp_path / "drift.json"
    drift_json.write_text(
        json.dumps(
            {
                "schema": "lens_music_prompt_poc_threshold_recommendation_drift_v1",
                "state": "WATCH",
                "reason": "drift_exceeds_bounds",
                "deltas": {"min_samples_delta": 20},
                "checks": {"samples_delta_within_bound": False},
                "bounds": {"samples_delta_max": 12},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "dispatch.json"

    env = dict(os.environ)
    env.pop("LENS_MUSIC_PROMPT_POC_THRESHOLD_DRIFT_WEBHOOK_URL", None)
    env.pop("ENABLE_WEBHOOK_STRICT_MODE", None)
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/dispatch_lens_music_prompt_poc_threshold_drift_webhook_v1.py"),
            "--drift-json",
            str(drift_json),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["decision"]["drift_state"] == "WATCH"
    assert doc["dispatch"]["status"] == "skipped"
    assert doc["dispatch"]["reason"] == "webhook_not_configured"


def test_dispatch_lens_music_prompt_poc_threshold_drift_webhook_v1_strict_missing_webhook_fails(tmp_path):
    drift_json = tmp_path / "drift.json"
    drift_json.write_text(
        json.dumps({"schema": "lens_music_prompt_poc_threshold_recommendation_drift_v1", "state": "WATCH"}),
        encoding="utf-8",
    )
    out = tmp_path / "dispatch.json"

    env = dict(os.environ)
    env.pop("LENS_MUSIC_PROMPT_POC_THRESHOLD_DRIFT_WEBHOOK_URL", None)
    env["ENABLE_WEBHOOK_STRICT_MODE"] = "true"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/dispatch_lens_music_prompt_poc_threshold_drift_webhook_v1.py"),
            "--drift-json",
            str(drift_json),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["dispatch"]["status"] == "failed"
    assert doc["dispatch"]["reason"] == "webhook_required_but_missing"
