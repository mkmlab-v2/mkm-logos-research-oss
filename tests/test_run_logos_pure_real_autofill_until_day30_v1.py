import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_pure_real_autofill_until_day30_v1.py"


def test_run_logos_pure_real_autofill_until_day30_dry_run(tmp_path: Path) -> None:
    out_json = tmp_path / "autofill.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target-unique-days",
            "30",
            "--max-iterations",
            "2",
            "--output-json",
            str(out_json),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode in (0, 2), cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_autofill_until_day30_v1"
    assert isinstance(doc.get("iterations"), list)

