# Keywords: compression enterprise readiness, lg deck

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_lg_compression_deck() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_lg_hs_compression_discipline_deck_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = ROOT / "docs/final/artifacts/lg_hs_compression_discipline_deck_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "lg_hs_compression_discipline_deck_v1"
    assert len(doc.get("slides") or []) >= 5


def test_readiness_check_runs() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_compression_enterprise_summary_readiness_v1.py"),
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    payload = json.loads(r.stdout.strip().splitlines()[-1])
    assert "ready_internal" in payload
