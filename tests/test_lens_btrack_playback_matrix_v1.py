# -*- coding: utf-8 -*-
from scripts.lens_btrack_playback_matrix_v1 import (
    audio_filename,
    audio_playback_id,
    build_audio_lut,
    build_video_lut,
    matrix_pair_count,
    media_hub_query,
    sasang_from_macro_scenario,
    showroom_mode_from_final_action,
    video_playback_id,
)


def test_matrix_has_twelve_pairs() -> None:
    assert matrix_pair_count() == 12
    audio = build_audio_lut(version="2026-06-07")
    video = build_video_lut(version="2026-06-07")
    assert len(audio["entries"]) == 12
    assert len(video["entries"]) == 12


def test_playback_ids_and_mirrors() -> None:
    pid = audio_playback_id("soyang", "idle")
    vid = video_playback_id("soyang", "idle")
    assert pid == "LM_HP050_SOYANG_IDLE_V1"
    assert vid == "LV_HP050_SOYANG_IDLE_V1"
    assert audio_filename("taeyang", "attack") == "hp050_taeyang_attack_v1.wav"
    video_lut = build_video_lut(version="2026-06-07")
    assert video_lut["entries"][vid]["audio_playback_id_mirror"] == pid


def test_all_sasang_modes_present() -> None:
    audio = build_audio_lut(version="2026-06-07")
    seen = {
        (v["sasang_primary"], v["showroom_display_mode"])
        for v in audio["entries"].values()
    }
    assert len(seen) == 12


def test_showroom_mode_from_final_action() -> None:
    assert showroom_mode_from_final_action("WATCH") == "idle"
    assert showroom_mode_from_final_action("REDUCE") == "defend"
    assert showroom_mode_from_final_action("ATTACK") == "attack"


def test_media_hub_query_contains_playback_id() -> None:
    q = media_hub_query(sasang="soyang", mode="defend")
    assert q["playback_id"] == "LM_HP050_SOYANG_DEFEND_V1"
    assert "sasang=soyang" in q["media_hub_query"]
    assert "mode=defend" in q["media_hub_query"]


def test_sasang_from_macro_scenario_reads_dominant() -> None:
    doc = {
        "lens_triad_stub": {
            "sasang": {"dominant_constitution": "taeyang"},
        }
    }
    sasang, source = sasang_from_macro_scenario(doc)
    assert sasang == "taeyang"
    assert "dominant_constitution" in source
