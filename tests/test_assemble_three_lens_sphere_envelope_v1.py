"""O-P30 envelope assembler smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "assemble_three_lens_sphere_envelope_v1.py"
OUT = ROOT / "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"
PUBLIC_MKMLIFE = ROOT / "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_public_v1.json"
INTERNAL_MKMLIFE = ROOT / "projects/mkm/mkm-life/data/internal/three_lens_sphere_envelope_v1.json"
LEGACY_PUBLIC_FULL = ROOT / "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_v1.json"


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


def test_assemble_copy_mkmlife_public_logos_only_envelope():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--copy-mkmlife-public"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert PUBLIC_MKMLIFE.is_file()
    assert INTERNAL_MKMLIFE.is_file()
    assert not LEGACY_PUBLIC_FULL.is_file()
    pub = json.loads(PUBLIC_MKMLIFE.read_text(encoding="utf-8"))
    assert pub.get("profile_mode") == "public_logos_only"
    assert set((pub.get("lenses") or {}).keys()) == {"logos"}
    logos = pub["lenses"]["logos"]
    assert "성경" not in logos.get("title_ko", "")
    assert "Logos" not in logos.get("body_ko", "")
    assert pub.get("consumer_facade")
    assert "rag_layers_resolved" not in pub
    assert "inputs_manifest" not in pub
    internal = json.loads(INTERNAL_MKMLIFE.read_text(encoding="utf-8"))
    assert set((internal.get("lenses") or {}).keys()) == {"logos", "sasang", "myeongni"}
