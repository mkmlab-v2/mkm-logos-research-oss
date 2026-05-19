# @MKM12-METADATA
# Type: Logic
# Purpose: logos_verse_4d regression bundle runner smoke.
# Keywords: logos, track_b, verse_4d, regression, bundle

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BUNDLE = _ROOT / "scripts" / "run_logos_verse_4d_regression_bundle_v1.py"


def test_regression_bundle_script_exists() -> None:
    assert _BUNDLE.is_file()


def test_regression_bundle_dry_run_lists_known_tests() -> None:
    cp = subprocess.run(
        [sys.executable, str(_BUNDLE), "--dry-run", "--json"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    payload = json.loads(cp.stdout.strip())
    assert payload["dry_run"] is True
    files = payload["test_files"]
    assert any("test_logos_verse_4d_v1_schema.py" in f for f in files)
    assert any("test_build_logos_verse_canon_coverage" in f for f in files)
    assert any("test_project_logos_verse" in f for f in files)
