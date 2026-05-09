import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_daily_go_nogo_v1.py"


def test_build_logos_pure_real_daily_go_nogo_smoke(tmp_path: Path) -> None:
    gate_json = tmp_path / "gate.json"
    preflight_json = tmp_path / "preflight.json"
    out_json = tmp_path / "out.json"

    gate_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_execution_gate_status_v1",
                "gate_status": "FAIL_ACTION_REQUIRED",
                "blockers": ["OFF_TRACK_DAILY_EXECUTION"],
            }
        ),
        encoding="utf-8",
    )
    preflight_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_intake_preflight_status_v1",
                "status": "FAIL_NEED_MORE_ROWS",
                "shortage_rows_today": 6,
            }
        ),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gate-status-json",
            str(gate_json),
            "--preflight-json",
            str(preflight_json),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_daily_go_nogo_v1"
    assert doc.get("decision") == "NO_GO"
    assert int(doc.get("shortage_rows_today", 0)) == 6
    reasons = doc.get("reasons") or []
    assert any("SHORTAGE_ROWS_TODAY=6" == r for r in reasons)

