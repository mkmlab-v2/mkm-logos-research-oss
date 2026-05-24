"""MKM Life Anchor OS kernel + 4 skins builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_mkm_life_anchor_os_kernel_skins_v1 as anchor  # noqa: E402


def test_build_kernel_skins_doc_structure() -> None:
    doc = anchor.build_doc(exist_ok=False)
    assert doc["schema"] == "mkm_life_anchor_os_kernel_skins_v1"
    assert doc["hypothesis_tier"] == "B"
    assert len(doc["kernel"]["modules"]) >= 5
    assert len(doc["skins"]) == 4
    mode_ids = [m["mode_id"] for m in doc["forbidden_fusion_modes"]]
    assert "twelve_month_three_lens_matrix" in mode_ids
    for mod in doc["kernel"]["modules"]:
        assert mod["rag_graph_runtime"] is False


def test_main_writes_artifact(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "kernel_skins.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_mkm_life_anchor_os_kernel_skins_v1.py",
            "--out-json",
            str(out),
            "--skip-path-exists",
        ],
    )
    assert anchor.main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "mkm_life_anchor_os_kernel_skins_v1"
