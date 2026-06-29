"""Wall divergence exception cards v1 smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILDER = REPO / "scripts/build_universal_root_wall_divergence_exception_cards_v1.py"
OUT = REPO / "docs/final/artifacts/UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json"


def test_build_exception_cards_smoke():
    r = subprocess.run([sys.executable, str(BUILDER)], cwd=str(REPO), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "universal_root_wall_divergence_exception_cards_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["summary"]["exception_count"] == 2
    primes = {x["prime_en"] for x in doc["exceptions"]}
    assert primes == {"heal", "learn"}
