"""Contract smoke for bio_sasang n-states strict comparison rehydrate v1."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_bio_sasang_nstates_strict_comparison_rehydrate_v1.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("bio_sasang_rehydrate_v1", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_payload_schema_and_provenance() -> None:
    mod = _load_module()
    p = mod.build_payload()
    assert p["schema"] == "bio_sasang_nstates_strict_comparison_v2"
    assert p["version"] == 2
    reg = p["regeneration"]
    assert reg["mode"] == "rehydrated_from_ssot_documentation"
    assert "CENTRAL_AGENT_MEMORY" in reg["source_document"]
    assert reg["warning"]
    assert p["cohort"]["n_rows"] == 4783
    by = p["results"]["by_n_states"]
    assert by["12"]["spearman"] == pytest.approx(0.5295)
    assert p["results"]["recommended_n_states"] == 12
    assert p["results"]["ranking_by_spearman_desc"][0] == "12"


def test_cli_writes_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "bio_sasang_nstates_strict_comparison_v2.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "bio_sasang_nstates_strict_comparison_v2"
