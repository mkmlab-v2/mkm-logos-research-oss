import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_execution_gate_status_v1.py"


def test_build_logos_pure_real_execution_gate_status_smoke(tmp_path: Path) -> None:
    action_pack_json = tmp_path / "action_pack.json"
    monitor_json = tmp_path / "monitor.json"
    out_json = tmp_path / "out.json"

    action_pack_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_action_pack_v1",
                "status": {
                    "execution_status": "OFF_TRACK_NEED_CATCHUP",
                    "priority": "EXECUTE_CATCHUP_TODAY",
                },
            }
        ),
        encoding="utf-8",
    )
    monitor_json.write_text(
        json.dumps(
            {
                "schema": "logos_backfill_dependence_monitor_v1",
                "status": "FAIL_HIGH_BACKFILL_DEPENDENCE",
                "metrics": {"delta_mixed_minus_pure": 0.82},
            }
        ),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--action-pack-json",
            str(action_pack_json),
            "--monitor-json",
            str(monitor_json),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_execution_gate_status_v1"
    assert doc.get("gate_status") == "FAIL_ACTION_REQUIRED"
    blockers = doc.get("blockers") or []
    assert "OFF_TRACK_DAILY_EXECUTION" in blockers
    assert "HIGH_BACKFILL_DEPENDENCE" in blockers

