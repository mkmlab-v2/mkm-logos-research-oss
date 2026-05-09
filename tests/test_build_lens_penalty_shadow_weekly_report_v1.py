from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def test_build_lens_penalty_shadow_weekly_report_v1(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_shadow_weekly_report_v1.py"

    events = tmp_path / "events.jsonl"
    apply_policy = tmp_path / "apply_policy.json"
    out = tmp_path / "weekly.json"
    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent1 = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent2 = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

    rows = [
        {"timestamp_utc": old, "lens_id": "myeongni", "result": "FAIL"},
        {"timestamp_utc": recent1, "lens_id": "myeongni", "result": "FAIL"},
        {"timestamp_utc": recent2, "lens_id": "sasang", "result": "HIT"},
    ]
    events.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    apply_policy.write_text(
        json.dumps(
            {
                "schema": "lens_penalty_apply_mode_policy_v1",
                "profiles": {
                    "strict": {"min_weekly_events": 21, "max_weekly_fail_rate": 0.45}
                },
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--events-jsonl",
            str(events),
            "--out",
            str(out),
            "--apply-policy-json",
            str(apply_policy),
            "--window-days",
            "7",
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "lens_penalty_shadow_weekly_report_v1"
    assert payload["summary"]["total_events"] == 2
    assert payload["summary"]["strict_gap"] > 0
    by_lens = {x["lens_id"]: x for x in payload["per_lens"]}
    assert by_lens["myeongni"]["fail_count"] == 1
    assert by_lens["sasang"]["hit_count"] == 1
