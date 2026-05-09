from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_example_gate_report_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = ROOT / "docs/final/schemas/audio_bgm_gate_report_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/audio_bgm_gate_report_v1.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    instance = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def test_build_report_pass_when_optional_deps_mocked(monkeypatch, tmp_path):
    import wave

    from scripts.audio.evaluate_audio_gate import build_report

    monkeypatch.setattr(
        "scripts.audio.evaluate_audio_gate._measure_lufs",
        lambda _path: (True, -14.0, True),
    )

    policy = json.loads((ROOT / "policies/audio_copyright_field.json").read_text(encoding="utf-8"))
    wav = tmp_path / "silence.wav"
    with wave.open(str(wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 44100)

    report = build_report(
        wav_path=wav,
        field_policy=policy,
        seed={"seed_id": "x", "lufs_profile": "streaming_minus14_lufs_v1"},
        provenance={
            "provider": "self_hosted",
            "model_id": "test-model",
            "commercial_terms_tag": "apache2_self_host_weights_v1",
        },
        track="A",
        run_id="test_run",
        lufs_profile="streaming_minus14_lufs_v1",
        loop_join_policy={
            "crossfade_ms": 12.0,
            "max_join_sample_jump": 0.02,
            "eval_window_samples": 2048,
        },
    )
    assert report["decision"] == "PASS"


def test_waive_flags_allow_pass_with_bpm_without_detector(monkeypatch, tmp_path):
    import wave

    from scripts.audio.evaluate_audio_gate import build_report

    monkeypatch.setattr(
        "scripts.audio.evaluate_audio_gate._measure_lufs",
        lambda _path: (False, None, False),
    )

    policy = json.loads((ROOT / "policies/audio_copyright_field.json").read_text(encoding="utf-8"))
    wav = tmp_path / "silence.wav"
    with wave.open(str(wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        wf.writeframes(b"\x00\x00" * 96000)

    report = build_report(
        wav_path=wav,
        field_policy=policy,
        seed={"seed_id": "with_bpm", "bpm": 96, "lufs_profile": "streaming_minus14_lufs_v1"},
        provenance={
            "provider": "self_hosted",
            "model_id": "test-model",
            "commercial_terms_tag": "apache2_self_host_weights_v1",
        },
        track="A",
        run_id="test_run",
        lufs_profile="streaming_minus14_lufs_v1",
        loop_join_policy={
            "crossfade_ms": 12.0,
            "max_join_sample_jump": 0.02,
            "eval_window_samples": 2048,
        },
        waive_lufs=True,
        waive_bpm_lens=True,
    )
    assert report["decision"] == "PASS"
    assert "lufs_waived_explicit_cli" in (report["metrics"].get("skipped_checks") or [])
    assert "bpm_lens_waived_explicit_cli" in (report["metrics"].get("skipped_checks") or [])


def test_run_bgm_batch_placeholder_writes_wav_and_meta(tmp_path, monkeypatch):
    import sys

    from scripts.audio import run_bgm_generation_batch as batch

    seed = tmp_path / "seed.json"
    seed.write_text(
        json.dumps({"seed_id": "batch_smoke", "bpm": 100}),
        encoding="utf-8",
    )
    out = tmp_path / "raw"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_bgm_generation_batch.py",
            "--seed-json",
            str(seed),
            "--count",
            "1",
            "--output-dir",
            str(out),
            "--emit",
            "placeholder",
            "--run-id",
            "smokebatch01",
        ],
    )
    assert batch.main() == 0
    wavs = list(out.glob("bgm_smokebatch01_000.wav"))
    metas = list(out.glob("bgm_smokebatch01_000.meta.json"))
    assert len(wavs) == 1 and len(metas) == 1
    assert "apache2_self_host_weights_v1" in metas[0].read_text(encoding="utf-8")


def test_gemini_default_billing_env(monkeypatch):
    from scripts.audio import gemini_bgm_seed_expand_v1 as g

    monkeypatch.setenv("MKM_AUDIO_GEMINI_BILLING", "vertex")
    assert g._default_billing_arg() == "vertex"
    monkeypatch.setenv("MKM_AUDIO_GEMINI_BILLING", "bogus")
    assert g._default_billing_arg() == "developer"
    monkeypatch.delenv("MKM_AUDIO_GEMINI_BILLING", raising=False)
    assert g._default_billing_arg() == "developer"


def test_run_bgm_batch_placeholder_with_gate_passes(tmp_path, monkeypatch):
    import sys

    from scripts.audio import run_bgm_generation_batch as batch

    seed = tmp_path / "seed.json"
    seed.write_text(
        json.dumps({"seed_id": "gate_smoke", "bpm": 100}),
        encoding="utf-8",
    )
    out = tmp_path / "raw"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_bgm_generation_batch.py",
            "--seed-json",
            str(seed),
            "--count",
            "1",
            "--output-dir",
            str(out),
            "--emit",
            "placeholder",
            "--run-id",
            "gatebatch01",
            "--run-gate",
            "--gate-waive-lufs",
            "--gate-waive-bpm-lens",
            "--gate-export-dir",
            str(tmp_path / "gates_out"),
            "--gate-skip-latest-copy",
        ],
    )
    assert batch.main() == 0
    summary = json.loads((out / "_batch_gatebatch01.json").read_text(encoding="utf-8"))
    assert summary["written_wavs"]
    assert summary.get("gate_all_pass") is True
    assert "gate_summary_path" in summary
    gate_sum = tmp_path / "gates_out" / "_gates_summary_gatebatch01.json"
    assert gate_sum.is_file()
    loaded = json.loads(gate_sum.read_text(encoding="utf-8"))
    assert loaded["gates"][0]["decision"] == "PASS"


