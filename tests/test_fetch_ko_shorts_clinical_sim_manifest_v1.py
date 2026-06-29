"""clinical_sim OSS proxy manifest — offline unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_ko_shorts_web_speech_wav_v1 import build_clinical_sim_manifest_v1  # noqa: E402


def test_build_clinical_sim_manifest_v1_marks_not_patient_data() -> None:
    manifest = build_clinical_sim_manifest_v1(
        [
            {
                "source": "pansori",
                "proxy_tier": "interview",
                "wav_path": "reports/audio/ko_shorts_web_pansori_tedxkr_v1.wav",
                "duration_sec": 21.5,
                "license": "CC-BY-NC-ND-4.0",
                "source_page": "https://example.com/pansori",
            },
            {
                "source": "deeply",
                "proxy_tier": "read",
                "wav_path": "reports/audio/ko_shorts_web_deeply_read_v1.wav",
                "duration_sec": 19.9,
                "license": "CC-BY-NC-ND-4.0",
                "source_page": "https://example.com/deeply",
            },
        ]
    )
    assert manifest["schema"] == "ko_shorts_clinical_sim_manifest_v1"
    assert manifest["not_patient_data"] is True
    assert manifest["clinical_sim"] is True
    assert manifest["send_gate"] == "HOLD"
    assert manifest["member_count"] == 2
    assert {m["proxy_tier"] for m in manifest["members"]} == {"interview", "read"}


def test_build_clinical_sim_manifest_v1_proxy_tiers_sorted() -> None:
    manifest = build_clinical_sim_manifest_v1(
        [{"source": "pansori", "proxy_tier": "interview", "wav_path": "a.wav"}]
    )
    assert manifest["proxy_tiers"] == ["interview"]
