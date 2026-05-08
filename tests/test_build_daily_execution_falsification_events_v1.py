from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_daily_execution_falsification_events_v1_append(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_daily_execution_falsification_events_v1.py"

    input_json = tmp_path / "daily_execution_falsification_input_latest.json"
    events_jsonl = tmp_path / "daily_execution_insight_falsification_log.jsonl"
    out_json = tmp_path / "daily_execution_falsification_events_latest.json"

    _write_json(
        input_json,
        {
            "schema": "daily_execution_falsification_input_v1",
            "date_utc": "2026-05-07",
            "source": "unit_test",
            "entries": [
                {
                    "lens_id": "myeongni",
                    "prediction_label": "UP",
                    "actual_label": "DOWN",
                },
                {
                    "lens_id": "sasang",
                    "prediction_label": "UP",
                    "actual_label": "UP",
                },
            ],
        },
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-json",
            str(input_json),
            "--events-jsonl",
            str(events_jsonl),
            "--out",
            str(out_json),
        ],
        check=True,
        cwd=repo,
    )

    summary = json.loads(out_json.read_text(encoding="utf-8"))
    lines = [json.loads(x) for x in events_jsonl.read_text(encoding="utf-8").splitlines() if x.strip()]

    assert summary["status"] == "APPENDED"
    assert summary["appended_count"] == 2
    assert summary["hit_count"] == 1
    assert summary["fail_count"] == 1
    assert {r["result"] for r in lines} == {"HIT", "FAIL"}
