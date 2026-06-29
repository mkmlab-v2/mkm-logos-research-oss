from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts/seed_sasang_curated_joint_dummy_fixture_v1.py"


def test_seed_only_no_apply() -> None:
    suffix = "seedonly01"
    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "--suffix", suffix],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    report = json.loads((_ROOT / "reports/sasang_curated_joint_dummy_seed_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert report.get("suffix") == suffix
    assert report.get("apply_promote_requested") is False
