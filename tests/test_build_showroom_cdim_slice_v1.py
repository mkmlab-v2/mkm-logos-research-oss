from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_BUILDER = _ROOT / "scripts" / "build_showroom_cdim_slice_v1.py"
_CDIM = _ROOT / "docs" / "final" / "artifacts" / "logos_cross_domain_interface_latest.json"


def test_showroom_cdim_slice_builder(tmp_path: Path) -> None:
    if not _CDIM.is_file():
        pytest.skip("logos_cross_domain_interface_latest.json not on disk")
    out = tmp_path / "slice.json"
    cp = subprocess.run(
        [sys.executable, str(_BUILDER), "--cdim-json", str(_CDIM), "--out", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "showroom_logos_cross_domain_interface_slice_v1"
    assert doc.get("non_gating") is True
    assert doc.get("no_verse_level_ohaeng_ingest") is True
    assert doc.get("state") == "OK"
