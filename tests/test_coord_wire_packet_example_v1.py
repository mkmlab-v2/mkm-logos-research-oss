"""COORD wire packet example builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_coord_wire_packet_example_v1.py"
OUT = ROOT / "docs/final/artifacts/coord_wire_packet_example_v1_latest.json"


def test_build_coord_wire_packet_example_exit0():
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "coord_wire_packet_example_v1"
    wire = doc["coord_wire_minimal"]
    assert wire["sku_class"] == "coord"
    assert wire["wire_mode"] == "anatomy_overlay_coord_v1"
    assert len(wire["coord_inject"]["points_norm"]) == 3
    assert doc["v2_compress_request_example"]["sku_class"] == "coord"
    tokens = doc["token_proxy_cl100k"]["coord_wire_tokens"]
    assert tokens is not None and tokens < 200
