"""Load and apply Logic instrument map v1 (B-track symbolic render contract)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.audio.midi_type0_writer_v1 import (
    MidiEvent,
    bank_select_events,
    cc_event,
    program_change_event,
    track_name_meta_event,
)

SCHEMA = "logic_instrument_map_v1"


def load_instrument_map(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"expected schema {SCHEMA}")
    if not doc.get("parts"):
        raise ValueError("instrument map requires parts")
    return doc


def resolve_instrument_map(params: dict[str, Any], *, root: Path) -> dict[str, Any] | None:
    if isinstance(params.get("instrument_map"), dict):
        doc = dict(params["instrument_map"])
        if doc.get("schema") != SCHEMA:
            raise ValueError(f"expected schema {SCHEMA}")
        return doc
    rel = params.get("instrument_map_path")
    if not rel:
        return None
    path = Path(rel)
    if not path.is_absolute():
        path = root / path
    return load_instrument_map(path)


def part_by_id(inst_map: dict[str, Any], part_id: str) -> dict[str, Any] | None:
    for part in inst_map.get("parts") or []:
        if str(part.get("part_id")) == part_id:
            return dict(part)
    return None


def track_prefix_events(part: dict[str, Any]) -> list[MidiEvent]:
    """Emit tick-0 track name, bank/program, and static CC initials."""
    channel = int(part["midi_channel"])
    events: list[MidiEvent] = [
        track_name_meta_event(name=str(part["midi_track_name"]), tick=0),
    ]
    instrument = dict(part.get("instrument") or {})
    bank_msb = instrument.get("bank_msb")
    bank_lsb = instrument.get("bank_lsb")
    if bank_msb is not None or bank_lsb is not None:
        events.extend(
            bank_select_events(
                tick=0,
                channel=channel,
                bank_msb=int(bank_msb or 0),
                bank_lsb=int(bank_lsb or 0),
            )
        )
    program = instrument.get("program")
    if program is not None:
        events.append(program_change_event(tick=0, program=int(program), channel=channel))
    for binding in part.get("cc_map") or []:
        if str(binding.get("automation", "off")).lower() != "static":
            continue
        initial = binding.get("initial")
        if initial is None:
            continue
        events.append(
            cc_event(
                tick=0,
                cc_number=int(binding["cc"]),
                value=int(initial),
                channel=channel,
            )
        )
    return events


def cc_automation_events(
    *,
    part: dict[str, Any],
    cc_rows: list[dict[str, Any]],
    ticks_per_beat: int,
) -> list[MidiEvent]:
    channel = int(part["midi_channel"])
    out: list[MidiEvent] = []
    for binding in part.get("cc_map") or []:
        if str(binding.get("automation", "off")).lower() != "sine":
            continue
        if not binding.get("bind_to_seed_cc"):
            continue
        cc_number = int(binding["cc"])
        for row in cc_rows:
            tick = int(round(float(row["beat"]) * ticks_per_beat))
            out.append(
                cc_event(
                    tick=tick,
                    cc_number=cc_number,
                    value=int(row["value"]),
                    channel=channel,
                )
            )
    return out


def sfx_hits_to_note_rows(sfx: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hit in sfx.get("hits") or []:
        rows.append(
            {
                "beat": float(hit["beat"]),
                "midi": int(hit["note"]),
                "dur_beats": float(hit.get("dur_beats", 0.25)),
                "vel": int(hit.get("velocity", 90)),
                "role": "sfx",
                "sample_id": str(hit.get("sample_id", "")),
            }
        )
    return rows


def summarize_instrument_map(inst_map: dict[str, Any]) -> dict[str, Any]:
    parts_summary = []
    for part in inst_map.get("parts") or []:
        instrument = dict(part.get("instrument") or {})
        parts_summary.append(
            {
                "part_id": part.get("part_id"),
                "midi_channel": part.get("midi_channel"),
                "midi_track_name": part.get("midi_track_name"),
                "logic_track_name": part.get("logic_track_name"),
                "plugin": instrument.get("plugin"),
                "preset": instrument.get("preset"),
                "program": instrument.get("program"),
                "cc_roles": [b.get("role") for b in part.get("cc_map") or []],
                "fx_sends": part.get("fx_sends") or [],
            }
        )
    sfx = dict(inst_map.get("sfx") or {})
    return {
        "template_id": inst_map.get("template_id"),
        "logic_template_path": inst_map.get("logic_template_path"),
        "layout": inst_map.get("layout"),
        "parts": parts_summary,
        "sfx_enabled": bool(sfx.get("enabled")),
        "sfx_hit_count": len(sfx.get("hits") or []) if sfx.get("enabled") else 0,
    }
