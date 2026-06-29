from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data/audio/seeds/csharp_minor_sine_cc1.example.json"
COMMERCIAL_SEED = ROOT / "data/audio/seeds/csharp_minor_commercial_16bar_v1.example.json"
INSTRUMENT_MAP = ROOT / "data/audio/maps/mkm_commercial_csharp_v1.example.json"
SCRIPT = ROOT / "scripts/audio/generate_constrained_midi_v1.py"


def test_parse_csharp_minor_key():
    from scripts.audio.generate_constrained_midi_v1 import parse_key, scale_pitch_classes

    root_pc, mode, scale_name = parse_key("C#m")
    assert root_pc == 1
    assert mode == "minor"
    assert scale_name == "natural_minor"
    allowed = scale_pitch_classes(root_pc=root_pc, scale_name=scale_name)
    assert allowed == {1, 3, 4, 6, 8, 9, 11}


def test_generate_notes_stay_in_scale():
    from scripts.audio.generate_constrained_midi_v1 import (
        generate_notes,
        midi_in_scale,
        parse_key,
        scale_pitch_classes,
    )

    root_pc, _, scale_name = parse_key("C#m")
    allowed = scale_pitch_classes(root_pc=root_pc, scale_name=scale_name)
    notes = generate_notes(
        root_pc=root_pc,
        scale_name=scale_name,
        bars=4,
        beats_per_bar=4,
        note_length_beats=1.0,
        base_octave_midi=49,
        contour="arch",
    )
    assert len(notes) == 16
    assert all(midi_in_scale(int(n["midi"]), allowed) for n in notes)


def test_cc_sine_values_bounded():
    from scripts.audio.generate_constrained_midi_v1 import generate_cc_sine

    rows = generate_cc_sine(
        cc_number=1,
        total_beats=4.0,
        period_beats=4.0,
        steps_per_beat=4,
        center=0.5,
        depth=1.0,
    )
    assert len(rows) == 17
    assert all(0 <= int(r["value"]) <= 127 for r in rows)


def test_cli_writes_binary_midi(tmp_path: Path):
    out_mid = tmp_path / "melody.mid"
    meta = tmp_path / "meta.json"
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not prev else f"{ROOT}{__import__('os').pathsep}{prev}"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seed-json",
            str(SEED),
            "--out",
            str(out_mid),
            "--export-meta",
            str(meta),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    blob = out_mid.read_bytes()
    assert blob[:4] == b"MThd"
    assert b"MTrk" in blob
    doc = json.loads(meta.read_text(encoding="utf-8"))
    assert doc["schema"] == "constrained_midi_export_v1"
    assert doc["key"] == "C#m"
    assert doc["scale_violation_count"] == 0
    assert doc["note_count"] == 16
    assert doc["cc_event_count"] > 0


def test_commercial_3track_16bar_format1(tmp_path: Path):
    from scripts.audio.generate_constrained_midi_v1 import build_from_params, load_seed

    seed = load_seed(COMMERCIAL_SEED)
    payload, meta = build_from_params(seed)
    assert payload[:4] == b"MThd"
    assert payload[8:10] == b"\x00\x01"  # MIDI format 1
    assert meta["layout"] == "commercial_3track_v1"
    assert meta["bars"] == 16
    assert meta["scale_violation_count"] == 0
    assert meta["note_count"] > 100
    assert meta["cc_event_count"] >= 16 * 4 * 8
    assert len(meta["tracks"]) == 4
    assert meta.get("instrument_map", {}).get("template_id") == "mkm_commercial_csharp_v1"
    assert meta["instrument_map"]["sfx_hit_count"] == 2

    out_mid = tmp_path / "commercial.mid"
    meta_path = tmp_path / "commercial_meta.json"
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not prev else f"{ROOT}{__import__('os').pathsep}{prev}"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seed-json",
            str(COMMERCIAL_SEED),
            "--out",
            str(out_mid),
            "--export-meta",
            str(meta_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert out_mid.stat().st_size > 500
    blob = out_mid.read_bytes()
    assert b"Melody" in blob
    assert b"\xc0" in blob or b"\xc1" in blob


def test_instrument_map_track_prefix_and_program_change():
    from scripts.audio.logic_instrument_map_v1_lib import load_instrument_map, track_prefix_events
    from scripts.audio.midi_type0_writer_v1 import _serialize_track

    inst = load_instrument_map(INSTRUMENT_MAP)
    melody = next(p for p in inst["parts"] if p["part_id"] == "melody")
    events = track_prefix_events(melody)
    track_bytes = _serialize_track(events)
    assert b"Melody" in track_bytes
    assert b"\xc0" in track_bytes
    assert any(ev.data[0] == 0xB0 and ev.data[1] == 11 for ev in events)
