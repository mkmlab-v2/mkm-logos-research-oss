import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_evidence_snapshot_v1.py"


def test_build_logos_pure_real_evidence_snapshot_smoke(tmp_path: Path) -> None:
    art = ROOT / "docs" / "final" / "artifacts"
    for name in [
        "logos_pure_real_daily_go_nogo_latest.json",
        "logos_backfill_dependence_monitor_latest.json",
        "logos_pure_real_execution_gate_weekly_alert_latest.json",
        "logos_pure_real_d7_stability_checklist_latest.json",
        "logos_backfill_delta_sweep_latest.json",
        "logos_temporal_holdout_compare_backfill_latest.json",
        "logos_pure_real_progress_report_latest.json",
    ]:
        p = art / name
        if not p.exists():
            p.write_text("{}", encoding="utf-8")

    out_json = tmp_path / "snapshot_latest.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-json",
            str(out_json),
            "--snapshot-label",
            "test",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_evidence_snapshot_v1"
    assert int(doc.get("copied_count", 0)) >= 1

