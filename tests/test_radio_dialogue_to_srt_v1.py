"""SRT export for radio_dialogue_script_v1."""

from __future__ import annotations

import scripts.radio_dialogue_to_srt_v1 as srt_mod


def test_build_srt_has_cues() -> None:
    doc = {
        "segments": [
            {
                "segment_index": 1,
                "segment_name": "open",
                "dialogue": [
                    {
                        "sequence": 1,
                        "persona": "system_announcer",
                        "audio_text": "면책 고지입니다.",
                        "target_duration_sec": 3,
                    }
                ],
            }
        ]
    }
    body = srt_mod.build_srt(doc)
    assert "00:00:00" in body
    assert "면책" in body
