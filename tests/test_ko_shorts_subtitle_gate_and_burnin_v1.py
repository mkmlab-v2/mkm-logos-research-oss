"""P3 subtitle gate + P4 ASS burn-in unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_ass_burnin_lib_v1 import (  # noqa: E402
    build_ass_v1,
    resolve_ass_style_for_profile_v1,
    seconds_to_ass_ts,
)
from scripts.ko_shorts_subtitle_gate_lib_v1 import (  # noqa: E402
    PROFILES,
    evaluate_subtitle_gate_v1,
    refine_segments_for_profile_v1,
)


def test_seconds_to_ass_ts() -> None:
    assert seconds_to_ass_ts(65.5) == "0:01:05.50"


def test_build_ass_contains_safe_area_style() -> None:
    ass = build_ass_v1(
        [{"start": "00:00:00.00", "end": "00:00:02.00", "text": "안녕하세요"}],
        margin_v=220,
    )
    assert "PlayResX: 1080" in ass
    assert "MarginV" in ass
    assert "안녕하세요" in ass


def test_netflix_gate_fails_long_line() -> None:
    segs = [{"id": "s1", "start": "00:00:00.00", "end": "00:00:02.00", "text": "이 줄은 열여섯 글자를 넘깁니다"}]
    gate = evaluate_subtitle_gate_v1(segs, PROFILES["netflix_v16"])
    assert gate["char_gate_pass"] is False


def test_two_pass_splits_pansori_style_long_cue() -> None:
    from scripts.ko_shorts_subtitle_gate_lib_v1 import (
        PROFILES,
        refine_segments_two_pass_v1,
        two_pass_chunk_text_v1,
    )

    text = "그런데 더 놀라운 사실은 하나하나 보여 드리도록 하겠습니다."
    lines = two_pass_chunk_text_v1(text, max_chars=16)
    assert lines
    assert all(len(x) <= 16 for x in lines)
    parent = [{"id": "p1", "start": "00:00:00.00", "end": "00:00:05.00", "text": text}]
    refined = refine_segments_two_pass_v1(parent, PROFILES["netflix_v16"])
    assert all(len(str(s.get("text") or "")) <= 16 for s in refined)


def test_shorts_gate_passes_short_cues() -> None:
    segs = [
        {"id": "s1", "start": "00:00:00.00", "end": "00:00:02.00", "text": "회고 문화입니다."},
        {"id": "s2", "start": "00:00:02.00", "end": "00:00:05.00", "text": "짧은 회고 한 줄."},
    ]
    refined = refine_segments_for_profile_v1(segs, PROFILES["shorts_v28"])
    gate = evaluate_subtitle_gate_v1(refined, PROFILES["shorts_v28"])
    assert gate["char_gate_pass"] is True


def test_two_pass_netflix_avoids_orphan_ending() -> None:
    from scripts.ko_shorts_subtitle_gate_lib_v1 import two_pass_chunk_text_v1
    from scripts.media_stt_transcription_lib_v1 import _is_orphan_ending

    text = "그런데 더 놀라운 사실은 하나하나 보여 드리도록 하겠습니다."
    lines = two_pass_chunk_text_v1(text, max_chars=16)
    assert lines
    assert all(len(x) <= 16 for x in lines)
    assert not any(_is_orphan_ending(x) for x in lines)


def test_coalesce_orphan_prefix_comma() -> None:
    from scripts.media_stt_transcription_lib_v1 import _is_orphan_prefix, coalesce_orphan_chunks_v1

    lines = coalesce_orphan_chunks_v1(["인류의 역사,", "다음 장으로"], max_chars=16)
    assert lines
    assert not any(_is_orphan_prefix(x) for x in lines)


def test_netflix_ass_style_scales_font() -> None:
    short = [{"text": "짧은 줄"}]
    long = [{"text": "열여섯 글자에 가까운 줄"}]
    short_style = resolve_ass_style_for_profile_v1("netflix_v16", short)
    long_style = resolve_ass_style_for_profile_v1("netflix_v16", long)
    assert int(short_style["font_size"]) >= int(long_style["font_size"])
    assert int(short_style["margin_v"]) >= 240


def test_netflix_pro_ass_has_stronger_outline() -> None:
    segs = [{"text": "회고 문화입니다."}]
    base = resolve_ass_style_for_profile_v1("netflix_v16", segs)
    pro = resolve_ass_style_for_profile_v1("netflix_v16_pro", segs)
    assert int(pro["outline"]) >= int(base["outline"])
    assert int(pro["bold"]) == 1
    ass = build_ass_v1(
        [{"start": "00:00:00.00", "end": "00:00:02.00", "text": "안녕"}],
        outline=int(pro["outline"]),
        shadow=int(pro["shadow"]),
        bold=int(pro["bold"]),
        scale_y=int(pro["scale_y"]),
    )
    assert f",1,0,0,0,100,{int(pro['scale_y'])},0,0,1,{int(pro['outline'])},{int(pro['shadow'])},2," in ass
