from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_lens_audio_observability_smoke(tmp_path: Path) -> None:
    lut = tmp_path / "lut.json"
    out = tmp_path / "block.json"
    lut.write_text(
        json.dumps(
            {
                "schema": "jemaai_lens_audio_playback_lut_v1",
                "version": "2026-06-07",
                "assets_base_url": "https://api.jemaai.cloud/audio/lens_btrack/v1/",
                "entries": {
                    "LM_HP050_SOYANG_IDLE_V1": {
                        "file": "hp050_soyang_idle_v1.wav",
                        "hp_pct": 0.5,
                        "sasang_primary": "soyang",
                        "showroom_display_mode": "idle",
                        "gate_decision": "PASS",
                        "duration_sec": 30,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    script = ROOT / "scripts/build_showroom_lens_audio_observability_v1.py"
    r = subprocess.run(
        [
            sys.executable,
            str(script),
            "--showroom-display-mode",
            "idle",
            "--out-json",
            str(out),
            "--lut",
            str(lut),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    block = json.loads(out.read_text(encoding="utf-8"))
    assert block["schema"] == "public_event_lens_audio_thin_slice_v1"
    assert block["hypothesis_class"] == "HYPO"
    assert block["playback_id"] == "LM_HP050_SOYANG_IDLE_V1"
    assert block["gate"]["decision"] in ("PASS", "WATCH", "HOLD")


def test_build_lens_audio_observability_unit(tmp_path: Path, monkeypatch) -> None:
    import scripts.build_showroom_lens_audio_observability_v1 as mod

    trend = {"schema": "lens_music_hormone_trend_v1", "state": "WATCH"}
    sweep = {
        "schema": "dynamic_bgm_hp_sweep_v1",
        "sasang": "soyang",
        "rows": [
            {
                "hp_pct": 1.0,
                "sasang": "soyang",
                "gate_decision": "PASS",
                "run_id": "abc123def456",
                "gate_metrics": {
                    "lens_alignment_pass": True,
                    "loop_seamlessness_pass": True,
                    "lufs_target_match": True,
                    "commercial_license_verified": True,
                },
            }
        ],
    }
    lut = {
        "schema": "jemaai_lens_audio_playback_lut_v1",
        "version": "2026-06-07",
        "entries": {"LM_HP100_SOYANG_DEFEND_V1": {"file": "hp100.wav"}},
    }
    (tmp_path / "lut.json").write_text(json.dumps(lut), encoding="utf-8")

    def fake_read(path: Path) -> dict:
        name = path.name
        if "trend" in name:
            return trend
        if "sweep" in name:
            return sweep
        return {}

    monkeypatch.setattr(mod, "_read_json", fake_read)

    block = mod.build_lens_audio_observability(
        showroom_display_mode="defend", lut_path=tmp_path / "lut.json"
    )

    assert block["playback_id"] == "LM_HP100_SOYANG_DEFEND_V1"
    assert block["gate"]["decision"] == "WATCH"
    assert block["showroom_display_mode_bind"] == "defend"
