"""O-P30 envelope assembler smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "assemble_three_lens_sphere_envelope_v1.py"
OUT = ROOT / "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"


def test_assemble_three_lens_sphere_envelope_v1_runs():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--validate-schema"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "three_lens_sphere_envelope_v1"
    assert doc["hypothesis_tier"] == "B"
    assert doc["final_action"] in ("HOLD", "WATCH", "REDUCE")
    for key in ("logos", "sasang", "myeongni"):
        assert key in doc["lenses"]
        assert doc["lenses"][key]["available"] is True
    assert doc["lenses"]["logos"]["non_gating"] is True
    assert "jemaai.cloud" in doc["hub_links"]["jemaai_logos_v6_product"]
    assert "mkmlife.com" in doc["hub_links"]["mkmlife_oracle_sphere"]
    resolved = doc.get("rag_layers_resolved") or {}
    assert "lexical" in resolved
    assert all(e.get("present") for e in resolved["lexical"])