def test_external_generator_template_cli_smoke(tmp_path):
    import subprocess
    import sys

    seed = tmp_path / "s.json"
    seed.write_text(json.dumps({"seed_id": "tpl"}), encoding="utf-8")
    wav = tmp_path / "o.wav"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/external_generator_template_v1.py"),
            "--seed-json",
            str(seed),
            "--out-wav",
            str(wav),
            "--index",
            "0",
            "--run-id",
            "r1",
        ],
        cwd=str(ROOT),
    )
    assert r.returncode == 0
    assert wav.is_file()


def test_gemini_seed_expand_dry_run_writes_json(tmp_path):
    import subprocess
    import sys

    seed = tmp_path / "s.json"
    seed.write_text(json.dumps({"seed_id": "dry"}), encoding="utf-8")
    out = tmp_path / "out.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/gemini_bgm_seed_expand_v1.py"),
            "--seed-json",
            str(seed),
            "--out-json",
            str(out),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("billing_surface") == "dry_run"


def test_gemini_placeholder_skip_gemini(tmp_path):
    import subprocess
    import sys

    seed = tmp_path / "s.json"
    seed.write_text(json.dumps({"seed_id": "x"}), encoding="utf-8")
    out_wav = tmp_path / "a.wav"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/gemini_placeholder_external_generator_v1.py"),
            "--seed-json",
            str(seed),
            "--out-wav",
            str(out_wav),
            "--skip-gemini",
        ],
        cwd=str(ROOT),
    )
    assert r.returncode == 0
    assert out_wav.is_file()


