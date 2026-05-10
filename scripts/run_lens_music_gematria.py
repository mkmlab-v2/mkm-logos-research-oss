#!/usr/bin/env python3
"""Music/Gematria translation lens stub (B-track): Sasang (+ optional integer) → audio parameter JSON.

Does not generate audio. Does not claim clinical efficacy. Independent of `run_lens_sasang.py`
(no shared state). Outputs envelope `lens_music_gematria_v1` with `resolved_outputs` compatible
with `docs/final/schemas/sasang_music_mapping_v1.schema.json` outputs section.

Optional `--emotion-mapping-json` loads `sasang_emotion_mapping_v1` and attaches deterministic
VA anchors (`emotion_va_overlay_v1`) — audio numeric outputs are unchanged unless downstream
code consumes the overlay (§3.10 TRACK_C).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_ENVELOPE = "lens_music_gematria_v1"
ENGINE_VERSION = "0.1.0"
BUILTIN_TABLE_VERSION = "builtin_sasang_hypo_v1_2026-05-10"

# Deterministic HYPO table only — swap via explicit --mapping-json for experiments.
_BUILTIN_SASANG: dict[str, dict[str, Any]] = {
    "taeyang": {
        "tempo_bpm": {"target": 108, "min": 92, "max": 124},
        "harmony": {"mode_hint": "major", "root_pc": 2},
        "dynamics": {"velocity_0_1": 0.62},
    },
    "soyang": {
        "tempo_bpm": {"target": 96, "min": 82, "max": 110},
        "harmony": {"mode_hint": "mixolydian", "root_pc": 7},
        "dynamics": {"velocity_0_1": 0.58},
    },
    "taeeum": {
        "tempo_bpm": {"target": 72, "min": 60, "max": 84},
        "harmony": {"mode_hint": "minor", "root_pc": 0},
        "dynamics": {"velocity_0_1": 0.55},
    },
    "soeumin": {
        "tempo_bpm": {"target": 60, "min": 48, "max": 72},
        "harmony": {"mode_hint": "minor", "root_pc": 5},
        "dynamics": {"velocity_0_1": 0.48},
    },
}

_DEFAULT_SAFETY = {
    "min_hz": 80.0,
    "max_hz": 12000.0,
    "max_velocity_0_1": 0.92,
}


def _validate_mapping_doc(doc: dict[str, Any]) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        raise RuntimeError("jsonschema required for --mapping-json validation; pip install jsonschema")
    schema_path = ROOT / "docs/final/schemas/sasang_music_mapping_v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def _validate_emotion_mapping_doc(doc: dict[str, Any]) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        raise RuntimeError("jsonschema required for --emotion-mapping-json; pip install jsonschema")
    schema_path = ROOT / "docs/final/schemas/sasang_emotion_mapping_v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def _build_emotion_va_overlay(
    emotion_doc: dict[str, Any],
    sasang_primary: str,
    *,
    source_path: str,
) -> dict[str, Any]:
    key = sasang_primary.strip().lower()
    anchors = emotion_doc.get("anchors") or {}
    if key not in anchors:
        raise ValueError(
            f"emotion anchors missing sasang_primary={key!r}; "
            f"have {sorted(anchors)}"
        )
    pt = anchors[key]
    return {
        "schema": "emotion_va_overlay_v1",
        "emotion_mapping_schema": "sasang_emotion_mapping_v1",
        "mapping_version": emotion_doc["mapping_version"],
        "emotion_model": emotion_doc["emotion_model"],
        "sasang_primary": key,
        "valence": float(pt["valence"]),
        "arousal": float(pt["arousal"]),
        "emotion_mapping_source": source_path,
        "note": "VA lookup only; tempo/harmony unchanged unless a downstream step consumes this overlay.",
    }


def _apply_gematria_tempo_shift(outputs: dict[str, Any], gematria: int) -> None:
    """In-place narrow tempo window shift; deterministic, bounded."""
    tb = outputs["tempo_bpm"]
    delta = (gematria % 33) - 16  # [-16, 16]
    tb["target"] = float(max(tb["min"], min(tb["max"], tb["target"] + delta)))


def _builtin_mapping_v1(
    sasang: str,
    gematria: int | None,
    *,
    mapping_version: str,
    experiment_id: str,
) -> dict[str, Any]:
    key = sasang.strip().lower()
    if key not in _BUILTIN_SASANG:
        raise ValueError(f"unknown sasang_primary: {sasang!r}; expected one of {sorted(_BUILTIN_SASANG)}")
    base = _BUILTIN_SASANG[key]
    outputs: dict[str, Any] = {
        "tempo_bpm": {k: float(v) if k != "target" else float(v) for k, v in base["tempo_bpm"].items()},
        "harmony": dict(base["harmony"]),
        "dynamics": dict(base["dynamics"]),
        "safety": dict(_DEFAULT_SAFETY),
    }
    if gematria is not None:
        _apply_gematria_tempo_shift(outputs, int(gematria))

    return {
        "schema": "sasang_music_mapping_v1",
        "version": "1.0.0",
        "mapping_version": mapping_version,
        "hypothesis_class": "HYPO",
        "notes": f"builtin table {BUILTIN_TABLE_VERSION}; not clinical; replace with --mapping-json for sweeps.",
        "inputs": {"sasang_primary": key, "gematria_total_optional": gematria},
        "outputs": outputs,
        "provenance": {"source": "batch_generate", "experiment_id": experiment_id},
    }


def _envelope(
    *,
    resolution: str,
    mapping_doc: dict[str, Any] | None,
    resolved_outputs: dict[str, Any],
    extra_provenance: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": SCHEMA_ENVELOPE,
        "version": ENGINE_VERSION,
        "lens_id": "music_gematria",
        "ts_utc": now,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autobind_forbidden": True,
        "resolution": resolution,
        "sasang_music_mapping_v1": mapping_doc,
        "resolved_outputs": resolved_outputs,
        "provenance": extra_provenance,
        "note": "B-track translation stub only; no audio render; not music therapy; not TOE.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit lens_music_gematria_v1 JSON (Sasang→audio params stub).")
    ap.add_argument("--mapping-json", type=Path, help="Full sasang_music_mapping_v1 document path.")
    ap.add_argument("--sasang-primary", type=str, help="One of taeyang|soyang|taeeum|soeumin (if no --mapping-json).")
    ap.add_argument("--gematria-total", type=int, default=None, help="Optional integer shift for builtin tempo.")
    ap.add_argument(
        "--mapping-version",
        type=str,
        default=BUILTIN_TABLE_VERSION,
        help="mapping_version string for builtin runs.",
    )
    ap.add_argument("--experiment-id", type=str, default="lens_music_gematria_cli")
    ap.add_argument("--output", type=Path, default=None, help="Write JSON here; default stdout.")
    ap.add_argument(
        "--emotion-mapping-json",
        type=Path,
        default=None,
        help="Optional sasang_emotion_mapping_v1 document; VA anchors merged into envelope as emotion_va_overlay_v1.",
    )
    args = ap.parse_args()

    try:
        if args.mapping_json is not None:
            doc = json.loads(args.mapping_json.read_text(encoding="utf-8"))
            _validate_mapping_doc(doc)
            resolved = doc["outputs"]
            env = _envelope(
                resolution="explicit_mapping_document",
                mapping_doc=doc,
                resolved_outputs=resolved,
                extra_provenance={
                    "source": "mapping_json_file",
                    "path": str(args.mapping_json.resolve()),
                    "experiment_id": args.experiment_id,
                },
            )
        else:
            if not args.sasang_primary:
                print("error: provide --mapping-json or --sasang-primary", file=sys.stderr)
                return 2
            doc = _builtin_mapping_v1(
                args.sasang_primary,
                args.gematria_total,
                mapping_version=args.mapping_version,
                experiment_id=args.experiment_id,
            )
            env = _envelope(
                resolution="builtin_sasang_table_v1",
                mapping_doc=doc,
                resolved_outputs=doc["outputs"],
                extra_provenance={
                    "source": "builtin_table",
                    "experiment_id": args.experiment_id,
                    "builtin_version": BUILTIN_TABLE_VERSION,
                },
            )

        if args.emotion_mapping_json is not None:
            edoc = json.loads(args.emotion_mapping_json.read_text(encoding="utf-8"))
            _validate_emotion_mapping_doc(edoc)
            sm = env.get("sasang_music_mapping_v1")
            if not isinstance(sm, dict) or "inputs" not in sm:
                raise ValueError("internal: missing sasang_music_mapping_v1.inputs for emotion overlay")
            sk = str(sm["inputs"].get("sasang_primary", "")).strip().lower()
            if not sk:
                raise ValueError("sasang_primary missing in mapping envelope")
            env["emotion_va_overlay_v1"] = _build_emotion_va_overlay(
                edoc,
                sk,
                source_path=str(args.emotion_mapping_json.resolve()),
            )

        text = json.dumps(env, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"WROTE: {args.output.resolve()}", file=sys.stderr)
        else:
            sys.stdout.write(text)
        return 0
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
