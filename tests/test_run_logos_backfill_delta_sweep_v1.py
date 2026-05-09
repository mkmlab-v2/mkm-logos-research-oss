import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_backfill_delta_sweep_v1.py"


def test_run_logos_backfill_delta_sweep_smoke(tmp_path: Path) -> None:
    out_json = tmp_path / "sweep.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-json",
            str(out_json),
            "--bins-candidates",
            "4",
            "--min-non-synth-candidates",
            "4",
            "--balanced-max-per-day-candidates",
            "2",
            "--max-allowed-delta",
            "0.15",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_backfill_delta_sweep_v1"
    assert int(doc.get("run_count", 0)) == 1
    assert "best" in doc

