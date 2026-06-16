# -*- coding: utf-8 -*-
"""[HYPO] rib55 deterministic overlay renderer smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def temp_manifest(tmp_path: Path) -> tuple[Path, Path]:
    from PIL import Image

    base = tmp_path / "base.png"
    Image.new("RGB", (120, 80), color=(240, 240, 240)).save(base)

    manifest = {
        "schema": "rib55_angle_overlay_manifest_v1",
        "version": "v1",
        "entries": [
            {
                "entry_id": "test_entry",
                "base_image": {"local_path": "base.png"},
                "overlays": [
                    {
                        "layer_id": "t1",
                        "type": "angle_arc",
                        "angle_deg": 55,
                        "points_norm": [[0.4, 0.5], [0.7, 0.4], [0.6, 0.7]],
                        "stroke": "#E11D48",
                        "label_text": "55° (test)",
                    }
                ],
            }
        ],
        "verification": {},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, base


def test_render_from_manifest_offline(temp_manifest: tuple[Path, Path], tmp_path: Path) -> None:
    from scripts.rib55_angle_overlay_v1_lib import render_from_manifest

    manifest_path, _ = temp_manifest
    out = tmp_path / "out.png"
    report = render_from_manifest(
        manifest_path,
        entry_id="test_entry",
        out_path=out,
        fetch_base=False,
        update_manifest=True,
        workspace_root=manifest_path.parent,
    )
    assert out.is_file()
    assert out.stat().st_size > 0
    assert report["output_sha256"]
    assert report["width"] == 120
    assert report["height"] == 80

    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["verification"]["render_script"] == "scripts/render_rib55_angle_overlay_v1.py"


def test_load_default_manifest_schema() -> None:
    from scripts.rib55_angle_overlay_v1_lib import load_manifest

    path = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
    data = load_manifest(path)
    assert data["schema"] == "rib55_angle_overlay_manifest_v1"
    assert data["entries"]
    entry = data["entries"][0]
    inf = entry.get("infographic_field_v1") or {}
    assert inf.get("headline_ko")
    assert "55" not in str(inf.get("headline_ko", ""))
    assert entry["overlays"][0].get("angle_deg") is None
    assert entry["overlays"][0].get("show_degree_label") is False
    pts = (entry.get("anatomical_reference_points_v1") or {}).get("points") or []
    assert len(pts) == 3
    ids = {p.get("infographic_id") for p in pts}
    assert ids == {"a", "b", "c"}
