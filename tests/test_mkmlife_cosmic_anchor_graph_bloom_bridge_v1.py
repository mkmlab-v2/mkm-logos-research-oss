"""mkmlife graph bridge → OrbGraphBloom slice wire (ADV-3 UI)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE = ROOT / "projects/mkm/mkm-life"
SLICE_PUBLIC = MKMLIFE / "public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
BRIDGE_LIB = MKMLIFE / "lib/magic-orb-cosmic-anchor-graph-bridge-v1.ts"
ORB = MKMLIFE / "components/magic-orb/MagicOrbExperience.tsx"
BUILD = ROOT / "scripts/build_logos_cosmic_anchor_graph_bloom_slice_v1.py"


def test_build_graph_bloom_slice_exit0() -> None:
    proc = subprocess.run([sys.executable, str(BUILD)], cwd=ROOT, check=False)
    assert proc.returncode == 0, "build_logos_cosmic_anchor_graph_bloom_slice_v1.py failed"


def test_graph_bloom_slice_public_contract() -> None:
    assert SLICE_PUBLIC.is_file(), "run build_logos_cosmic_anchor_graph_bloom_slice_v1.py first"
    doc = json.loads(SLICE_PUBLIC.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_cosmic_anchor_graph_bloom_slice_v1"
    assert doc["hypothesis_class"] == "HYPO"
    assert doc["research_only"] is True
    assert len(doc.get("narrative_path_samples") or []) >= 8
    assert doc.get("preset_narrative_map", {}).get("job_suffering_reason") == "isa53_wound_to_jhn_light"


def test_mkmlife_orb_wires_cosmic_anchor_graph_bridge() -> None:
    lib = BRIDGE_LIB.read_text(encoding="utf-8")
    assert "enrichGraphBloomWithCosmicAnchorBridge" in lib
    assert "COSMIC_ANCHOR_GRAPH_BLOOM_SLICE_URL" in lib
    assert "loadCosmicAnchorGraphBloomSlice" in lib
    orb = ORB.read_text(encoding="utf-8")
    assert "enrichGraphBloomWithCosmicAnchorBridge" in orb
    assert "magic-orb-cosmic-anchor-graph-bridge-v1" in orb
    assert "loadCosmicAnchorGraphBloomSlice" in orb
