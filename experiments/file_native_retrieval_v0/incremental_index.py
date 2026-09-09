"""Persistent bounded incremental manifest for file-native retrieval records.

The size + mtime_ns fast path is a performance optimization only. It is not
cryptographic proof that file bytes are unchanged. Use full_rescan=True to
rehash/rebuild every approved source and re-establish byte-integrity evidence.

When the approved path set changes, stat-reused records may have only their
literal-path relation metadata refreshed. Removing targets needs no source-body
read; adding targets reads reused source text only to test the newly approved
literal target paths. These rows remain counted as reused and are not rehashed.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable

from experiments.file_native_retrieval_v0 import retrieval

SCHEMA_VERSION = "mkm_file_native_incremental_index_v0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_LITERAL_PATH_REFERENCE = "literal_path_reference"


class ManifestError(ValueError):
    """Raised when a persisted incremental manifest is malformed."""


@dataclass(frozen=True)
class UpdateCounters:
    reused_count: int
    rebuilt_count: int
    removed_count: int
    total_count: int

    def as_dict(self) -> dict[str, int]:
        return {
            "reused_count": self.reused_count,
            "rebuilt_count": self.rebuilt_count,
            "removed_count": self.removed_count,
            "total_count": self.total_count,
        }


def _canonical_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("approved paths must be non-empty relative strings")
    raw = value.strip().replace("\\", "/")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:/", raw):
        raise ValueError(f"absolute path is not allowed: {value}")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"path escape/non-canonical path is not allowed: {value}")
    return "/".join(parts)


def _resolve_approved(root: Path, relative: str) -> Path:
    canonical = _canonical_relative_path(relative)
    root_resolved = root.resolve()
    path = (root_resolved / canonical).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"path escapes approved root: {relative}") from exc
    return path


def _validate_record(record: object, *, path: str, sha256: str) -> dict:
    if not isinstance(record, dict):
        raise ManifestError(f"record must be an object for {path}")
    if record.get("source_path") != path or record.get("id") != path:
        raise ManifestError(f"record identity mismatch for {path}")
    if record.get("source_hash") != sha256:
        raise ManifestError(f"record hash mismatch for {path}")
    return record


def validate_manifest(document: object) -> dict:
    if not isinstance(document, dict):
        raise ManifestError("manifest must be an object")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError("unsupported manifest schema_version")
    sources = document.get("sources")
    if not isinstance(sources, list):
        raise ManifestError("manifest sources must be a list")

    seen: set[str] = set()
    validated: list[dict] = []
    for row in sources:
        if not isinstance(row, dict):
            raise ManifestError("manifest source rows must be objects")
        try:
            path = _canonical_relative_path(row["path"])
            size = row["size"]
            mtime_ns = row["mtime_ns"]
            sha256 = row["sha256"]
            record = row["record"]
        except KeyError as exc:
            raise ManifestError(f"manifest source missing field: {exc.args[0]}") from exc
        if path in seen:
            raise ManifestError(f"duplicate manifest source: {path}")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ManifestError(f"invalid size for {path}")
        if not isinstance(mtime_ns, int) or isinstance(mtime_ns, bool) or mtime_ns < 0:
            raise ManifestError(f"invalid mtime_ns for {path}")
        if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
            raise ManifestError(f"invalid sha256 for {path}")
        _validate_record(record, path=path, sha256=sha256)
        seen.add(path)
        validated.append({"path": path, "size": size, "mtime_ns": mtime_ns, "sha256": sha256, "record": record})
    return {"schema_version": SCHEMA_VERSION, "sources": sorted(validated, key=lambda row: row["path"])}


def serialize_manifest(document: dict) -> str:
    validated = validate_manifest(document)
    return json.dumps(validated, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def load_manifest(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read/parse manifest: {path}") from exc
    return validate_manifest(parsed)


def atomic_write_manifest(path: Path, document: dict) -> None:
    payload = serialize_manifest(document).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as handle:
            temp_name = handle.name
            handle.write(payload)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def _read_source_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _refresh_reused_relations(
    root: Path,
    relative: str,
    old_record: dict,
    *,
    added_paths: frozenset[str],
    removed_paths: frozenset[str],
) -> dict:
    """Refresh only relation metadata after an approved-path-set delta.

    This deliberately does not hash the source. A source-body read happens only
    when there are newly approved target paths whose literal presence must be
    checked. Stat-reused rows remain reused for counter purposes.
    """
    record = dict(old_record)
    other_relations: list[dict] = []
    literal_targets: set[str] = set()
    for edge in record.get("relations", []):
        if edge.get("kind") != _LITERAL_PATH_REFERENCE:
            other_relations.append(dict(edge))
            continue
        target = edge.get("target")
        if isinstance(target, str) and target not in removed_paths:
            literal_targets.add(target)

    if added_paths:
        text = _read_source_text(_resolve_approved(root, relative))
        literal_targets.update(
            target
            for target in added_paths
            if target != relative and target in text
        )

    literal_relations = [
        {"target": target, "kind": _LITERAL_PATH_REFERENCE}
        for target in sorted(literal_targets)
    ]
    record["relations"] = literal_relations + other_relations
    return record


def _rebuild_record(root: Path, relative: str, all_paths: tuple[str, ...]) -> tuple[dict, os.stat_result]:
    record = retrieval.build(root, [relative])[0]
    path = _resolve_approved(root, relative)
    text = path.read_text(encoding="utf-8-sig")
    record = dict(record)
    record["relations"] = [
        {"target": target, "kind": _LITERAL_PATH_REFERENCE}
        for target in all_paths
        if target != relative and target in text
    ]
    stat = path.stat()
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if record.get("source_hash") != actual_sha:
        raise RuntimeError(f"source changed during rebuild: {relative}")
    return record, stat


def update_index(root: Path, approved_paths: Iterable[str], manifest_path: Path, *, on_corrupt: str = "error", full_rescan: bool = False) -> tuple[dict, UpdateCounters]:
    """Update and atomically persist a manifest for the complete approved path set."""
    if on_corrupt not in {"error", "full_rescan"}:
        raise ValueError("on_corrupt must be 'error' or 'full_rescan'")

    root = root.resolve()
    canonical_paths = tuple(sorted({_canonical_relative_path(path) for path in approved_paths}))
    for relative in canonical_paths:
        path = _resolve_approved(root, relative)
        if not path.is_file():
            raise FileNotFoundError(path)

    force_rescan = bool(full_rescan)
    try:
        previous = load_manifest(manifest_path)
    except ManifestError:
        if on_corrupt != "full_rescan":
            raise
        previous = None
        force_rescan = True

    previous_rows = {row["path"]: row for row in (previous or {}).get("sources", [])}
    previous_paths = frozenset(previous_rows)
    current_paths = frozenset(canonical_paths)
    added_paths = current_paths - previous_paths
    removed_paths = previous_paths - current_paths
    removed_count = len(removed_paths)

    sources: list[dict] = []
    reused_count = 0
    rebuilt_count = 0
    for relative in canonical_paths:
        path = _resolve_approved(root, relative)
        stat = path.stat()
        old = previous_rows.get(relative)
        if not force_rescan and old is not None and old["size"] == stat.st_size and old["mtime_ns"] == stat.st_mtime_ns:
            if added_paths or removed_paths:
                refreshed = dict(old)
                refreshed["record"] = _refresh_reused_relations(
                    root,
                    relative,
                    old["record"],
                    added_paths=added_paths,
                    removed_paths=removed_paths,
                )
                sources.append(refreshed)
            else:
                sources.append(old)
            reused_count += 1
            continue

        record, final_stat = _rebuild_record(root, relative, canonical_paths)
        sha256 = record["source_hash"]
        if not _SHA256_RE.fullmatch(sha256):
            raise RuntimeError(f"retrieval record emitted invalid sha256: {relative}")
        sources.append({"path": relative, "size": final_stat.st_size, "mtime_ns": final_stat.st_mtime_ns, "sha256": sha256, "record": record})
        rebuilt_count += 1

    document = validate_manifest({"schema_version": SCHEMA_VERSION, "sources": sources})
    atomic_write_manifest(manifest_path, document)
    counters = UpdateCounters(reused_count=reused_count, rebuilt_count=rebuilt_count, removed_count=removed_count, total_count=len(sources))
    return document, counters
