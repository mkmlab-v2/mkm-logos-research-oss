"""YouTube allowlist SSOT for clinical_sim proxy — offline checks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SSOT = ROOT / "tests/fixtures/ko_shorts_clinical_sim_youtube_allowlist_v1.json"


def test_youtube_allowlist_ssot_has_required_fields() -> None:
    doc = json.loads(SSOT.read_text(encoding="utf-8"))
    assert doc["schema"] == "ko_shorts_clinical_sim_youtube_allowlist_v1"
    assert doc["not_patient_data"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["video_id"] == "8-dSwR5iUyY"
    assert float(doc["clip_duration_sec"]) > 0
    assert "youtube.com" in doc["youtube_url"]
