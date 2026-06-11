"""Smoke tests for lens MusicGen warm batch helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audio.musicgen_external_generator_v1 import (  # noqa: E402
    MusicGenWarmSession,
    _ensure_target_duration,
    _resolve_effective_seconds,
    _resolve_max_new_tokens,
)
from scripts.build_dynamic_bgm_conditioning_diff_v1 import _normalize_sasang_in_prompt  # noqa: E402
from scripts.build_lens_btrack_audio_loops_musicgen_v1 import (  # noqa: E402
    _should_publish_wav,
    recover_from_gen,
    _lut_entries,
)


def test_musicgen_warm_session_import() -> None:
    assert MusicGenWarmSession is not None


def test_should_publish_wav_warn_mode(tmp_path: Path) -> None:
    wav = tmp_path / "bgm.wav"
    wav.write_bytes(b"RIFF" + b"\0" * 40)
    assert _should_publish_wav(chain_rc=1, src_wav=wav, gate_mode="warn") is True
    assert _should_publish_wav(chain_rc=1, src_wav=wav, gate_mode="strict") is False
    assert _should_publish_wav(chain_rc=0, src_wav=wav, gate_mode="strict") is True


def test_recover_from_gen_no_crash(tmp_path: Path) -> None:
    work = tmp_path / "work"
    out = tmp_path / "out"
    out.mkdir()
    gen = work / "soyang_idle" / "gen"
    gen.mkdir(parents=True)
    (gen / "bgm_test_000.wav").write_bytes(b"RIFF" + b"\0" * 40)
    rows = [("LM_HP050_SOYANG_IDLE_V1", "soyang", "idle", 32, "hp050_soyang_idle_v1.wav")]
    n = recover_from_gen(work_root=work, out_dir=out, rows=rows)
    assert n == 1
    assert (out / "hp050_soyang_idle_v1.wav").is_file()


def test_lut_entries_has_twelve() -> None:
    assert len(_lut_entries()) == 12


def test_normalize_sasang_in_prompt_replaces_duplicate() -> None:
    raw = "bed, 96 bpm, sasang soyang, preview, sasang taeeum"
    out = _normalize_sasang_in_prompt(raw, "taeeum")
    assert out.count("sasang") == 1
    assert "sasang taeeum" in out
    assert "soyang" not in out


def test_ensure_target_duration_pads_after_short_stretch() -> None:
    import numpy as np

    short = np.zeros(8000, dtype=np.float32)
    out = _ensure_target_duration(short, 32000, 32.0)
    assert len(out) == 32 * 32000


def test_resolve_effective_seconds_prefers_seed_target_loop() -> None:
    seed = {"target_loop_seconds": 32, "seed_id": "tension_sasang_01"}
    seconds = _resolve_effective_seconds(seed, None, 8.0)
    assert seconds == 32.0


def test_resolve_max_new_tokens_covers_32s_hub_loop() -> None:
    conditioning = {
        "conditioning": {
            "duration_seconds": 32.0,
            "tempo_bpm_target": 96,
        }
    }
    tokens = _resolve_max_new_tokens(32.0, conditioning)
    assert tokens >= 1632
