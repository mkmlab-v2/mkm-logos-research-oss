"""zone_ko_premium_cs template catalog coverage eval."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl"
COVERAGE_RUNNER = ROOT / "scripts/run_zone_ko_premium_cs_template_catalog_coverage_v1.py"
PIPELINE = ROOT / "scripts/run_zone_ko_premium_cs_template_catalog_pipeline_v1.py"


def test_coverage_manifest_canonical_mask_full_match() -> None:
    proc = subprocess.run(
        [sys.executable, str(COVERAGE_RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/zone_ko_premium_cs_template_catalog_coverage_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema"] == "zone_ko_premium_cs_template_catalog_coverage_v1"
    assert doc["canonical_mask_token"] == "███"
    assert doc["aggregate"]["full_wire_match"] is True
    assert doc["aggregate"]["wire_match_rate"] == 1.0


def test_pipeline_dry_run_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(PIPELINE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
