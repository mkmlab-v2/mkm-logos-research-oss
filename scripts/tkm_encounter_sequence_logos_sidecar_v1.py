#!/usr/bin/env python3
"""TKM encounter_sequence L6 logos_ref sidecar — cosmic anchor batch [HYPO][NON_GATING]."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
BATCH_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1"
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1_manifest_latest.json"
DEFAULT_FILE_STEM = "seed"
KERNEL_RECIPE_ID = "gematria_bridge_v1"

REF_TOKEN_MOTIF_MAP: dict[str, str] = {
    "ENC-PARK-GEUMJA-2026": "shepherd",
    "PARK-GEUMJA-SENIOR-2026-001": "shepherd",
    "ENC-PHYSICIAN-GOLD-P21-01": "lamb",
    "ENC-DEMO-2026-0618-01": "seed",
}

_registry_cache: dict[str, Any] | None = None


def latest_records_by_sequence_id(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_seq: dict[str, dict[str, Any]] = {}
    for row in records:
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if seq_id:
            by_seq[seq_id] = row
    return list(by_seq.values())


def _load_registry() -> dict[str, Any]:
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache
    if not REGISTRY.is_file():
        _registry_cache = {"entries": []}
        return _registry_cache
    _registry_cache = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    return _registry_cache


def enabled_entries() -> list[dict[str, Any]]:
    reg = _load_registry()
    entries = reg.get("entries") if isinstance(reg.get("entries"), list) else []
    return [e for e in entries if isinstance(e, dict) and e.get("enabled") is True]


def entry_by_file_stem(stem: str) -> dict[str, Any] | None:
    for entry in enabled_entries():
        if str(entry.get("file_stem") or "") == stem:
            return entry
    return None


def anchor_relpath(file_stem: str) -> str:
    return f"docs/final/artifacts/logos_cosmic_anchor_batch_v1/{file_stem}.json"


def _ref_token(record: dict[str, Any]) -> str:
    enc = record.get("encounter") if isinstance(record.get("encounter"), dict) else {}
    return str(enc.get("ref_token") or "")


def resolve_motif_file_stem(record: dict[str, Any], *, capture: dict[str, Any] | None = None) -> str:
    if capture:
        meta = capture.get("meta") if isinstance(capture.get("meta"), dict) else {}
        explicit = meta.get("logos_motif_file_stem") or meta.get("cosmic_anchor_file_stem")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()
        anchor_id = meta.get("logos_anchor_id")
        if isinstance(anchor_id, str) and anchor_id.strip():
            for entry in enabled_entries():
                if str(entry.get("anchor_id") or "") == anchor_id.strip():
                    return str(entry.get("file_stem") or DEFAULT_FILE_STEM)
    token = _ref_token(record)
    if token in REF_TOKEN_MOTIF_MAP:
        return REF_TOKEN_MOTIF_MAP[token]
    entries = enabled_entries()
    if not entries:
        return DEFAULT_FILE_STEM
    idx = abs(hash(token or "default")) % len(entries)
    return str(entries[idx].get("file_stem") or DEFAULT_FILE_STEM)


def load_anchor(file_stem: str) -> dict[str, Any] | None:
    path = ROOT / anchor_relpath(file_stem)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_sidecar(
    record: dict[str, Any],
    *,
    capture: dict[str, Any] | None = None,
    motif_file_stem: str | None = None,
) -> dict[str, Any] | None:
    stem = motif_file_stem or resolve_motif_file_stem(record, capture=capture)
    anchor = load_anchor(stem)
    if not anchor:
        stem = DEFAULT_FILE_STEM
        anchor = load_anchor(stem)
    if not anchor:
        return None
    entry = entry_by_file_stem(stem)
    fact_lock = anchor.get("fact_lock") if isinstance(anchor.get("fact_lock"), dict) else {}
    verse_refs = anchor.get("verse_refs") if isinstance(anchor.get("verse_refs"), list) else []
    return {
        "hypothesis_tier": "B",
        "non_gating": True,
        "logos_cosmic_anchor_ref": anchor_relpath(stem).replace("\\", "/"),
        "anchor_id": str(anchor.get("anchor_id") or (entry or {}).get("anchor_id") or ""),
        "motif_file_stem": stem,
        "verse_refs": verse_refs,
        "kernel_recipe_id": KERNEL_RECIPE_ID,
        "registry_schema": "logos_motif_registry_top100_v1",
        "fact_lock_non_gating": fact_lock.get("non_gating") is True,
        "sasang_lens_separation_ok": True,
        "myeongni_lens_separation_ok": True,
        "note_ko": "[HYPO][NON_GATING] L6 Logos cosmic anchor; 사상·명리 constitution 합선 금지.",
    }


def attach_sidecar(
    record: dict[str, Any],
    *,
    capture: dict[str, Any] | None = None,
    motif_file_stem: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    out = dict(record)
    if out.get("l6_logos_ref") and not force:
        return out
    sidecar = build_sidecar(out, capture=capture, motif_file_stem=motif_file_stem)
    if sidecar:
        out["l6_logos_ref"] = sidecar
    return out


def validate_logos_lens_separation(record: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    sidecar = record.get("l6_logos_ref")
    if not isinstance(sidecar, dict):
        return errs
    if sidecar.get("non_gating") is not True:
        errs.append("l6_logos_ref.non_gating must be true")
    if sidecar.get("sasang_lens_separation_ok") is not True:
        errs.append("l6_logos_ref.sasang_lens_separation_ok must be true")
    forbidden = (
        "constitution",
        "final_ai_constitution",
        "sasang_label",
        "myeongni_report_ref",
        "cross_check_status",
    )
    for key in forbidden:
        if key in sidecar:
            errs.append(f"l6_logos_ref must not contain {key}")
    ref = str(sidecar.get("logos_cosmic_anchor_ref") or "")
    if ref and not (ROOT / ref).is_file():
        errs.append(f"missing anchor file: {ref}")
    return errs
