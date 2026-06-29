"""mkmlife Wave 3b — batch cosmic anchor local wire (40 motifs, no CF)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE = ROOT / "projects/mkm/mkm-life"
BATCH_MANIFEST = MKMLIFE / "public/data/logos_cosmic_anchor_batch_v1_manifest_latest.json"
BATCH_PUBLIC = MKMLIFE / "public/data/logos_cosmic_anchor_batch_v1"
INDEX = MKMLIFE / "lib/mkmlifeCosmicAnchorBatchIndex.generated.ts"


def test_wave3b_batch_sync_and_wire() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_cosmic_anchor_batch_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    assert BATCH_MANIFEST.is_file()
    assert INDEX.is_file()
    manifest = json.loads(BATCH_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "logos_cosmic_anchor_batch_v1_manifest"
    assert manifest["anchor_count"] >= 30
    assert manifest["lookup_by_preset_id"]["motif_door"] == "cosmic_anchor_door_jhn_10_9"
    assert len(list(BATCH_PUBLIC.glob("*.json"))) == manifest["anchor_count"]

    lib = (MKMLIFE / "lib/mkmlifeCosmicAnchorV1.ts").read_text(encoding="utf-8")
    assert "mkmlifeCosmicAnchorBatchIndex.generated" in lib
    assert "lookupCosmicAnchorByVerseRef" in lib

    page = (MKMLIFE / "app/oracle-sphere/page.tsx").read_text(encoding="utf-8")
    assert "cosmicVerseRef" in page
    assert "cosmicAnchorId" in page

    api = (MKMLIFE / "app/api/v1/design-kernel/cosmic-anchor/route.ts").read_text(
        encoding="utf-8"
    )
    assert "lookupCosmicAnchorByVerseRef" in api

    index = INDEX.read_text(encoding="utf-8")
    assert "BATCH_ANCHOR_BY_ID" in index
    assert "doorDoc" in index

    check = subprocess.run(
        [sys.executable, "scripts/check_mkmlife_design_kernel_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stderr or check.stdout