def test_run_bgm_batch_external_stub(monkeypatch, tmp_path):
    import sys

    from scripts.audio import run_bgm_generation_batch as batch

    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"seed_id": "ext_smoke"}), encoding="utf-8")
    out = tmp_path / "raw"
    stub = ROOT / "scripts/audio/external_generator_stub_v1.py"
    monkeypatch.setenv("MKM_AUDIO_EXTERNAL_SCRIPT", str(stub))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_bgm_generation_batch.py",
            "--seed-json",
            str(seed),
            "--count",
            "1",
            "--output-dir",
            str(out),
            "--emit",
            "external",
            "--run-id",
            "ext001",
        ],
    )
    assert batch.main() == 0
    assert list(out.glob("bgm_ext001_000.wav"))


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not on PATH")
def test_run_bgm_batch_external_ffmpeg_bed_smoke(monkeypatch, tmp_path):
    import sys

    from scripts.audio import run_bgm_generation_batch as batch

    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"seed_id": "ext_ffbed", "bpm": 82}), encoding="utf-8")
    out = tmp_path / "raw"
    script = ROOT / "scripts/audio/ffmpeg_bed_external_generator_v1.py"
    monkeypatch.setenv("MKM_AUDIO_EXTERNAL_SCRIPT", str(script))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_bgm_generation_batch.py",
            "--seed-json",
            str(seed),
            "--count",
            "1",
            "--output-dir",
            str(out),
            "--emit",
            "external",
            "--run-id",
            "ffbed01",
            "--placeholder-seconds",
            "0.5",
        ],
    )
    assert batch.main() == 0
    assert list(out.glob("bgm_ffbed01_000.wav"))


def test_gemini_bgm_extract_json_object_plain():
    from scripts.audio import gemini_bgm_seed_expand_v1 as g

    out = g._extract_json_object('{"schema": "x", "a": 1}')
    assert out["schema"] == "x" and out["a"] == 1


def test_gemini_bgm_extract_json_object_prefix_and_markdown_fence():
    from scripts.audio import gemini_bgm_seed_expand_v1 as g

    noisy = 'Sure:\n```json\n{"schema": "gemini_bgm_seed_expand_v1", "k": 2}\n```\n'
    out = g._extract_json_object(noisy)
    assert out["k"] == 2


def test_gemini_bgm_extract_json_object_nested_braces_in_string():
    from scripts.audio import gemini_bgm_seed_expand_v1 as g

    text = '{"schema": "y", "notes_for_human": "brace chars like {a} in strings"}'
    out = g._extract_json_object(text)
    assert out["schema"] == "y" and "{a}" in out["notes_for_human"]


def test_gemini_bgm_extract_json_object_empty_raises():
    from scripts.audio import gemini_bgm_seed_expand_v1 as g

    with pytest.raises(ValueError):
        g._extract_json_object("")


@pytest.mark.parametrize(
    "rel",
    [
        "data/audio/seeds/tension_sasang_01.example.json",
        "data/audio/seeds/calm_taeeum_01.example.json",
    ],
)
def test_audio_bgm_example_seeds_parse(rel):
    p = ROOT / rel
    assert p.is_file()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("schema") == "audio_bgm_seed_v1"
    assert data.get("seed_id")


