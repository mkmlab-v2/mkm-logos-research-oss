import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_baseline_drift_check_v1.py"


def test_build_logos_pure_real_baseline_drift_check_smoke(tmp_path: Path) -> None:
    snap_dir = tmp_path / "snap"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_go = snap_dir / "logos_pure_real_daily_go_nogo_latest.json"
    snap_mon = snap_dir / "logos_backfill_dependence_monitor_latest.json"
    snap_d7 = snap_dir / "logos_pure_real_d7_stability_checklist_latest.json"
    snap_go.write_text(json.dumps({"decision": "GO"}), encoding="utf-8")
    snap_mon.write_text(json.dumps({"status": "PASS_LOW_BACKFILL_DEPENDENCE"}), encoding="utf-8")
    snap_d7.write_text(json.dumps({"summary": {"overall_status": "PASS_STABLE_D7_READY"}}), encoding="utf-8")

    idx = tmp_path / "index.json"
    idx.write_text(
        json.dumps(
            {
                "copied": [
                    {"snapshot": str(snap_go)},
                    {"snapshot": str(snap_mon)},
                    {"snapshot": str(snap_d7)},
                ]
            }
        ),
        encoding="utf-8",
    )

    art = ROOT / "docs" / "final" / "artifacts"
    (art / "logos_pure_real_daily_go_nogo_latest.json").write_text(json.dumps({"decision": "GO"}), encoding="utf-8")
    (art / "logos_backfill_dependence_monitor_latest.json").write_text(
        json.dumps({"status": "PASS_LOW_BACKFILL_DEPENDENCE"}), encoding="utf-8"
    )
    (art / "logos_pure_real_d7_stability_checklist_latest.json").write_text(
        json.dumps({"summary": {"overall_status": "PASS_STABLE_D7_READY"}}), encoding="utf-8"
    )

    out_json = tmp_path / "drift.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--snapshot-index-json",
            str(idx),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_baseline_drift_check_v1"
    assert (doc.get("summary") or {}).get("overall_status") == "PASS_ALIGNED_WITH_BASELINE"

