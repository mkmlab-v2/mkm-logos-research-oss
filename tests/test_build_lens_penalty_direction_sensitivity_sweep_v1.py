from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def test_build_lens_penalty_direction_sensitivity_sweep_v1(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_direction_sensitivity_sweep_v1.py"

    now = datetime.now(timezone.utc)
    ts = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = tmp_path / "events.jsonl"
    out = tmp_path / "sweep.json"

    rows = [
        {"timestamp_utc": ts, "lens_id": "myeongni", "prediction_label": "UP", "actual_label": "DOWN"},
        {"timestamp_utc": ts, "lens_id": "myeongni", "prediction_label": "UP", "actual_label": "DOWN"},
        {"timestamp_utc": ts, "lens_id": "myeongni", "prediction_label": "UP", "actual_label": "DOWN"},
        {"timestamp_utc": ts, "lens_id": "myeongni", "prediction_label": "UP", "actual_label": "DOWN"},
        {"timestamp_utc": ts, "lens_id": "myeongni", "prediction_label": "UP", "actual_label": "DOWN"},
        {"timestamp_utc": ts, "lens_id": "myeongni", "prediction_label": "UP", "actual_label": "DOWN"},
    ]
    events.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--events-jsonl",
            str(events),
            "--out",
            str(out),
            "--window-days",
            "7",
            "--min-events",
            "6",
            "--min-improvement",
            "0.15",
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "lens_penalty_direction_sensitivity_sweep_v1"
    assert payload["summary"]["flip_candidates"] == 1
    lens = payload["per_lens"][0]
    assert lens["lens_id"] == "myeongni"
    assert lens["recommend_flip_shadow_candidate"] is True
