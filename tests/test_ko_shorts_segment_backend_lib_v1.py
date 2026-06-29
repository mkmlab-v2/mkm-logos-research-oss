"""P2 segment backend bench — semantic vs kss (offline)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_segment_backend_lib_v1 import (  # noqa: E402
    BACKEND_KSS_FAST,
    BACKEND_SEMANTIC,
    compare_backends_on_text_v1,
    compute_subtitle_line_metrics_v1,
    segment_kss_fast_ko_v1,
    segment_semantic_chunk_ko_v1,
)


def test_semantic_and_kss_agree_on_clean_punct() -> None:
    text = "첫째, 잘한 것. 둘째, 개선할 점."
    assert segment_semantic_chunk_ko_v1(text) == segment_kss_fast_ko_v1(text)


def test_metrics_flags_netflix_over_16() -> None:
    metrics = compute_subtitle_line_metrics_v1(
        ["짧은줄", "이 문장은 열여섯 글자를 넘깁니다"],
        duration_sec=4.0,
        netflix_max_chars=16,
    )
    assert metrics["lines_over_netflix_max"] == 1
    assert metrics["cps_mean"] > 0


def test_compare_backends_fixture_orphan() -> None:
    text = "오늘 회고 문화를 짚어 줍니다."
    cmp = compare_backends_on_text_v1(text, duration_sec=3.0, backends=(BACKEND_SEMANTIC, BACKEND_KSS_FAST))
    sem = cmp[BACKEND_SEMANTIC]["lines"]
    assert sem == ["오늘 회고 문화를 짚어 줍니다."]
    assert cmp[BACKEND_SEMANTIC]["metrics"]["line_count"] >= 1
