from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_compression_shadow_auditor_v1.py"


def test_shadow_auditor_dry_run_smoke() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--stdout-only",
            "--loss-worst-top-n",
            "2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode in (0, 1, 2), cp.stderr + cp.stdout
    doc = json.loads(cp.stdout)
    assert doc["schema"] == "compression_shadow_auditor_v1"
    assert "pytest" in doc
    assert doc["dry_run"] is True
    assert doc["queue"]["appended_count"] == 0


def test_shadow_auditor_writes_latest_when_artifacts_present(tmp_path: Path) -> None:
    out = tmp_path / "auditor.json"
    queue = tmp_path / "queue.jsonl"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--out-json",
            str(out),
            "--queue-jsonl",
            str(queue),
            "--skip-pytest",
            "--loss-worst-top-n",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode in (0, 1, 2), cp.stderr + cp.stdout
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_shadow_auditor_v1"
    assert not queue.exists() or queue.read_text(encoding="utf-8").strip() == ""
