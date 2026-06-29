#!/usr/bin/env python3
"""Validate post-it pointer contracts (31k / 41k / zone) — v0 research governance."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "docs/final/schemas/postit_pointer_v1.schema.json"
DEFAULT_JSON_FIXTURES = [
    ROOT / "docs/final/artifacts/fixtures/postit_pointer_v1.example.json",
]
DEFAULT_REPORT = ROOT / "reports/postit_pointer_validation_v1_latest.json"

LOGOS_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
ATOMS_SUMMARY = (
    ROOT / "reports/constitution/btrack_pilot/original_language_master_atoms_summary_latest.json"
)
ZONE_SHARDS_GLOB = "zone_*.json"

V2_TARGETS = [
    ROOT / "scripts/train_mkm_prophecy_lora_windows_fallback_v1.py",
    ROOT / "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py",
    ROOT / "scripts/Run-MyeongriQwenSafeManagedPipeline_v1.ps1",
    ROOT / "scripts/Register-MyeongriQwenSafeManagedTask_v1.ps1",
]

REQUIRED_V2_TOP = {"owner", "lane", "status", "evidence_mode", "metric_scope", "lifecycle"}
REQUIRED_METRIC_SCOPE = {"raw_metric", "repair_metric", "delta"}
REQUIRED_LIFECYCLE = {"phase", "replacement"}

VERSE_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9.]*\.\d+\.\d+$")
ATOM_ID_PATTERN = re.compile(r"^(greek|hebrew|other)::.+$")
ZONE_ID_PATTERN = re.compile(r"^zone_[a-z0-9_]+$")
SHARD_REL_PATTERN = re.compile(r"^codebook/shards/zone_[a-z0-9_]+\.json$")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_postit_v2_marker(text: str) -> dict[str, Any] | None:
    m = re.search(r"postit_v2:\s*(\{.+\})", text)
    if not m:
        return None
    return json.loads(m.group(1))


def load_denominators(root: Path) -> dict[str, Any]:
    zones: dict[str, str] = {}
    shards_dir = root / "codebook" / "shards"
    for path in sorted(shards_dir.glob(ZONE_SHARDS_GLOB)):
        data = _load_json(path)
        shard_id = str(data.get("shard_id", ""))
        if shard_id:
            rel = path.relative_to(root).as_posix()
            zones[shard_id] = rel

    logos: dict[str, Any] = {}
    if LOGOS_MANIFEST.is_file():
        manifest = _load_json(LOGOS_MANIFEST)
        logos = {
            "manifest_rel": LOGOS_MANIFEST.relative_to(root).as_posix(),
            "verse_count": manifest.get("verse_count"),
            "verse_id_pattern": r"^[A-Za-z][A-Za-z0-9.]*\.\d+\.\d+$",
        }

    lexicon: dict[str, Any] = {}
    if ATOMS_SUMMARY.is_file():
        summary = _load_json(ATOMS_SUMMARY)
        stats = summary.get("stats") if isinstance(summary.get("stats"), dict) else {}
        lexicon = {
            "summary_rel": ATOMS_SUMMARY.relative_to(root).as_posix(),
            "unique_master_atoms": stats.get("unique_master_atoms"),
            "atom_id_pattern": r"^(greek|hebrew|other)::.+$",
        }

    return {
        "schema": "postit_pointer_denominators_v1",
        "zone_shards": zones,
        "logos_31k": logos,
        "lexicon_41k": lexicon,
    }


def _validate_v2_marker_shape(marker: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    missing_top = sorted(REQUIRED_V2_TOP - set(marker.keys()))
    if missing_top:
        errs.append(f"missing top keys: {missing_top}")

    ms = marker.get("metric_scope")
    if not isinstance(ms, dict):
        errs.append("metric_scope must be object")
    else:
        missing_ms = sorted(REQUIRED_METRIC_SCOPE - set(ms.keys()))
        if missing_ms:
            errs.append(f"missing metric_scope keys: {missing_ms}")

    lc = marker.get("lifecycle")
    if not isinstance(lc, dict):
        errs.append("lifecycle must be object")
    else:
        missing_lc = sorted(REQUIRED_LIFECYCLE - set(lc.keys()))
        if missing_lc:
            errs.append(f"missing lifecycle keys: {missing_lc}")
    return errs


def _validate_pointer_object(
    pointer: Any,
    *,
    root: Path,
    denoms: dict[str, Any],
    context: str,
) -> list[str]:
    if not isinstance(pointer, dict):
        return [f"{context}: pointer must be object"]

    errs: list[str] = []
    zone_ids = denoms.get("zone_shards") or {}
    if not isinstance(zone_ids, dict):
        zone_ids = {}

    zone_id = pointer.get("zone_id")
    verse_id = pointer.get("verse_id")
    atom_id = pointer.get("atom_id")
    shard_rel = pointer.get("codebook_shard_rel")

    known_keys = {"zone_id", "verse_id", "atom_id", "codebook_shard_rel"}
    extra = sorted(set(pointer.keys()) - known_keys)
    if extra:
        errs.append(f"{context}: unknown pointer keys: {extra}")

    if not any(v for v in (zone_id, verse_id, atom_id, shard_rel) if v):
        errs.append(f"{context}: pointer must set at least one reference field")

    if zone_id is not None:
        z = str(zone_id)
        if not ZONE_ID_PATTERN.match(z):
            errs.append(f"{context}: invalid zone_id pattern: {z!r}")
        elif z not in zone_ids:
            errs.append(f"{context}: zone_id not in codebook/shards: {z!r}")

    if verse_id is not None:
        v = str(verse_id)
        if not VERSE_ID_PATTERN.match(v):
            errs.append(f"{context}: invalid verse_id pattern: {v!r}")

    if atom_id is not None:
        a = str(atom_id)
        if not ATOM_ID_PATTERN.match(a):
            errs.append(f"{context}: invalid atom_id pattern: {a!r}")

    if shard_rel is not None:
        rel = str(shard_rel)
        if not SHARD_REL_PATTERN.match(rel):
            errs.append(f"{context}: invalid codebook_shard_rel: {rel!r}")
        else:
            abs_path = root / rel
            if not abs_path.is_file():
                errs.append(f"{context}: codebook_shard_rel missing on disk: {rel}")
            else:
                shard = _load_json(abs_path)
                sid = str(shard.get("shard_id", ""))
                if zone_id is not None and sid and str(zone_id) != sid:
                    errs.append(
                        f"{context}: zone_id {zone_id!r} != shard file shard_id {sid!r}"
                    )
                if sid and sid not in zone_ids:
                    errs.append(f"{context}: shard_id not registered: {sid!r}")

    return errs


def _validate_with_jsonschema(instance: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return []

    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError as exc:
        return [str(exc.message)]
    return []


def validate_pointer_document(
    path: Path,
    *,
    root: Path,
    denoms: dict[str, Any],
    schema: dict[str, Any] | None,
) -> list[str]:
    if not path.is_file():
        return [f"missing file: {path}"]

    doc = _load_json(path)
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    errs: list[str] = []

    if schema is not None:
        errs.extend(_validate_with_jsonschema(doc, schema))

    pointer = doc.get("pointer")
    errs.extend(
        _validate_pointer_object(pointer, root=root, denoms=denoms, context=rel)
    )
    return errs


def validate_v2_file(path: Path, *, root: Path, denoms: dict[str, Any]) -> list[str]:
    if not path.is_file():
        return [f"missing file: {path}"]

    text = path.read_text(encoding="utf-8-sig")
    rel = path.relative_to(root).as_posix()
    marker = _extract_postit_v2_marker(text)
    if marker is None:
        return [f"{rel}: missing postit_v2 marker"]

    errs = [f"{rel}: {e}" for e in _validate_v2_marker_shape(marker)]
    pointer = marker.get("pointer")
    if pointer is not None:
        errs.extend(
            _validate_pointer_object(pointer, root=root, denoms=denoms, context=rel)
        )
    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="append",
        default=[],
        help="Additional postit_pointer_v1 JSON documents to validate",
    )
    parser.add_argument(
        "--skip-v2",
        action="store_true",
        help="Skip embedded postit_v2 marker checks on managed pipeline files",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help="Write validation report JSON (default: reports/postit_pointer_validation_v1_latest.json)",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print report to stdout only; do not write report file",
    )
    args = parser.parse_args()

    denoms = load_denominators(ROOT)
    schema: dict[str, Any] | None = None
    if SCHEMA_PATH.is_file():
        schema = _load_json(SCHEMA_PATH)

    failures: list[dict[str, Any]] = []
    checked: list[str] = []

    json_paths = [Path(p) for p in args.json] + DEFAULT_JSON_FIXTURES
    for path in json_paths:
        checked.append(str(path))
        for err in validate_pointer_document(path, root=ROOT, denoms=denoms, schema=schema):
            failures.append({"target": str(path), "error": err})

    if not args.skip_v2:
        for path in V2_TARGETS:
            checked.append(str(path))
            for err in validate_v2_file(path, root=ROOT, denoms=denoms):
                failures.append({"target": str(path), "error": err})

    out = {
        "schema": "postit_pointer_validation_v1",
        "validated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "b_track_research",
        "denominators": denoms,
        "checked_targets": checked,
        "ok": len(failures) == 0,
        "failure_count": len(failures),
        "failures": failures,
        "notes": (
            "v0 ingress pointer validator; extends postit_v2 with optional pointer block. "
            "Not Track A promotion or enterprise firewall product certification."
        ),
    }

    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)

    if not args.stdout_only:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")

    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
