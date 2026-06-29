from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_build_themed_vector_jhn1() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_logos_themed_vector_index_v1.py"), "--theme", "john_1_logos"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True
    assert doc["verse_count"] >= 3


def test_query_themed_vector_jhn1() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/query_logos_themed_vector_index_v1.py"), "--theme", "john_1_logos"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    out = _ROOT / "docs/final/artifacts/logos_themed_vector_query_john_1_logos_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert len(doc.get("top_k") or []) >= 1
