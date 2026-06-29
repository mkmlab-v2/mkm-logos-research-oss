#!/usr/bin/env python3
"""Build Logos Cosmic Anchor pilot v1 — static coordinate rows (Wave 1).

Reproducible:
  py scripts/build_logos_cosmic_anchor_pilot_v1.py

Outputs:
  docs/final/artifacts/logos_cosmic_anchor_pilot_v1/{seed,light,way}.json
  docs/final/artifacts/logos_cosmic_anchor_pilot_v1_manifest_latest.json
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

from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge
from scripts.core.normalize_gematria_to_kernel_v1 import (
    NORMALIZE_FN,
    kernel_drafts_from_4d,
    rank_primitive_alignments,
)

OUT_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_pilot_v1"
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_pilot_v1_manifest_latest.json"
MKMLIFE_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data"
MKMLIFE_ANCHOR_DIR = MKMLIFE_PUBLIC / "logos_cosmic_anchor_pilot_v1"
MKMLIFE_MANIFEST = MKMLIFE_PUBLIC / "logos_cosmic_anchor_pilot_v1_manifest_latest.json"

PRESET_LOOKUP: dict[str, str] = {
    "job_suffering_reason": "cosmic_anchor_seed_jhn_12_24",
}

FACT_LOCK = {
    "hypothesis_class": "HYPO",
    "rail": "B_TRACK",
    "non_gating": True,
    "forbidden_synthesis": True,
    "ready_for_external_send": False,
    "disclaimer_ko": (
        "[HYPO] gematria 4D ↔ kernel draft resonance row. "
        "신학·체질·운세 단정 아님. Track A·live·SEND 금지."
    ),
}

TRACK_WALL = {
    "a_track_auto_promotion": False,
    "live_trading_trigger": False,
}

PILOT_SPECS: list[dict[str, Any]] = [
    {
        "file_stem": "seed",
        "anchor_id": "cosmic_anchor_seed_jhn_12_24",
        "verse_refs": ["Jhn.12.24"],
        "motif_lemma": {"greek": "σπερμα", "scope": "motif_lemma"},
        "gematria_text": "σπερμα",
        "gematria_texts": {
            "raw": (
                "αμην αμην λεγω υμιν εαν μη ο κοκκος του σιτου πεσων εις την γην "
                "αποθανη αυτος μονος μενει εαν δε αποθανη πολυν καρπον φερει"
            ),
            "compressed": "σπερμα",
            "reconstructed": "κοκκος σιτου πεσων εις την γην αποθανη",
        },
        "logos_summary_ko": (
            "씨앗 motif — 잠재·죽음·열매 narrative (Jhn.12.24). "
            "motif note only; verse-level dogma 금지."
        ),
        "sasang_summary_ko": (
            "응축·경계·보명지주 motif (사상 card). "
            "임상 체질 단정 아님."
        ),
        "constitution_hint": "none",
        "ohaeng_hint": "water",
        "legacy_thermo_alias": {
            "energy_intensity_raw": 22.0,
            "pulse_frequency_hz": 4.0,
            "density_coefficient": 1.83,
            "harmony_constant": 0.88,
        },
        "conflict_resolution": {"pair_kind": "none"},
    },
    {
        "file_stem": "light",
        "anchor_id": "cosmic_anchor_light_jhn_1_5",
        "verse_refs": ["Jhn.1.5"],
        "motif_lemma": {"greek": "φως", "scope": "motif_lemma"},
        "gematria_text": "φως",
        "gematria_texts": {
            "raw": "και το φως εν τη σκοτια φαινει και η σκοτια αυτο ου κατελαβεν",
            "compressed": "φως",
            "reconstructed": "φως εν τη σκοτια φαινει",
        },
        "logos_summary_ko": (
            "빛 motif — 어둠 대비 radiant/expansive narrative (Jhn.1.5). "
            "motif note only."
        ),
        "sasang_summary_ko": (
            "화(火) 원심·확장 motif (명리 accent card). "
            "체질 처방 아님."
        ),
        "constitution_hint": "soeumin",
        "ohaeng_hint": "fire",
        "legacy_thermo_alias": {
            "energy_intensity_raw": 1500.0,
            "pulse_frequency_hz": 6.0,
            "density_coefficient": 0.45,
            "harmony_constant": 0.95,
        },
        "conflict_resolution": {
            "pair_kind": "controlling",
            "peer_anchor_ids": ["cosmic_anchor_seed_jhn_12_24"],
            "harmony_draft": {"layout_density": 0.55, "contrast_cap": 0.28},
            "circulation_draft": {"transition_ms": 280, "accent_budget_pct_max": 8},
        },
    },
    {
        "file_stem": "way",
        "anchor_id": "cosmic_anchor_way_jhn_14_6",
        "verse_refs": ["Jhn.14.6"],
        "motif_lemma": {"greek": "οδος", "scope": "motif_lemma"},
        "gematria_text": "οδος",
        "gematria_texts": {
            "raw": (
                "λεγει αυτω ιησους εγω ειμι η οδος και η αληθεια και η ζωη "
                "ουδεις ερχεται προς τον πατερα ει μη δι εμου"
            ),
            "compressed": "οδος",
            "reconstructed": "εγω ειμι η οδος και η αληθεια",
        },
        "logos_summary_ko": (
            "길(way) motif — 방향·프레임 narrative (Jhn.14.6). "
            "motif note only."
        ),
        "sasang_summary_ko": (
            "경로·프레임·토(土) 중재 motif (명리 card). "
            "운세·길흉 단정 아님."
        ),
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "legacy_thermo_alias": {
            "energy_intensity_raw": 374.0,
            "pulse_frequency_hz": 5.0,
            "density_coefficient": 1.05,
            "harmony_constant": 0.92,
        },
        "conflict_resolution": {"pair_kind": "generating"},
    },
]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _gematria_inputs(spec: dict[str, Any]) -> tuple[str, str, str, str]:
    texts = spec.get("gematria_texts")
    if isinstance(texts, dict):
        raw = str(texts.get("raw") or spec["gematria_text"])
        compressed = str(texts.get("compressed") or spec["gematria_text"])
        reconstructed = str(texts.get("reconstructed") or compressed)
        canonical = raw
        return raw, compressed, reconstructed, canonical
    text = str(spec["gematria_text"])
    return text, text, text, text


def _build_row(spec: dict[str, Any], *, generated_at_utc: str) -> dict[str, Any]:
    raw_text, compressed_text, reconstructed_text, canonical_text = _gematria_inputs(spec)
    meta = build_gematria_metadata(
        raw_text=raw_text,
        compressed_text=compressed_text,
        reconstructed_text=reconstructed_text,
    )
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    vector_4d = bridge["vector_4d"]
    alignments = rank_primitive_alignments(vector_4d, top_n=3)

    return {
        "schema": "logos_cosmic_anchor_formalization_v1",
        "version": "1.0.0",
        "anchor_id": spec["anchor_id"],
        "verse_refs": spec["verse_refs"],
        "motif_lemma": spec["motif_lemma"],
        "fact_lock": dict(FACT_LOCK),
        "layers": {
            "logos_layer": {
                "summary_ko": spec["logos_summary_ko"],
                "citation_refs": spec["verse_refs"],
                "interpretive_class": "motif_note",
            },
            "sasang_myeongni_layer": {
                "summary_ko": spec["sasang_summary_ko"],
                "ssot_refs": [
                    "docs/final/artifacts/sasang_design_primitive_kernel_v1_latest.json",
                    "docs/final/LENS_UTILIZATION_CHARTER_V1.md",
                ],
                "constitution_hint": spec["constitution_hint"],
                "ohaeng_hint": spec["ohaeng_hint"],
            },
        },
        "text_span": {
            "unit": "verse" if spec.get("gematria_texts") else "motif_lemma",
            "original_script_text": canonical_text,
            "text_sha256": _sha256(canonical_text),
        },
        "gematria_v1": {
            "method": "mispar_hechrachi_additive",
            "hebrew_value": int(meta.get("raw_hebrew_sum", 0)),
            "greek_value": int(meta.get("raw_greek_sum", 0)),
            "total_value": int(meta.get("raw_combined_sum", 0)),
        },
        "vector_4d": vector_4d,
        "legacy_thermo_alias": spec.get("legacy_thermo_alias"),
        "mapping": {
            "recipe_id": "gematria_bridge_v1",
            "normalize_fn": NORMALIZE_FN,
            "generated_at_utc": generated_at_utc,
            "state16_nearest": bridge.get("state16"),
            "distance_to_state16": bridge.get("distance_to_state16"),
        },
        "kernel_alignment": alignments,
        "conflict_resolution": spec.get("conflict_resolution") or {"pair_kind": "none"},
        "track_wall": dict(TRACK_WALL),
        "_builder_meta": {
            "kernel_drafts_full": kernel_drafts_from_4d(vector_4d),
            "gematria_metadata": meta,
        },
    }


def build_all() -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    anchor_rows: list[dict[str, Any]] = []
    paths: dict[str, str] = {}
    lookup_by_verse: dict[str, str] = {}

    for spec in PILOT_SPECS:
        row = _build_row(spec, generated_at_utc=generated_at_utc)
        # Strip internal builder-only block from written artifact
        public_row = {k: v for k, v in row.items() if not k.startswith("_")}
        out_path = OUT_DIR / f"{spec['file_stem']}.json"
        out_path.write_text(
            json.dumps(public_row, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        anchor_rows.append(public_row)
        paths[spec["file_stem"]] = out_path.relative_to(ROOT).as_posix()
        for ref in spec["verse_refs"]:
            lookup_by_verse[ref] = spec["anchor_id"]

    manifest = {
        "schema": "logos_cosmic_anchor_pilot_v1_manifest",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "anchor_count": len(anchor_rows),
        "anchor_ids": [r["anchor_id"] for r in anchor_rows],
        "paths": paths,
        "lookup_by_verse_ref": lookup_by_verse,
        "lookup_by_preset_id": dict(PRESET_LOOKUP),
        "lookup_manifest_fn": "lookup_cosmic_anchor_by_verse_ref_v1",
        "mkmlife_public_manifest": MKMLIFE_MANIFEST.relative_to(ROOT).as_posix(),
        "reproducible_command": "py scripts/build_logos_cosmic_anchor_pilot_v1.py",
        "formalization_schema": "docs/final/schemas/logos_cosmic_anchor_formalization_v1.schema.json",
        "pytest": "tests/test_logos_cosmic_anchor_formalization_v1.py",
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    MKMLIFE_ANCHOR_DIR.mkdir(parents=True, exist_ok=True)
    for spec in PILOT_SPECS:
        src = OUT_DIR / f"{spec['file_stem']}.json"
        dst = MKMLIFE_ANCHOR_DIR / f"{spec['file_stem']}.json"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    MKMLIFE_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    manifest = build_all()
    print(f"WROTE: {OUT_DIR} ({manifest['anchor_count']} anchors)")
    print(f"WROTE: {MANIFEST}")
    for stem, rel in manifest["paths"].items():
        print(f"  - {stem}: {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