def test_tone_external_generator_cli_and_gate_passes(tmp_path, monkeypatch):
    import subprocess
    import sys

    from scripts.audio.evaluate_audio_gate import build_report

    monkeypatch.setattr(
        "scripts.audio.evaluate_audio_gate._measure_lufs",
        lambda _path: (True, -14.0, True),
    )

    seed_path = tmp_path / "seed.json"
    seed_path.write_text(
        json.dumps(
            {
                "seed_id": "tone_cli_smoke",
                "bpm": 96,
                "lufs_profile": "streaming_minus14_lufs_v1",
            }
        ),
        encoding="utf-8",
    )
    wav = tmp_path / "tone.wav"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/tone_external_generator_v1.py"),
            "--seed-json",
            str(seed_path),
            "--out-wav",
            str(wav),
            "--seconds",
            "1.5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr + rc.stdout
    assert wav.is_file()

    policy = json.loads((ROOT / "policies/audio_copyright_field.json").read_text(encoding="utf-8"))
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    report = build_report(
        wav_path=wav,
        field_policy=policy,
        seed=seed,
        provenance={
            "provider": "self_hosted",
            "model_id": "tone_external_generator_v1",
            "commercial_terms_tag": "apache2_self_host_weights_v1",
        },
        track="A",
        run_id="tone_cli_smoke",
        lufs_profile="streaming_minus14_lufs_v1",
        loop_join_policy={
            "crossfade_ms": 12.0,
            "max_join_sample_jump": 0.02,
            "eval_window_samples": 2048,
        },
        waive_lufs=False,
        waive_bpm_lens=True,
    )
    assert report["decision"] == "PASS"
    import subprocess
    import sys

    from scripts.audio.evaluate_audio_gate import build_report

    monkeypatch.setattr(
        "scripts.audio.evaluate_audio_gate._measure_lufs",
        lambda _path: (True, -14.0, True),
    )

    seed_path = tmp_path / "seed.json"
    seed_path.write_text(
        json.dumps(
            {
                "seed_id": "expand_tone_skip",
                "bpm": 88,
                "lufs_profile": "streaming_minus14_lufs_v1",
            }
        ),
        encoding="utf-8",
    )
    wav = tmp_path / "out.wav"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/expand_tone_external_generator_v1.py"),
            "--seed-json",
            str(seed_path),
            "--out-wav",
            str(wav),
            "--seconds",
            "1.5",
            "--skip-expand",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr + rc.stdout
    assert wav.is_file()

    policy = json.loads((ROOT / "policies/audio_copyright_field.json").read_text(encoding="utf-8"))
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    report = build_report(
        wav_path=wav,
        field_policy=policy,
        seed=seed,
        provenance={
            "provider": "self_hosted",
            "model_id": "expand_tone_external_generator_v1",
            "commercial_terms_tag": "apache2_self_host_weights_v1",
        },
        track="A",
        run_id="expand_tone_skip",
        lufs_profile="streaming_minus14_lufs_v1",
        loop_join_policy={
            "crossfade_ms": 12.0,
            "max_join_sample_jump": 0.02,
            "eval_window_samples": 2048,
        },
        waive_lufs=False,
        waive_bpm_lens=True,
    )
    assert report["decision"] == "PASS"


def test_expand_tone_external_generator_dry_expand_gate_passes(tmp_path, monkeypatch):
    import subprocess
    import sys

    from scripts.audio.evaluate_audio_gate import build_report

    monkeypatch.setenv("MKM_AUDIO_EXPAND_DRY_RUN", "1")
    monkeypatch.setattr(
        "scripts.audio.evaluate_audio_gate._measure_lufs",
        lambda _path: (True, -14.0, True),
    )

    seed_path = tmp_path / "seed.json"
    seed_path.write_text(
        json.dumps(
            {
                "seed_id": "expand_tone_dry",
                "bpm": 100,
                "lufs_profile": "streaming_minus14_lufs_v1",
            }
        ),
        encoding="utf-8",
    )
    wav = tmp_path / "dry.wav"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/expand_tone_external_generator_v1.py"),
            "--seed-json",
            str(seed_path),
            "--out-wav",
            str(wav),
            "--seconds",
            "1.5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr + rc.stdout
    assert wav.is_file()
    exp = wav.with_suffix(".expand.json")
    assert exp.is_file()

    policy = json.loads((ROOT / "policies/audio_copyright_field.json").read_text(encoding="utf-8"))
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    report = build_report(
        wav_path=wav,
        field_policy=policy,
        seed=seed,
        provenance={
            "provider": "self_hosted",
            "model_id": "expand_tone_external_generator_v1",
            "commercial_terms_tag": "apache2_self_host_weights_v1",
        },
        track="A",
        run_id="expand_tone_dry",
        lufs_profile="streaming_minus14_lufs_v1",
        loop_join_policy={
            "crossfade_ms": 12.0,
            "max_join_sample_jump": 0.02,
            "eval_window_samples": 2048,
        },
        waive_lufs=False,
        waive_bpm_lens=True,
    )
    assert report["decision"] == "PASS"


def test_ffmpeg_bed_external_generator_force_tone_fallback_cli(tmp_path):
    import subprocess
    import sys

    seed = tmp_path / "s.json"
    seed.write_text(json.dumps({"seed_id": "ffbed_force", "bpm": 90}), encoding="utf-8")
    wav = tmp_path / "o.wav"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/ffmpeg_bed_external_generator_v1.py"),
            "--seed-json",
            str(seed),
            "--out-wav",
            str(wav),
            "--seconds",
            "1.0",
            "--force-tone-fallback",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert wav.is_file()
    row = json.loads(r.stdout.strip())
    assert row["backend"] == "tone_fallback"
    assert row["reason"] == "force_tone_fallback"
    assert row.get("hz")
    assert row.get("expand_prompt_influence") is False


