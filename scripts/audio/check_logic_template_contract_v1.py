#!/usr/bin/env python3
"""Validate logic_template_contract_v1 aligns with logic_instrument_map_v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audio.logic_instrument_map_v1_lib import load_instrument_map  # noqa: E402

CONTRACT_SCHEMA = "logic_template_contract_v1"


def load_contract(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != CONTRACT_SCHEMA:
        raise ValueError(f"expected schema {CONTRACT_SCHEMA}")
    return doc


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else ROOT / path


def validate_alignment(contract: dict[str, Any], inst_map: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("template_id") != inst_map.get("template_id"):
        errors.append("template_id mismatch")
    if contract.get("layout") != inst_map.get("layout"):
        errors.append("layout mismatch")

    map_parts = {p["part_id"]: p for p in inst_map.get("parts") or []}
    contract_tracks = [t for t in contract.get("tracks") or [] if t.get("part_id") != "sfx"]
    if len(contract_tracks) != len(map_parts):
        errors.append(f"part count mismatch: contract={len(contract_tracks)} map={len(map_parts)}")

    for track in contract.get("tracks") or []:
        part_id = track.get("part_id")
        if part_id == "sfx":
            sfx = inst_map.get("sfx") or {}
            if not sfx.get("enabled"):
                errors.append("contract has sfx track but map sfx disabled")
                continue
            if int(track.get("midi_channel", -1)) != int(sfx.get("midi_channel", -2)):
                errors.append("sfx midi_channel mismatch")
            if track.get("midi_track_name") != sfx.get("midi_track_name"):
                errors.append("sfx midi_track_name mismatch")
            note_map = sfx.get("note_map") or {}
            regions = {int(r["note"]): r for r in track.get("sampler_regions") or []}
            for note_str, meta in note_map.items():
                note = int(note_str)
                if note not in regions:
                    errors.append(f"sfx note {note} missing from contract sampler_regions")
                elif regions[note].get("sample_id") != meta.get("sample_id"):
                    errors.append(f"sfx sample_id mismatch for note {note}")
            continue

        part = map_parts.get(str(part_id))
        if not part:
            errors.append(f"unknown part_id in contract: {part_id}")
            continue
        for key in ("logic_track_name", "midi_channel", "midi_track_name"):
            if track.get(key) != part.get(key):
                errors.append(f"{part_id}.{key} mismatch")
        inst_m = part.get("instrument") or {}
        for key in ("plugin", "preset", "program"):
            if track.get(key) != inst_m.get(key):
                errors.append(f"{part_id}.{key} mismatch")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Check Logic template contract vs instrument map.")
    ap.add_argument(
        "--contract",
        type=Path,
        default=ROOT / "data/audio/templates/mkm_commercial_csharp_v1.logic_template_contract_v1.json",
    )
    ap.add_argument(
        "--instrument-map",
        type=Path,
        default=None,
        help="override; default read from contract.instrument_map_path",
    )
    ap.add_argument("--export-report", type=Path, default=None)
    args = ap.parse_args()

    contract_path = _resolve(str(args.contract))
    contract = load_contract(contract_path)
    map_path = _resolve(str(args.instrument_map or contract["instrument_map_path"]))
    inst_map = load_instrument_map(map_path)

    errors = validate_alignment(contract, inst_map)
    report = {
        "schema": "logic_template_contract_check_v1",
        "ok": len(errors) == 0,
        "contract_path": str(contract_path.as_posix()),
        "instrument_map_path": str(map_path.as_posix()),
        "template_id": contract.get("template_id"),
        "error_count": len(errors),
        "errors": errors,
        "reproduce": f"py scripts/audio/check_logic_template_contract_v1.py --contract {contract_path.relative_to(ROOT)}",
    }

    if args.export_report:
        out = _resolve(str(args.export_report))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"ok": report["ok"], "errors": errors}, ensure_ascii=False))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
