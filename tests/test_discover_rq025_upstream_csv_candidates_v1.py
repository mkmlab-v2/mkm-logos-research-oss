from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISCOVER = ROOT / "scripts/discover_rq025_upstream_csv_candidates_v1.py"


def test_discover_validate_candidates(tmp_path: Path) -> None:
    out = tmp_path / "discovery.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(DISCOVER),
            "--validate-candidates",
            "--max-depth",
            "0",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    verdict = doc.get("verdict") or {}
    assert verdict.get("schema_validated") is True
    assert isinstance(verdict.get("n_schema_ok"), int)
    candidates = doc.get("candidates") or []
    if candidates:
        assert "schema_ok" in candidates[0]
