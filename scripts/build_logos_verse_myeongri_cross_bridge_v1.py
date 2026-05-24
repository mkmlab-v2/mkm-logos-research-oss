#!/usr/bin/env python3
"""Track B Cross-Bridge v0: frozen verse OS 4D (gematria bridge) vs human Myeongri 4D geometry.

Pedagogical map: compare broadcast (verse medoid) vs receiver (golden birth profile) frequencies —
L2/cosine only; not healing, trading, or doctrinal proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_VERSE_JSONL = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
DEFAULT_MEDOID_MANIFEST = ROOT / "docs/final/artifacts/logos_verse_4d_medoids_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_verse_myeongri_cross_bridge_v1_latest.json"

# SSOT golden terminal (myeongri_deterministic_lora_golden_sample_v1.jsonl row 1)
GOLDEN_BIRTH_INSTANT_UTC = "1992-03-12T17:00:00Z"
GOLDEN_IANA_TZ = "Asia/Seoul"
GOLDEN_ENGINE = {"year": 1992, "month": 3, "day": 13, "hour": 2, "is_solar": True, "is_male": False}

# SSOT human terminals for Cross-Bridge demos (B-track, NON_GATING).
STANDARD_HUMAN_PROFILES: list[dict[str, Any]] = [
    {
        "profile_id": "golden_mdl_gs_v1_0001",
        "birth_instant_utc": GOLDEN_BIRTH_INSTANT_UTC,
        "iana_tz": GOLDEN_IANA_TZ,
        "engine_inputs": dict(GOLDEN_ENGINE),
        "ssot": "tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl (mdl-gs-v1-0001)",
    },
    {
        "profile_id": "golden_mdl_gs_v1_0002",
        "birth_instant_utc": "2000-01-01T12:00:00Z",
        "iana_tz": "UTC",
        "engine_inputs": {
            "year": 2000,
            "month": 1,
            "day": 1,
            "hour": 12,
            "is_solar": True,
            "is_male": False,
        },
        "ssot": "tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl (mdl-gs-v1-0002)",
    },
    {
        "profile_id": "patient_intake_demo_v1",
        "birth_instant_utc": "1990-05-15T05:30:00Z",
        "iana_tz": "Asia/Seoul",
        "engine_inputs": {
            "year": 1990,
            "month": 5,
            "day": 15,
            "hour": 14,
            "is_solar": True,
            "is_male": True,
        },
        "ssot": "tests/fixtures/patient_intake_fusion_draft_v1.example.json (ENC-DEMO, de-identified)",
    },
]

SCHEMA = "logos_verse_myeongri_cross_bridge_v1"
VERSION = "1.0.0"

INTERPRETATION_NOTE = (
    "[HYPO] Geometric distance between gematria-bridge verse 4D (frozen v1_core_subset map) and "
    "MyeongriCompleteFusion birth 4D under fixed recipes. Same axis labels (S,L,K,M) do not imply "
    "identical measurement instruments. Not proof of semantic resonance, correction, or promotion readiness."
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_verse_row(jsonl: Path, verse_id: str) -> dict[str, Any]:
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("verse_id") == verse_id:
                return row
    raise KeyError(f"verse_id not found in {jsonl}: {verse_id}")


def _default_verse_id(medoid_manifest: Path) -> str:
    doc = json.loads(medoid_manifest.read_text(encoding="utf-8"))
    medoids = doc.get("global_medoids") or []
    if not medoids:
        raise ValueError(f"no global_medoids in {medoid_manifest}")
    return str(medoids[0]["verse_id"])


def _human_vector_4d_from_engine(engine: dict[str, Any]) -> dict[str, float]:
    from scripts.myeongri_complete_fusion import MyeongriCompleteFusion

    fusion = MyeongriCompleteFusion().calculate_complete_fusion(
        int(engine["year"]),
        int(engine["month"]),
        int(engine["day"]),
        int(engine["hour"]),
        is_solar=bool(engine.get("is_solar", True)),
        is_male=bool(engine.get("is_male", True)),
    )
    vec = fusion.get("vector_4d") or {}
    return {k: float(vec[k]) for k in ("S", "L", "K", "M")}


def _human_vector_4d() -> dict[str, float]:
    return _human_vector_4d_from_engine(GOLDEN_ENGINE)


def resolve_human_profiles(profile_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Materialize STANDARD_HUMAN_PROFILES (or subset) with vector_4d."""
    wanted = set(profile_ids) if profile_ids else None
    out: list[dict[str, Any]] = []
    for spec in STANDARD_HUMAN_PROFILES:
        pid = str(spec["profile_id"])
        if wanted is not None and pid not in wanted:
            continue
        engine = spec["engine_inputs"]
        vec = _human_vector_4d_from_engine(engine)
        out.append(
            {
                "profile_id": pid,
                "birth_instant_utc": spec.get("birth_instant_utc"),
                "iana_tz": spec.get("iana_tz"),
                "engine_inputs": dict(engine),
                "vector_4d": vec,
                "ssot": spec.get("ssot"),
            }
        )
    return out


