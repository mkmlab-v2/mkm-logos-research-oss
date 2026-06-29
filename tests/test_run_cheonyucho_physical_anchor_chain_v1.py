"""Smoke: cheonyucho physical anchor chain (offline)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_physical_anchor_chain_offline_smoke() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_cheonyucho_physical_anchor_chain_v1.py",
            "--skip-network",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/constitution/btrack_pilot/cheonyucho_physical_anchor_chain_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["hanja_canon_status"] == "not_acquired"

    index = json.loads(
        (ROOT / "reports/constitution/btrack_pilot/cheonyucho_physical_proxy_index_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    slugs = [p["slug"] for p in index["proxies"]]
    assert "SASANG_CLINICAL_P344_2026" in slugs
