from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHED = ROOT / "reports/logos_graphrag_2026_regime_watch_luke_patch_v1_latest.json"


def test_luke_patch_adds_router_path():
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/apply_logos_graphrag_regime_watch_luke_gap_patch_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    assert PATCHED.is_file()
    doc = json.loads(PATCHED.read_text(encoding="utf-8-sig"))
    steps = [s for p in doc.get("paths") or [] for s in (p.get("steps") or [])]
    assert "vr_luke_22_4" in steps
    assert "greek::Luke.22.4" in (doc.get("verse_ids") or [])
