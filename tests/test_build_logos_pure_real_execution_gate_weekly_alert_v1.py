import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_execution_gate_weekly_alert_v1.py"


def test_build_logos_pure_real_execution_gate_weekly_alert_smoke(tmp_path: Path) -> None:
    log_jsonl = tmp_path / "trend.jsonl"
    out_json = tmp_path / "weekly.json"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    log_jsonl.write_text(
        "\n".join(
            [
                json.dumps({"timestamp_utc": now, "gate_status": "FAIL_ACTION_REQUIRED"}),
                json.dumps({"timestamp_utc": now, "gate_status": "WARN_CONTINUE_DAILY_EXECUTION"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--log-jsonl",
            str(log_jsonl),
            "--output-json",
            str(out_json),
            "--window-days",
            "7",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_execution_gate_weekly_alert_v1"
    assert doc.get("is_alert") is True
    assert int((doc.get("counts") or {}).get("fail_action_required", 0)) == 1

