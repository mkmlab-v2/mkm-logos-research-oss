import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_d7_stability_checklist_v1.py"


def test_build_logos_pure_real_d7_stability_checklist_smoke(tmp_path: Path) -> None:
    progress_json = tmp_path / "progress.json"
    go_nogo_json = tmp_path / "go.json"
    weekly_json = tmp_path / "weekly.json"
    monitor_json = tmp_path / "monitor.json"
    out_json = tmp_path / "out.json"

    progress_json.write_text(
        json.dumps({"checkpoint": {"current_unique_days": 30, "target_unique_days": 30}}),
        encoding="utf-8",
    )
    go_nogo_json.write_text(json.dumps({"decision": "GO"}), encoding="utf-8")
    weekly_json.write_text(json.dumps({"is_alert": False}), encoding="utf-8")
    monitor_json.write_text(
        json.dumps({"status": "PASS_LOW_BACKFILL_DEPENDENCE", "metrics": {"delta_mixed_minus_pure": 0.1}}),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--progress-json",
            str(progress_json),
            "--go-nogo-json",
            str(go_nogo_json),
            "--weekly-alert-json",
            str(weekly_json),
            "--backfill-monitor-json",
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
    assert doc.get("schema") == "logos_pure_real_d7_stability_checklist_v1"
    assert (doc.get("summary") or {}).get("overall_status") == "PASS_STABLE_D7_READY"

