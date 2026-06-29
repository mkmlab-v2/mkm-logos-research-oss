# Keywords: pillar_a, health_smoke, continuity

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts/run_mkm_pillar_a_cursor_health_smoke_v1.py"


def test_pillar_a_health_smoke_dry_run():
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "turn_meta_audit" in proc.stdout
    assert "context_diet_strict" in proc.stdout
