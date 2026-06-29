#!/usr/bin/env python3
"""SSOT: 4 sasang × 3 showroom modes = 12 lens B-track playback pairs (HP050)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator

SASANG_PRIMARY = ("soyang", "taeyang", "taeeum", "soeum")
SHOWROOM_DISPLAY_MODES = ("idle", "defend", "attack")
HP_PCT_MATRIX = 0.5
HP_TAG = "HP050"
LUT_VERSION = datetime.now(timezone.utc).strftime("%Y-%m-%d")
AUDIO_BASE_URL = "https://jemaai.cloud/audio/lens_btrack/v1/"
VIDEO_BASE_URL = "https://jemaai.cloud/video/lens_btrack/v1/"
MATRIX_VERSION = 1

SASANG_BPM_OFFSET: dict[str, int] = {
    "soyang": 0,
    "taeyang": 12,
    "taeeum": -8,
    "soeum": 20,
}
MODE_BPM_OFFSET: dict[str, int] = {
    "idle": 0,
    "defend": -6,
    "attack": 10,
}


def _sasang_upper(sasang: str) -> str:
    s = sasang.strip().lower()
    if s == "taeum":
        s = "taeeum"
    return s.upper()


def _mode_upper(mode: str) -> str:
    m = mode.strip().lower()
    if m not in SHOWROOM_DISPLAY_MODES:
        return "IDLE"
    return m.upper()


def audio_playback_id(sasang: str, mode: str, version: int = MATRIX_VERSION) -> str:
    return f"LM_{HP_TAG}_{_sasang_upper(sasang)}_{_mode_upper(mode)}_V{version}"


def video_playback_id(sasang: str, mode: str, version: int = MATRIX_VERSION) -> str:
    return f"LV_{HP_TAG}_{_sasang_upper(sasang)}_{_mode_upper(mode)}_V{version}"


def audio_filename(sasang: str, mode: str, version: int = MATRIX_VERSION) -> str:
    return f"hp050_{sasang.strip().lower()}_{mode.strip().lower()}_v{version}.wav"


def video_filename(sasang: str, mode: str, version: int = MATRIX_VERSION) -> str:
    return f"lv_hp050_{sasang.strip().lower()}_{mode.strip().lower()}_v{version}.webm"


def video_poster_filename(sasang: str, mode: str, version: int = MATRIX_VERSION) -> str:
    return f"lv_hp050_{sasang.strip().lower()}_{mode.strip().lower()}_v{version}_poster.png"


def iter_matrix_pairs() -> Iterator[tuple[str, str]]:
    for sasang in SASANG_PRIMARY:
        for mode in SHOWROOM_DISPLAY_MODES:
            yield sasang, mode


def target_bpm(sasang: str, mode: str, base_bpm: float = 96.0) -> float:
    s = sasang.strip().lower()
    m = mode.strip().lower()
    return base_bpm + float(SASANG_BPM_OFFSET.get(s, 0) + MODE_BPM_OFFSET.get(m, 0))


def build_audio_lut(*, version: str | None = None) -> dict[str, Any]:
    ver = version or LUT_VERSION
    entries: dict[str, Any] = {}
    for sasang, mode in iter_matrix_pairs():
        pid = audio_playback_id(sasang, mode)
        entries[pid] = {
            "file": audio_filename(sasang, mode),
            "hp_pct": HP_PCT_MATRIX,
            "sasang_primary": sasang,
            "showroom_display_mode": mode,
            "gate_decision": "WATCH",
            "duration_sec": 30,
        }
    return {
        "schema": "jemaai_lens_audio_playback_lut_v1",
        "version": ver,
        "hypothesis_class": "HYPO",
        "assets_base_url": AUDIO_BASE_URL,
        "entries": entries,
    }


def build_video_lut(*, version: str | None = None) -> dict[str, Any]:
    ver = version or LUT_VERSION
    entries: dict[str, Any] = {}
    for sasang, mode in iter_matrix_pairs():
        vid = video_playback_id(sasang, mode)
        entries[vid] = {
            "file": video_filename(sasang, mode),
            "poster_file": video_poster_filename(sasang, mode),
            "sasang_primary": sasang,
            "showroom_display_mode": mode,
            "gate_decision": "WATCH",
            "duration_sec": 12,
            "width": 1280,
            "height": 720,
            "fps": 30,
            "audio_playback_id_mirror": audio_playback_id(sasang, mode),
        }
    return {
        "schema": "jemaai_lens_video_playback_lut_v1",
        "version": ver,
        "hypothesis_class": "HYPO",
        "assets_base_url": VIDEO_BASE_URL,
        "entries": entries,
    }


def matrix_pair_count() -> int:
    return len(SASANG_PRIMARY) * len(SHOWROOM_DISPLAY_MODES)


def showroom_mode_from_final_action(final_action: str) -> str:
    """Map macro/topology final_action label to showroom display mode (PoC heuristic)."""
    fa = str(final_action or "WATCH").strip().upper()
    if fa in ("ATTACK", "AGGRESSIVE", "GO", "MOMENTUM"):
        return "attack"
    if fa in ("REDUCE", "DEFEND", "HOLD_DEFEND", "CRITICAL", "ELEVATED"):
        return "defend"
    return "idle"


def default_sasang_primary() -> str:
    return "soyang"


def normalize_sasang_primary(name: str) -> str:
    s = str(name or "").strip().lower()
    if s == "taeum":
        s = "taeeum"
    if s in SASANG_PRIMARY:
        return s
    return default_sasang_primary()


def sasang_from_macro_scenario(doc: dict[str, Any]) -> tuple[str, str]:
    """Resolve dominant sasang from logos_macro_horizon_2030 scenario (B-track, non-gating)."""
    triad = doc.get("lens_triad_stub") if isinstance(doc.get("lens_triad_stub"), dict) else {}
    sasang_block = triad.get("sasang") if isinstance(triad.get("sasang"), dict) else {}
    dom = sasang_block.get("dominant_constitution")
    if dom:
        return normalize_sasang_primary(str(dom)), "lens_triad_stub.sasang.dominant_constitution"
    vec = sasang_block.get("state_vector_sasang_softmax")
    if isinstance(vec, dict) and vec:
        best = max(vec.items(), key=lambda kv: float(kv[1] or 0))
        return normalize_sasang_primary(str(best[0])), "lens_triad_stub.sasang.state_vector_argmax"
    return default_sasang_primary(), "default_soyang"


def media_hub_query(*, sasang: str | None = None, mode: str | None = None) -> dict[str, str]:
    s = (sasang or default_sasang_primary()).strip().lower()
    m = (mode or "idle").strip().lower()
    pid = audio_playback_id(s, m)
    return {
        "sasang_primary": s,
        "showroom_display_mode": m,
        "playback_id": pid,
        "video_playback_id": video_playback_id(s, m),
        "media_hub_query": f"sasang={s}&mode={m}&playback_id={pid}",
    }
