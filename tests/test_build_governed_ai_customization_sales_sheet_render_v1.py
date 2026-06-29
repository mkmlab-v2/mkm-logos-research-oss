"""Sales sheet JSON -> counsel prep MD render."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "scripts/build_governed_ai_customization_sales_sheet_render_v1.py"
SRC = ROOT / "docs/final/artifacts/governed_ai_customization_sales_sheet_v1_latest.json"


def test_render_sales_sheet_md(tmp_path: Path) -> None:
    out = tmp_path / "sheet.md"
    proc = subprocess.run(
        [sys.executable, str(RENDER), "--in-json", str(SRC), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    text = out.read_text(encoding="utf-8")
    assert "Governed AI Customization" in text
    assert "Forbidden" in text
