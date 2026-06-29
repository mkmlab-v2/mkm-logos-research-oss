#!/usr/bin/env python3
"""Generate harmonic-constrained MIDI for Logic drag-drop (B-track [HYPO]).

Computes notes inside a diatonic set and optional sine CC automation on Windows/Cursor;
target playback host is a lightweight DAW (e.g. Intel Mac + Logic).

Exit 0: wrote .mid (+ optional meta JSON)
Exit 2: invalid args / scale violation guard
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audio.logic_instrument_map_v1_lib import (  # noqa: E402
    cc_automation_events,
    part_by_id,
    resolve_instrument_map,
    sfx_hits_to_note_rows,
    summarize_instrument_map,
    track_prefix_events,
)
from scripts.audio.midi_type0_writer_v1 import (  # noqa: E402
    MidiEvent,
    build_midi_format1,
    build_midi_type0,
    cc_event,
    note_off,
    note_on,
    tempo_meta_event,
)

GM_KICK = 36
GM_SNARE = 38
GM_HIHAT_CLOSED = 42
DRUM_CHANNEL = 9
MELODY_CHANNEL = 0
BASS_CHANNEL = 1
COMMERCIAL_PROGRESSION_DEGREES = [0, 5, 2, 6]  # i - VI - III - VII (natural minor indices)

TICKS_PER_BEAT = 480
NOTE_TO_PC = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}
SCALES = {
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "minor_pentatonic": [0, 3, 5, 7, 10],
}
KEY_RE = re.compile(
    r"^\s*([A-Ga-g])([#b]?)\s*(m|min|minor|maj|major)?\s*$",
    re.IGNORECASE,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_key(key: str) -> tuple[int, str, str]:
    """Return (root_pc, mode, scale_name). mode is 'minor' or 'major'."""
    text = key.strip().replace("-", "")
    m = KEY_RE.match(text)
    if not m:
        raise ValueError(f"unrecognized key: {key!r}")
    letter = m.group(1).upper()
    acc = m.group(2) or ""
    mode_token = (m.group(3) or "major").lower()
    root = NOTE_TO_PC[letter]
    if acc == "#":
        root = (root + 1) % 12
    elif acc == "b":
        root = (root - 1) % 12
    if mode_token in {"m", "min", "minor"}:
        return root, "minor", "natural_minor"
    return root, "major", "major"


def scale_pitch_classes(*, root_pc: int, scale_name: str) -> set[int]:
    rel = SCALES.get(scale_name, SCALES["natural_minor"])
    return {((root_pc + step) % 12) for step in rel}


def midi_in_scale(midi: int, allowed: set[int]) -> bool:
    return (midi % 12) in allowed


def hard_project_midi(midi: int, allowed: set[int], *, prefer_octave: int) -> int:
    pc = midi % 12
    if pc in allowed:
        return midi
    best = None
    best_dist = 10_000
    for cand_pc in allowed:
        for octave in range(prefer_octave - 1, prefer_octave + 2):
            cand = octave * 12 + cand_pc
            dist = abs(cand - midi)
            if dist < best_dist:
                best_dist = dist
                best = cand
    return int(best if best is not None else midi)


def build_arch_degree_indices(*, steps: int) -> list[int]:
    if steps <= 1:
        return [0]
    mid = (steps - 1) / 2.0
    out: list[int] = []
    for i in range(steps):
        if i <= mid:
            t = i / max(mid, 1.0)
            deg = int(round(t * 6))
        else:
            t = (i - mid) / max((steps - 1) - mid, 1.0)
            deg = int(round(6 - t * 6))
        out.append(max(0, min(6, deg)))
    return out


def generate_notes(
    *,
    root_pc: int,
    scale_name: str,
    bars: int,
    beats_per_bar: int,
    note_length_beats: float,
    base_octave_midi: int,
    contour: str,
) -> list[dict[str, Any]]:
    rel = SCALES.get(scale_name, SCALES["natural_minor"])
    allowed = scale_pitch_classes(root_pc=root_pc, scale_name=scale_name)
    prefer_oct = base_octave_midi // 12
    total_beats = bars * beats_per_bar
    step_beats = max(note_length_beats, 0.25)
    steps = max(1, int(math.floor(total_beats / step_beats)))
    if contour == "ascending":
        degree_seq = [min(i, len(rel) - 1) for i in range(steps)]
    elif contour == "descending":
        degree_seq = [max(len(rel) - 1 - i, 0) for i in range(steps)]
    else:
        arch = build_arch_degree_indices(steps=steps)
        degree_seq = [min(d, len(rel) - 1) for d in arch]

    notes: list[dict[str, Any]] = []
    beat = 0.0
    for i, deg in enumerate(degree_seq):
        pc = (root_pc + rel[deg]) % 12
        octave = prefer_oct + (1 if deg >= 4 and contour != "descending" else 0)
        midi = octave * 12 + pc
        midi = hard_project_midi(midi, allowed, prefer_octave=prefer_oct)
        if not midi_in_scale(midi, allowed):
            raise ValueError(f"scale guard failed at step {i}: midi={midi}")
        notes.append(
            {
                "step": i,
                "beat": round(beat, 4),
                "midi": midi,
                "dur_beats": step_beats,
                "scale_degree": deg,
            }
        )
        beat += step_beats
    return notes


def generate_cc_sine(
    *,
    cc_number: int,
    total_beats: float,
    period_beats: float,
    steps_per_beat: int,
    center: float,
    depth: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    step_beats = 1.0 / max(steps_per_beat, 1)
    beat = 0.0
    while beat <= total_beats + 1e-9:
        phase = 2.0 * math.pi * (beat / max(period_beats, 0.25))
        norm = center + depth * 0.5 * math.sin(phase)
        value = int(round(max(0.0, min(1.0, norm)) * 127))
        out.append({"beat": round(beat, 4), "cc": cc_number, "value": value})
        beat += step_beats
    return out


def notes_to_midi_events(
    notes: list[dict[str, Any]],
    *,
    ticks_per_beat: int,
    velocity: int,
    channel: int = 0,
) -> list[MidiEvent]:
    events: list[MidiEvent] = []
    for row in notes:
        beat = float(row["beat"])
        dur = float(row["dur_beats"])
        midi = int(row["midi"])
        on_tick = int(round(beat * ticks_per_beat))
        off_tick = int(round((beat + dur) * ticks_per_beat))
        vel = int(row.get("vel", velocity))
        events.append(note_on(tick=on_tick, midi=midi, velocity=vel, channel=channel))
        events.append(note_off(tick=off_tick, midi=midi, channel=channel))
    return events


def degree_to_midi(*, root_pc: int, rel: list[int], degree: int, octave: int) -> int:
    deg = int(degree) % len(rel)
    pc = (root_pc + rel[deg]) % 12
    return int(octave) * 12 + pc


def generate_drum_groove(
    *,
    bars: int,
    beats_per_bar: int,
    hihat: bool = True,
) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    total_beats = bars * beats_per_bar
    beat = 0.0
    while beat < total_beats - 1e-9:
        bar_beat = beat % beats_per_bar
        if bar_beat in {0.0, 2.0}:
            notes.append({"beat": beat, "midi": GM_KICK, "dur_beats": 0.25, "role": "kick", "vel": 100})
        if bar_beat in {1.0, 3.0}:
            notes.append({"beat": beat, "midi": GM_SNARE, "dur_beats": 0.25, "role": "snare", "vel": 95})
        if hihat and abs((bar_beat * 2) % 1.0) < 1e-9:
            notes.append(
                {
                    "beat": beat,
                    "midi": GM_HIHAT_CLOSED,
                    "dur_beats": 0.125,
                    "role": "hihat",
                    "vel": 70,
                }
            )
        beat += 0.5
    return notes


def generate_bass_line(
    *,
    root_pc: int,
    scale_name: str,
    bars: int,
    beats_per_bar: int,
    bass_octave: int = 2,
) -> list[dict[str, Any]]:
    rel = SCALES.get(scale_name, SCALES["natural_minor"])
    allowed = scale_pitch_classes(root_pc=root_pc, scale_name=scale_name)
    notes: list[dict[str, Any]] = []
    for bar in range(bars):
        deg = COMMERCIAL_PROGRESSION_DEGREES[bar % len(COMMERCIAL_PROGRESSION_DEGREES)]
        beat = float(bar * beats_per_bar)
        midi = degree_to_midi(root_pc=root_pc, rel=rel, degree=deg, octave=bass_octave)
        midi = hard_project_midi(midi, allowed, prefer_octave=bass_octave)
        notes.append(
            {
                "beat": beat,
                "midi": midi,
                "dur_beats": float(beats_per_bar),
                "role": "bass_root",
                "scale_degree": deg,
            }
        )
        if beats_per_bar >= 4:
            mid_beat = beat + 2.0
            walk_deg = (deg + 2) % len(rel)
            walk_midi = degree_to_midi(root_pc=root_pc, rel=rel, degree=walk_deg, octave=bass_octave)
            walk_midi = hard_project_midi(walk_midi, allowed, prefer_octave=bass_octave)
            notes.append(
                {
                    "beat": mid_beat,
                    "midi": walk_midi,
                    "dur_beats": 2.0,
                    "role": "bass_walk",
                    "scale_degree": walk_deg,
                }
            )
    return notes


def drum_notes_to_events(
    notes: list[dict[str, Any]],
    *,
    ticks_per_beat: int,
    channel: int = DRUM_CHANNEL,
) -> list[MidiEvent]:
    events: list[MidiEvent] = []
    for row in notes:
        beat = float(row["beat"])
        dur = float(row["dur_beats"])
        midi = int(row["midi"])
        vel = int(row.get("vel", 90))
        on_tick = int(round(beat * ticks_per_beat))
        off_tick = int(round((beat + dur) * ticks_per_beat))
        events.append(note_on(tick=on_tick, midi=midi, velocity=vel, channel=channel))
        events.append(note_off(tick=off_tick, midi=midi, channel=channel))
    return events


def _part_channel(inst_map: dict[str, Any] | None, part_id: str, default: int) -> int:
    if not inst_map:
        return default
    part = part_by_id(inst_map, part_id)
    if not part:
        return default
    return int(part["midi_channel"])


def build_commercial_3track(params: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    key = str(params.get("key") or "C#m")
    root_pc, mode, scale_name = parse_key(key)
    if params.get("scale"):
        scale_name = str(params["scale"])
    bpm = float(params.get("bpm", 92.0))
    bars = int(params.get("bars", 16))
    beats_per_bar = int(params.get("beats_per_bar", 4))
    melody_octave = int(params.get("base_octave_midi", 61)) // 12
    bass_octave = int(params.get("bass_octave", 2))
    melody_vel = int(params.get("velocity", 78))
    bass_vel = int(params.get("bass_velocity", 85))
    note_length = float(params.get("note_length_beats", 0.5))
    contour = str(params.get("contour", "arch"))

    cc_cfg = dict(params.get("cc") or {})
    cc_number = int(cc_cfg.get("number", 1))
    cc_period = float(cc_cfg.get("period_beats", 8.0))
    cc_steps = int(cc_cfg.get("steps_per_beat", 8))
    cc_center = float(cc_cfg.get("center", 0.5))
    cc_depth = float(cc_cfg.get("depth", 1.0))

    melody = generate_notes(
        root_pc=root_pc,
        scale_name=scale_name,
        bars=bars,
        beats_per_bar=beats_per_bar,
        note_length_beats=note_length,
        base_octave_midi=melody_octave * 12,
        contour=contour,
    )
    bass = generate_bass_line(
        root_pc=root_pc,
        scale_name=scale_name,
        bars=bars,
        beats_per_bar=beats_per_bar,
        bass_octave=bass_octave,
    )
    drums = generate_drum_groove(bars=bars, beats_per_bar=beats_per_bar, hihat=True)

    allowed = scale_pitch_classes(root_pc=root_pc, scale_name=scale_name)
    for part_name, rows in ("melody", melody), ("bass", bass):
        bad = [r for r in rows if not midi_in_scale(int(r["midi"]), allowed)]
        if bad:
            raise ValueError(f"scale violations in {part_name}: {bad[:2]}")

    total_beats = float(bars * beats_per_bar)
    cc_rows = generate_cc_sine(
        cc_number=cc_number,
        total_beats=total_beats,
        period_beats=cc_period,
        steps_per_beat=cc_steps,
        center=cc_center,
        depth=cc_depth,
    )

    inst_map = resolve_instrument_map(params, root=ROOT)
    melody_ch = _part_channel(inst_map, "melody", MELODY_CHANNEL)
    bass_ch = _part_channel(inst_map, "bass", BASS_CHANNEL)
    drum_ch = _part_channel(inst_map, "drums", DRUM_CHANNEL)

    melody_part = part_by_id(inst_map, "melody") if inst_map else None
    bass_part = part_by_id(inst_map, "bass") if inst_map else None
    drum_part = part_by_id(inst_map, "drums") if inst_map else None

    melody_track: list[MidiEvent] = [tempo_meta_event(bpm=bpm, tick=0)]
    if melody_part:
        melody_track.extend(track_prefix_events(melody_part))
    melody_track.extend(
        notes_to_midi_events(
            melody, ticks_per_beat=TICKS_PER_BEAT, velocity=melody_vel, channel=melody_ch
        )
    )
    if melody_part and any(
        str(b.get("automation", "off")).lower() == "sine" and b.get("bind_to_seed_cc")
        for b in melody_part.get("cc_map") or []
    ):
        melody_track.extend(
            cc_automation_events(
                part=melody_part,
                cc_rows=cc_rows,
                ticks_per_beat=TICKS_PER_BEAT,
            )
        )
    else:
        melody_track.extend(
            cc_to_midi_events(cc_rows, ticks_per_beat=TICKS_PER_BEAT, channel=melody_ch)
        )

    bass_track: list[MidiEvent] = []
    if bass_part:
        bass_track.extend(track_prefix_events(bass_part))
    bass_track.extend(
        notes_to_midi_events(bass, ticks_per_beat=TICKS_PER_BEAT, velocity=bass_vel, channel=bass_ch)
    )

    drum_track: list[MidiEvent] = []
    if drum_part:
        drum_track.extend(track_prefix_events(drum_part))
    drum_track.extend(
        drum_notes_to_events(drums, ticks_per_beat=TICKS_PER_BEAT, channel=drum_ch)
    )

    track_specs: list[dict[str, Any]] = [
        {"name": "melody", "channel": melody_ch, "note_count": len(melody)},
        {"name": "bass", "channel": bass_ch, "note_count": len(bass)},
        {"name": "drums", "channel": drum_ch, "note_count": len(drums)},
    ]
    all_tracks: list[list[MidiEvent]] = [melody_track, bass_track, drum_track]

    sfx_rows: list[dict[str, Any]] = []
    sfx_cfg = dict(inst_map.get("sfx") or {}) if inst_map else {}
    if sfx_cfg.get("enabled"):
        sfx_rows = sfx_hits_to_note_rows(sfx_cfg)
        sfx_ch = int(sfx_cfg.get("midi_channel", 2))
        sfx_track: list[MidiEvent] = []
        sfx_part = {
            "midi_channel": sfx_ch,
            "midi_track_name": str(sfx_cfg.get("midi_track_name", "SFX")),
            "instrument": dict(sfx_cfg.get("instrument") or {}),
            "cc_map": [],
        }
        sfx_track.extend(track_prefix_events(sfx_part))
        sfx_track.extend(
            notes_to_midi_events(
                sfx_rows,
                ticks_per_beat=TICKS_PER_BEAT,
                velocity=90,
                channel=sfx_ch,
            )
        )
        all_tracks.append(sfx_track)
        track_specs.append({"name": "sfx", "channel": sfx_ch, "note_count": len(sfx_rows)})

    payload = build_midi_format1(all_tracks, ticks_per_beat=TICKS_PER_BEAT)
    note_count = len(melody) + len(bass) + len(drums) + len(sfx_rows)
    meta = {
        "schema": "constrained_midi_export_v1",
        "layout": "commercial_3track_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track_wall": "B_track_research_only",
        "send_gate": "HOLD",
        "key": key,
        "root_pc": root_pc,
        "mode": mode,
        "scale_name": scale_name,
        "bpm": bpm,
        "bars": bars,
        "beats_per_bar": beats_per_bar,
        "ticks_per_beat": TICKS_PER_BEAT,
        "midi_format": 1,
        "tracks": track_specs,
        "note_count": note_count,
        "cc_event_count": len(cc_rows),
        "cc_number": cc_number,
        "cc_curve": "sine",
        "scale_violation_count": 0,
        "progression": "i-VI-III-VII",
        "notes_preview": melody[:4],
    }
    if inst_map:
        meta["instrument_map"] = summarize_instrument_map(inst_map)
    return payload, meta


def cc_to_midi_events(
    cc_rows: list[dict[str, Any]],
    *,
    ticks_per_beat: int,
    channel: int = 0,
) -> list[MidiEvent]:
    return [
        cc_event(
            tick=int(round(float(row["beat"]) * ticks_per_beat)),
            cc_number=int(row["cc"]),
            value=int(row["value"]),
            channel=channel,
        )
        for row in cc_rows
    ]


def load_seed(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "constrained_midi_seed_v1":
        raise ValueError("expected schema constrained_midi_seed_v1")
    return doc


def build_from_params(params: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    layout = str(params.get("layout") or "single_melody_v1")
    if layout == "commercial_3track_v1":
        return build_commercial_3track(params)

    key = str(params.get("key") or "C")
    root_pc, mode, scale_name = parse_key(key)
    if params.get("scale"):
        scale_name = str(params["scale"])
    bpm = float(params.get("bpm", 120.0))
    bars = int(params.get("bars", 4))
    beats_per_bar = int(params.get("beats_per_bar", 4))
    note_length = float(params.get("note_length_beats", 1.0))
    contour = str(params.get("contour", "arch"))
    velocity = int(params.get("velocity", 80))
    base_octave_midi = int(params.get("base_octave_midi", 60))

    cc_cfg = dict(params.get("cc") or {})
    cc_number = int(cc_cfg.get("number", params.get("cc_number", 1)))
    cc_curve = str(cc_cfg.get("curve", params.get("cc_curve", "sine"))).lower()
    cc_period = float(cc_cfg.get("period_beats", params.get("cc_period_beats", 4.0)))
    cc_center = float(cc_cfg.get("center", 0.5))
    cc_depth = float(cc_cfg.get("depth", 1.0))
    cc_steps = int(cc_cfg.get("steps_per_beat", params.get("cc_steps_per_beat", 4)))

    notes = generate_notes(
        root_pc=root_pc,
        scale_name=scale_name,
        bars=bars,
        beats_per_bar=beats_per_bar,
        note_length_beats=note_length,
        base_octave_midi=base_octave_midi,
        contour=contour,
    )
    total_beats = float(bars * beats_per_bar)
    cc_rows: list[dict[str, Any]] = []
    if cc_curve == "sine":
        cc_rows = generate_cc_sine(
            cc_number=cc_number,
            total_beats=total_beats,
            period_beats=cc_period,
            steps_per_beat=cc_steps,
            center=cc_center,
            depth=cc_depth,
        )

    allowed = scale_pitch_classes(root_pc=root_pc, scale_name=scale_name)
    violations = [n for n in notes if not midi_in_scale(int(n["midi"]), allowed)]
    if violations:
        raise ValueError(f"scale violations: {violations[:3]}")

    events: list[MidiEvent] = [tempo_meta_event(bpm=bpm, tick=0)]
    events.extend(notes_to_midi_events(notes, ticks_per_beat=TICKS_PER_BEAT, velocity=velocity))
    events.extend(cc_to_midi_events(cc_rows, ticks_per_beat=TICKS_PER_BEAT))

    payload = build_midi_type0(events, ticks_per_beat=TICKS_PER_BEAT)
    meta = {
        "schema": "constrained_midi_export_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track_wall": "B_track_research_only",
        "key": key,
        "root_pc": root_pc,
        "mode": mode,
        "scale_name": scale_name,
        "bpm": bpm,
        "bars": bars,
        "beats_per_bar": beats_per_bar,
        "ticks_per_beat": TICKS_PER_BEAT,
        "note_count": len(notes),
        "cc_event_count": len(cc_rows),
        "cc_number": cc_number,
        "cc_curve": cc_curve,
        "scale_violation_count": 0,
        "notes_preview": notes[:8],
    }
    return payload, meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Harmonic-constrained MIDI generator for Logic (B-track [HYPO]).")
    ap.add_argument("--seed-json", type=Path, default=None, help="constrained_midi_seed_v1 JSON")
    ap.add_argument("--key", type=str, default="C#m", help="e.g. C#m, F major, Bbmin")
    ap.add_argument("--scale", type=str, default="", help="override scale name (natural_minor, major, ...)")
    ap.add_argument("--bpm", type=float, default=90.0)
    ap.add_argument("--bars", type=int, default=4)
    ap.add_argument("--beats-per-bar", type=int, default=4)
    ap.add_argument("--note-length-beats", type=float, default=1.0)
    ap.add_argument("--contour", choices=("arch", "ascending", "descending"), default="arch")
    ap.add_argument("--base-octave-midi", type=int, default=49, help="anchor MIDI (49=C#3)")
    ap.add_argument("--velocity", type=int, default=80)
    ap.add_argument("--cc", type=int, default=1, dest="cc_number", help="CC number (default mod wheel)")
    ap.add_argument("--cc-curve", choices=("sine", "off"), default="sine")
    ap.add_argument("--cc-period-beats", type=float, default=4.0)
    ap.add_argument("--cc-steps-per-beat", type=int, default=4)
    ap.add_argument("--out", type=Path, required=True, help="Output .mid path")
    ap.add_argument("--export-meta", type=Path, default=None, help="Optional JSON metadata path")
    ap.add_argument(
        "--instrument-map",
        type=Path,
        default=None,
        help="logic_instrument_map_v1 JSON (overrides seed instrument_map_path)",
    )
    args = ap.parse_args()

    if args.seed_json is not None:
        params = load_seed(args.seed_json)
    else:
        params = {
            "key": args.key,
            "bpm": args.bpm,
            "bars": args.bars,
            "beats_per_bar": args.beats_per_bar,
            "note_length_beats": args.note_length_beats,
            "contour": args.contour,
            "base_octave_midi": args.base_octave_midi,
            "velocity": args.velocity,
            "cc_number": args.cc_number,
            "cc_curve": args.cc_curve,
            "cc_period_beats": args.cc_period_beats,
            "cc_steps_per_beat": args.cc_steps_per_beat,
        }
        if args.scale:
            params["scale"] = args.scale

    if args.instrument_map is not None:
        params["instrument_map_path"] = str(args.instrument_map)

    try:
        payload, meta = build_from_params(params)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(payload)
    meta["path"] = str(args.out.resolve().as_posix())

    if args.export_meta is not None:
        args.export_meta.parent.mkdir(parents=True, exist_ok=True)
        args.export_meta.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": meta["path"],
                "key": meta["key"],
                "notes": meta["note_count"],
                "cc_events": meta["cc_event_count"],
                "scale_violations": meta["scale_violation_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