def test_ffmpeg_bed_expand_prompt_influence_json(tmp_path):
    import subprocess
    import sys

    seed = tmp_path / "s.json"
    seed.write_text(json.dumps({"seed_id": "ffbed_prompt", "bpm": 90}), encoding="utf-8")
    wav = tmp_path / "o.wav"
    exp = wav.with_suffix(".expand.json")
    exp.write_text(
        json.dumps(
            {
                "expanded_prompt_en": "dark cinematic pads",
                "expanded_prompt_ko": "어두운 패드",
                "suggested_duration_sec": 1.0,
            }
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/ffmpeg_bed_external_generator_v1.py"),
            "--seed-json",
            str(seed),
            "--out-wav",
            str(wav),
            "--seconds",
            "2.0",
            "--force-tone-fallback",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert wav.is_file()
    row = json.loads(r.stdout.strip())
    assert row["expand_prompt_influence"] is True
    assert len(row.get("prompt_digest16", "")) == 16
    assert float(row["seconds"]) == 1.0


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not on PATH")
def test_ffmpeg_bed_external_generator_lavfi_when_ffmpeg_present(tmp_path):
    import subprocess
    import sys

    seed = tmp_path / "s.json"
    seed.write_text(json.dumps({"seed_id": "ffbed_lavfi", "bpm": 88}), encoding="utf-8")
    wav = tmp_path / "o.wav"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/ffmpeg_bed_external_generator_v1.py"),
            "--seed-json",
            str(seed),
            "--out-wav",
            str(wav),
            "--seconds",
            "0.8",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert wav.is_file()
    row = json.loads(r.stdout.strip())
    assert row["backend"] == "ffmpeg_lavfi"
    assert row.get("ffmpeg")
    assert row.get("expand_prompt_influence") is False
    assert row.get("noise_color") == "brown"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not on PATH")
def test_ffmpeg_bed_lavfi_noise_color_from_prompt(tmp_path):
    import subprocess
    import sys

    seed = tmp_path / "s.json"
    seed.write_text(json.dumps({"seed_id": "ffbed_ncolor", "bpm": 92}), encoding="utf-8")
    wav = tmp_path / "o.wav"
    exp = wav.with_suffix(".expand.json")
    exp.write_text(
        json.dumps({"expanded_prompt_en": "ambient wash", "expanded_prompt_ko": "분위기"}),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/ffmpeg_bed_external_generator_v1.py"),
            "--seed-json",
            str(seed),
            "--out-wav",
            str(wav),
            "--seconds",
            "0.6",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    row = json.loads(r.stdout.strip())
    assert row["backend"] == "ffmpeg_lavfi"
    assert row["noise_color"] in ("brown", "pink", "white")
    assert row.get("expand_prompt_influence") is True


def test_check_audio_gate_optional_deps_cli_smoke():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audio/check_audio_gate_optional_deps_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    row = json.loads(r.stdout.strip())
    assert row["lufs_measurement_available"] == (row["numpy"] and row["pyloudnorm"])


def test_check_audio_gate_optional_deps_require_all_when_installed():
    pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    import subprocess
    import sys

    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/check_audio_gate_optional_deps_v1.py"),
            "--require-all",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_measure_lufs_measured_flag_when_pyloudnorm_installed(tmp_path):
    pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    import math
    import struct
    import wave

    from scripts.audio.evaluate_audio_gate import _measure_lufs

    sr = 48000
    n = sr // 2
    path = tmp_path / "s.wav"
    amp = 8000
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for i in range(n):
            v = int(amp * math.sin(2 * math.pi * 220 * i / sr))
            wf.writeframes(struct.pack("<h", max(-32767, min(32767, v))))

    _ok, val, measured = _measure_lufs(path)
    assert measured is True
    assert val is not None
