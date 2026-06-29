"""Tests for apply_mkmlife_pixel_language_local_sprite_paths_v1.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts/apply_mkmlife_pixel_language_local_sprite_paths_v1.py"


def test_rewrite_local_and_cdn_modes(tmp_path: Path) -> None:
    pixel = tmp_path / "data" / "MKM_PIXEL_LANGUAGE_V1.json"
    pixel.parent.mkdir(parents=True)
    pixel.write_text(
        json.dumps(
            {
                "category_sprite_registry": {
                    "world": {
                        "sprite_url": (
                            "https://assets.jemaai.cloud/pixel_battalion/refined/a.png"
                        )
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    report = tmp_path / "reports" / "local_paths.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(APPLY),
            "--pixel-json",
            str(pixel),
            "--report-json",
            str(report),
            "--mode",
            "local",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(pixel.read_text(encoding="utf-8"))
    assert doc["category_sprite_registry"]["world"]["sprite_url"] == "/pixel_battalion/refined/a.png"
    assert doc["sprite_deploy_mode"]["mode"] == "local"

    cp2 = subprocess.run(
        [
            sys.executable,
            str(APPLY),
            "--pixel-json",
            str(pixel),
            "--report-json",
            str(report),
            "--mode",
            "cdn",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp2.returncode == 0, cp2.stderr
    doc2 = json.loads(pixel.read_text(encoding="utf-8"))
    assert doc2["sprite_deploy_mode"]["mode"] == "cdn"
    assert "assets.jemaai.cloud" in doc2["category_sprite_registry"]["world"]["sprite_url"]