def build_report(
    *,
    verse_row: dict[str, Any],
    human_vec: dict[str, float],
    blend_weight_myeongri: float | None,
    verse_jsonl: Path,
    medoid_manifest: Path,
) -> dict[str, Any]:
    from tools.myeongni.gematria_myeongri_math_v1 import (
        MATH_MODULE_ID,
        MATH_MODULE_VERSION,
        blend_convex_renorm,
        coerce_4d,
        cosine_similarity,
        l2_distance,
    )

    os_vec = coerce_4d(verse_row["vector_4d"])
    hum_vec = coerce_4d(human_vec)
    geometry = {
        "l2_os_human": round(l2_distance(os_vec, hum_vec), 8),
        "cosine_os_human": round(cosine_similarity(os_vec, hum_vec), 8),
    }
    blend: dict[str, Any] | None = None
    if blend_weight_myeongri is not None:
        w = float(blend_weight_myeongri)
        hybrid = blend_convex_renorm(os_vec, hum_vec, w)
        blend = {
            "weight_myeongri": w,
            "vector_4d_hybrid": hybrid,
            "l2_os_hybrid": round(l2_distance(os_vec, hybrid), 8),
            "cosine_os_hybrid": round(cosine_similarity(os_vec, hybrid), 8),
        }

    mapping = verse_row.get("mapping") or {}
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "subset_id": "v1_core_subset",
        "ts_utc": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "interpretation_note": INTERPRETATION_NOTE,
        "pedagogical_map": {
            "verse_os": "universe_broadcast_station_gematria_4d",
            "human_terminal": "receiver_myeongri_4d_golden_profile",
            "geometry": "frequency_distance_meter_not_healing_proof",
        },
        "inputs": {
            "verse_4d_jsonl": _rel(verse_jsonl),
            "verse_4d_jsonl_sha256": _sha256_file(verse_jsonl) if verse_jsonl.is_file() else None,
            "medoid_manifest": _rel(medoid_manifest),
            "golden_birth_instant_utc": GOLDEN_BIRTH_INSTANT_UTC,
            "golden_iana_tz": GOLDEN_IANA_TZ,
            "golden_engine_inputs": dict(GOLDEN_ENGINE),
            "golden_profile_ssot": "tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl (mdl-gs-v1-0001)",
        },
        "verse_os": {
            "verse_id": verse_row["verse_id"],
            "lane": verse_row.get("lane"),
            "vector_4d": os_vec,
            "mapping_recipe_id": mapping.get("recipe_id"),
            "medoid_rank": 1,
        },
        "human_terminal": {
            "profile_id": "golden_mdl_gs_v1_0001",
            "birth_instant_utc": GOLDEN_BIRTH_INSTANT_UTC,
            "iana_tz": GOLDEN_IANA_TZ,
            "engine_inputs": dict(GOLDEN_ENGINE),
            "fusion_runner": "scripts/myeongri_complete_fusion.py",
            "vector_4d": hum_vec,
        },
        "geometry": geometry,
        "blend_optional": blend,
        "math_module": {"id": MATH_MODULE_ID, "version": MATH_MODULE_VERSION},
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
            "ready_for_external_send": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verse-id", type=str, default=None, help="Default: rank-1 global medoid")
    ap.add_argument("--verse-jsonl", type=Path, default=DEFAULT_VERSE_JSONL)
    ap.add_argument("--medoid-manifest", type=Path, default=DEFAULT_MEDOID_MANIFEST)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--blend-weight-myeongri",
        type=float,
        default=None,
        help="If set (0..1), also emit convex hybrid vector metrics",
    )
    ap.add_argument("--validate-schema", action="store_true", help="Validate against JSON Schema before write")
    args = ap.parse_args()

    verse_jsonl = args.verse_jsonl if args.verse_jsonl.is_absolute() else ROOT / args.verse_jsonl
    medoid_manifest = (
        args.medoid_manifest if args.medoid_manifest.is_absolute() else ROOT / args.medoid_manifest
    )
    if not verse_jsonl.is_file():
        print(f"missing verse jsonl: {verse_jsonl}", file=sys.stderr)
        return 1
    if not medoid_manifest.is_file():
        print(f"missing medoid manifest: {medoid_manifest}", file=sys.stderr)
        return 1

    verse_id = args.verse_id or _default_verse_id(medoid_manifest)
    verse_row = _load_verse_row(verse_jsonl, verse_id)
    human_vec = _human_vector_4d()
    doc = build_report(
        verse_row=verse_row,
        human_vec=human_vec,
        blend_weight_myeongri=args.blend_weight_myeongri,
        verse_jsonl=verse_jsonl,
        medoid_manifest=medoid_manifest,
    )

    if args.validate_schema:
        schema_path = ROOT / "docs/final/schemas/logos_verse_myeongri_cross_bridge_v1.schema.json"
        if not schema_path.is_file():
            print(f"missing schema: {schema_path}", file=sys.stderr)
            return 1
        jsonschema = __import__("jsonschema")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(schema).validate(doc)

    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {out_path} verse={verse_id} l2={doc['geometry']['l2_os_human']} "
        f"cosine={doc['geometry']['cosine_os_human']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
