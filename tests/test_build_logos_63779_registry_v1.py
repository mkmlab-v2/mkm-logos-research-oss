from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_63779_registry_v1.py"


def test_build_63779_registry_smoke(tmp_path: Path) -> None:
    out = tmp_path / "logos_63779_registry.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_63779_registry_v1"
    deep = doc["deep_logos_tension_gematria"]
    assert deep["pattern_id"] == "63779_like_v1"
    assert 0.0 <= float(deep["similarity_0_1"]) <= 1.0
    assert deep["price_mapping_forbidden"] is True
    arch = doc["archetypal_chaos_order_phase"]
    assert 0.0 <= float(arch["chaos_score"]) <= 1.0
    assert 0.0 <= float(arch["order_score"]) <= 1.0
