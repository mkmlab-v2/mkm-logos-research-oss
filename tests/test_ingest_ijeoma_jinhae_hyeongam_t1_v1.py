"""Smoke: Jinhae hyeongam T1 ingest."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_jinhae_hyeongam_t1_ingest_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/ingest_ijeoma_jinhae_hyeongam_t1_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/constitution/btrack_pilot/ijeoma_jinhae_hyeongam_t1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["retired"] == "1889-12"
    assert doc["cheonyucho_primary"] is False
    proxy = ROOT / "docs/research/raw/IJEOMA_JINHAE_HYEONGAM_career_T1_nl_proxy.md"
    assert proxy.is_file()
