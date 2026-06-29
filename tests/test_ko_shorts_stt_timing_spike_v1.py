"""P1 ko shorts STT timing spike — offline fixture + lib unit tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/ko_shorts_aligned_words_spike_v1.json"
SPIKE = ROOT / "scripts/run_ko_shorts_stt_timing_spike_v1.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_stt_timing_lib_v1 import (  # noqa: E402
    TIMING_AUTHORITY_ALIGNED,
    chunk_aligned_words_v1,
    compute_timing_drift_ms_v1,
    format_srt_v1,
)
from scripts.run_ko_shorts_stt_timing_spike_v1 import run_spike_from_words  # noqa: E402


def _load_words() -> list[dict]:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(doc["words"])


def test_chunk_aligned_words_merges_orphans_with_token_timing() -> None:
    words = _load_words()
    segs = chunk_aligned_words_v1(words, max_chars=28, pause_gap_sec=0.4)
    texts = [s["text"] for s in segs]
    assert any("첫째, 잘한 것." in t for t in texts)
    assert any("짚어 줍니다." in t for t in texts)
    assert not any(t.strip() == "줍니다." for t in texts)
    assert all(s.get("timing_authority") == TIMING_AUTHORITY_ALIGNED for s in segs)
    assert segs[0]["start"] == "00:00:00.00"
    assert float(segs[-1]["duration_sec"]) > 0


def test_compute_timing_drift_ms_on_fixture() -> None:
    words = _load_words()
    p1 = chunk_aligned_words_v1(words)
    report = run_spike_from_words(
        words,
        wav_source="fixture://test",
        stt_engine="fixture",
        model_name="small",
        pause_gap_sec=0.4,
        max_chars=28,
        min_seg_sec=0.5,
    )
    drift = report["drift_vs_proportional"]
    assert drift["pairs"] >= 1
    assert drift["start_drift_ms_mean"] is not None
    assert drift["start_drift_ms_mean"] >= 0.0
    assert report["timing_authority_p1"] == TIMING_AUTHORITY_ALIGNED


def test_spike_cli_subtitle_profile_netflix(tmp_path: Path) -> None:
    out = tmp_path / "spike.json"
    srt = tmp_path / "spike.srt"
    proc = subprocess.run(
        [
            sys.executable,
            str(SPIKE),
            "--from-words-json",
            str(FIXTURE),
            "--subtitle-profile",
            "netflix_v16",
            "--out",
            str(out),
            "--srt-out",
            str(srt),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("subtitle_profile") == "netflix_v16"
    assert doc.get("subtitle_segment_count", 0) >= 1
    assert (doc.get("subtitle_gate") or {}).get("char_gate_pass") is True
    assert all(len(str(s.get("text") or "")) <= 16 for s in doc.get("subtitle_segments") or [])


def test_spike_cli_offline_fixture(tmp_path: Path) -> None:
    out = tmp_path / "spike.json"
    srt = tmp_path / "spike.srt"
    proc = subprocess.run(
        [
            sys.executable,
            str(SPIKE),
            "--from-words-json",
            str(FIXTURE),
            "--out",
            str(out),
            "--srt-out",
            str(srt),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ko_shorts_stt_timing_spike_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["aligned_word_count"] == 8
    assert srt.is_file()
    assert "00:00:00,000" in srt.read_text(encoding="utf-8")


def test_format_srt_v1_nonempty() -> None:
    segs = chunk_aligned_words_v1(_load_words())
    srt = format_srt_v1(segs)
    assert "-->" in srt
    assert "회고" in srt


def test_drift_differs_when_p0_p1_misaligned() -> None:
    p0 = [{"start": "00:00:00.00", "end": "00:00:02.00", "text": "a"}]
    p1 = [{"start": "00:00:01.00", "end": "00:00:03.00", "text": "a"}]
    drift = compute_timing_drift_ms_v1(p0, p1)
    assert drift["start_drift_ms_mean"] == 1000.0
