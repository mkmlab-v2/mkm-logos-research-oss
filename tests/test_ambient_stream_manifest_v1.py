"""Zone A ambient stream manifest builder."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.build_ambient_stream_manifest_v1 as amb


def test_build_ambient_manifest(tmp_path: Path) -> None:
    pl = tmp_path / "playlist.json"
    pl.write_text(
        json.dumps(
            {
                "tracks": [
                    {
                        "track_id": "t1",
                        "path": "a.wav",
                        "license_tag": "CC0_APPROVED_ALLOWLIST",
                        "duration_sec": 60,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    doc = amb.build_manifest(tmp_path, playlist_path=pl)
    assert doc["schema"] == "ambient_stream_manifest_v1"
    assert doc["program_style"] == "ambient_24h_zone_a"
    assert doc["gates"]["spoken_price_allowed"] is False
    assert len(doc["playlist"]) == 1
