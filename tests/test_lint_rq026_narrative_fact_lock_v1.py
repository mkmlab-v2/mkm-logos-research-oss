"""RQ-026 narrative fact-lock lint."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINT = ROOT / "scripts/lint_rq026_narrative_fact_lock_v1.py"


def test_narrative_lint_passes_experiments_namespace(tmp_path: Path) -> None:
    out = tmp_path / "lint.json"
    proc = subprocess.run(
        [sys.executable, str(LINT), "--out", str(out), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("narrative_lint_ok") is True
    assert doc.get("forbidden_phrase_hits") == []
