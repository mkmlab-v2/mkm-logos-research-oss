"""Smoke tests for jemaai showroom public URL SSOT builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_jemaai_showroom_public_urls_v1.py"


def test_build_urls_ssot(tmp_path: Path) -> None:
    out = tmp_path / "urls.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "jemaai_showroom_public_urls_v1"
    assert doc["commercial_workspace"]["product_primary_url"] == "https://logos.jema-ai.com"
    spine = doc["logos_demo_spine"]["order"]
    assert "meaning_topology_qa_v2" in spine
    assert "logos_job_reading_pack" in spine
    assert "logos_job_cosmic_code" in spine
    assert doc["pages"]["logos_job_cosmic_code"]["path"].endswith(
        "public_showroom_logos_job_cosmic_code_v1.html"
    )
    assert doc["pages"]["logos_job_reading_pack"]["data_json"].endswith(
        "showroom_logos_job_reading_pack_slice_v1.json"
    )
    assert doc["deprecated_pages"]["logos_oracle_v3"]["redirect_to"] == "logos_oracle_v6"
