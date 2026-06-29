from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_logos_studio_ecs_telemetry_summary_smoke(tmp_path: Path) -> None:
    events = tmp_path / "hub_events.jsonl"
    out = tmp_path / "ecs_summary.json"
    events.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "logos_research_query_success_v1",
                        "ts_utc": "2026-06-25T08:00:00Z",
                        "effective_level": "preset+graphrag+synthesis",
                        "access_gate": "research_only_hold",
                        "ecs_v1": 82,
                        "ecs_band": "high",
                    }
                ),
                json.dumps(
                    {
                        "event": "logos_research_query_success_v1",
                        "ts_utc": "2026-06-25T09:00:00Z",
                        "effective_level": "preset",
                        "access_gate": "research_only_hold",
                        "ecs_v1": 46,
                        "ecs_band": "low",
                    }
                ),
                json.dumps({"event": "other_event_v1", "ts_utc": "2026-06-25T10:00:00Z"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_logos_studio_ecs_telemetry_summary_v1.py"),
            "--events-jsonl",
            str(events),
            "--out-json",
            str(out),
            "--window-days",
            "3650",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_studio_ecs_telemetry_summary_v1"
    assert (doc.get("event_contract") or {}).get("events_in_window") == 2
    assert (doc.get("event_contract") or {}).get("ecs_observed_count") == 2
    assert (doc.get("band_counts") or {}).get("high") == 1
    assert (doc.get("band_counts") or {}).get("low") == 1
