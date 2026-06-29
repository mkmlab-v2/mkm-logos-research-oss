#!/usr/bin/env python3
"""Minimal format-0 MIDI writer (no external deps). B-track utility for Logic drag-drop."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MidiEvent:
    tick: int
    data: bytes


def var_len(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative delta not allowed")
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def tempo_meta_event(*, bpm: float, tick: int = 0) -> MidiEvent:
    us_per_quarter = int(round(60_000_000 / max(bpm, 1.0)))
    data = bytes([0xFF, 0x51, 0x03]) + us_per_quarter.to_bytes(3, "big")
    return MidiEvent(tick=tick, data=data)


def note_on(*, tick: int, midi: int, velocity: int = 80, channel: int = 0) -> MidiEvent:
    return MidiEvent(tick=tick, data=bytes([0x90 | (channel & 0x0F), midi & 0x7F, velocity & 0x7F]))


def note_off(*, tick: int, midi: int, channel: int = 0) -> MidiEvent:
    return MidiEvent(tick=tick, data=bytes([0x80 | (channel & 0x0F), midi & 0x7F, 0]))


def cc_event(*, tick: int, cc_number: int, value: int, channel: int = 0) -> MidiEvent:
    return MidiEvent(
        tick=tick,
        data=bytes([0xB0 | (channel & 0x0F), cc_number & 0x7F, value & 0x7F]),
    )


def program_change_event(*, tick: int, program: int, channel: int = 0) -> MidiEvent:
    return MidiEvent(
        tick=tick,
        data=bytes([0xC0 | (channel & 0x0F), program & 0x7F]),
    )


def bank_select_events(
    *,
    tick: int,
    channel: int,
    bank_msb: int,
    bank_lsb: int,
) -> list[MidiEvent]:
    return [
        cc_event(tick=tick, cc_number=0, value=bank_msb & 0x7F, channel=channel),
        cc_event(tick=tick, cc_number=32, value=bank_lsb & 0x7F, channel=channel),
    ]


def track_name_meta_event(*, name: str, tick: int = 0) -> MidiEvent:
    encoded = name.encode("utf-8")
    data = bytes([0xFF, 0x03, len(encoded)]) + encoded
    return MidiEvent(tick=tick, data=data)


def _serialize_track(events: list[MidiEvent]) -> bytes:
    ordered = sorted(events, key=lambda e: e.tick)
    track = bytearray()
    last_tick = 0
    for ev in ordered:
        dt = ev.tick - last_tick
        if dt < 0:
            dt = 0
        track.extend(var_len(dt))
        track.extend(ev.data)
        last_tick = ev.tick
    track.extend(var_len(0))
    track.extend(b"\xFF\x2F\x00")
    return bytes(track)


def build_midi_type0(events: list[MidiEvent], *, ticks_per_beat: int = 480) -> bytes:
    track = _serialize_track(events)
    header = bytearray()
    header.extend(b"MThd")
    header.extend((6).to_bytes(4, "big"))
    header.extend((0).to_bytes(2, "big"))
    header.extend((1).to_bytes(2, "big"))
    header.extend(int(ticks_per_beat).to_bytes(2, "big"))

    chunk = bytearray()
    chunk.extend(b"MTrk")
    chunk.extend(len(track).to_bytes(4, "big"))
    chunk.extend(track)
    return bytes(header + chunk)


def build_midi_format1(track_events: list[list[MidiEvent]], *, ticks_per_beat: int = 480) -> bytes:
    """Format 1 — one SMF track per part (Logic-friendly)."""
    if not track_events:
        raise ValueError("track_events required")
    header = bytearray()
    header.extend(b"MThd")
    header.extend((6).to_bytes(4, "big"))
    header.extend((1).to_bytes(2, "big"))
    header.extend(len(track_events).to_bytes(2, "big"))
    header.extend(int(ticks_per_beat).to_bytes(2, "big"))

    chunks = bytearray()
    for events in track_events:
        track = _serialize_track(events)
        chunks.extend(b"MTrk")
        chunks.extend(len(track).to_bytes(4, "big"))
        chunks.extend(track)
    return bytes(header + chunks)
