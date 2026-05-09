import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "append_logos_pure_real_execution_gate_trend_v1.py"


def test_append_logos_pure_real_execution_gate_trend_smoke(tmp_path: Path) -> None:
    gate_json = tmp_path / "gate.json"
    log_jsonl = tmp_path / "trend.jsonl"
    gate_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_execution_gate_status_v1",
                "inputs": {
                    "execution_status": "OFF_TRACK_NEED_CATCHUP",
                    "backfill_dependence_status": "FAIL_HIGH_BACKFILL_DEPENDENCE",
                    "delta_mixed_minus_pure": 0.82,
                },
                "blockers": ["OFF_TRACK_DAILY_EXECUTION", "HIGH_BACKFILL_DEPENDENCE"],
                "gate_status": "FAIL_ACTION_REQUIRED",
            }
        ),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--gate-json", str(gate_json), "--log-jsonl", str(log_jsonl)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    lines = [x for x in log_jsonl.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec.get("gate_status") == "FAIL_ACTION_REQUIRED"

