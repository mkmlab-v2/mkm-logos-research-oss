from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def test_build_lens_penalty_shadow_fail_reason_report_v1(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_shadow_fail_reason_report_v1.py"

    now = datetime.now(timezone.utc)
    ts_recent = (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_old = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = tmp_path / "events.jsonl"
    out = tmp_path / "fail_reason.json"
    rows = [
        {"timestamp_utc": ts_recent, "lens_id": "myeongni", "prediction_label": "UP", "actual_label": "UNKNOWN", "result": "FAIL"},
        {"timestamp_utc": ts_recent, "lens_id": "sasang", "prediction_label": "UP", "actual_label": "DOWN", "result": "FAIL"},
        {"timestamp_utc": ts_recent, "lens_id": "logos", "prediction_label": "DOWN", "actual_label": "DOWN", "result": "HIT"},
        {"timestamp_utc": ts_old, "lens_id": "myeongni", "prediction_label": "UP", "actual_label": "DOWN", "result": "FAIL"},
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
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "lens_penalty_shadow_fail_reason_report_v1"
    assert payload["summary"]["fail_events"] == 2
    ranked = {x["reason_code"]: x["count"] for x in payload["reason_ranked"]}
    assert ranked["ACTUAL_UNKNOWN"] == 1
    assert ranked["DIRECTION_MISMATCH"] == 1
