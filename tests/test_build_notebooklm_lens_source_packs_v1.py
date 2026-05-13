"""Smoke: lens pack builder runs and writes index.json."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_lens_packs_script_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, str(root / "scripts" / "build_notebooklm_lens_source_packs_v1.py")],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    idx = root / "reports" / "notebooklm_lens_packs_v1" / "index.json"
    assert idx.is_file()
    doc = json.loads(idx.read_text(encoding="utf-8"))
    assert doc.get("schema") == "notebooklm_lens_packs_v1"
    assert "LENS_MYEONGNI" in (doc.get("packs") or {})
