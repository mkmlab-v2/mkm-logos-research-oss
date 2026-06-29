from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "reports/logos_graphrag_2026_regime_watch_latest.json"


def test_promotion_verify_chain():
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_regime_watch_luke_promotion_verify_chain_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(TARGET.read_text(encoding="utf-8-sig"))
    assert doc.get("promotion_signoff")
    assert "vr_luke_22_4" in json.dumps(doc.get("paths") or [])
