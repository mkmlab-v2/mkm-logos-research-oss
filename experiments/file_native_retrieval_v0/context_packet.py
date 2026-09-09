"""Bounded, source-verifiable Context Packet V1.

Packets carry locators and expected hashes only. Verification is always computed
by the receiver after reopening the current source beneath an approved root.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
from typing import Any, Mapping

SCHEMA_VERSION = "mkm_context_packet_v1"
VERIFY_BEFORE_EVIDENCE = "VERIFY_BEFORE_EVIDENCE"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class PacketValidationError(ValueError):
    """Validation failure carrying the receiver-visible status class."""

    def __init__(self, message: str, *, status: str = "INVALID_PACKET") -> None:
        super().__init__(message)
        self.status = status


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PacketValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _canonical_relative_path(value: Any) -> str:
    raw = _nonempty_string(value, "source.path")
    if PurePosixPath(raw).is_absolute() or PureWindowsPath(raw).is_absolute():
        raise PacketValidationError("absolute source paths are forbidden", status="PATH_ESCAPE")
    normalized = raw.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise PacketValidationError(
            "source path must be a canonical relative path", status="PATH_ESCAPE"
        )
    return "/".join(parts)


def _canonical_sha256(value: Any) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise PacketValidationError(
            "expected_sha256 must be exactly 64 hexadecimal characters"
        )
    return value.lower()


def _optional_nonempty_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _nonempty_string(value, field)


@dataclass(frozen=True)
class SourceCoordinate:
    path: str
    expected_sha256: str
    symbol: str | None = None
    line_start: int | None = None
    line_end: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _canonical_relative_path(self.path))
        object.__setattr__(
            self, "expected_sha256", _canonical_sha256(self.expected_sha256)
        )
        object.__setattr__(
            self, "symbol", _optional_nonempty_string(self.symbol, "source.symbol")
        )
        if (self.line_start is None) != (self.line_end is None):
            raise PacketValidationError(
                "line_start and line_end must be supplied together"
            )
        if self.line_start is not None:
            if type(self.line_start) is not int or type(self.line_end) is not int:
                raise PacketValidationError("line span values must be integers")
            if self.line_start < 1 or self.line_end < self.line_start:
                raise PacketValidationError(
                    "line span must satisfy 1 <= line_start <= line_end"
                )

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "SourceCoordinate":
        if not isinstance(row, Mapping):
            raise PacketValidationError("each source must be an object")
        if "source_verified" in row:
            raise PacketValidationError("source_verified is receiver output only")
        allowed = {"path", "expected_sha256", "symbol", "line_start", "line_end"}
        unknown = set(row) - allowed
        if unknown:
            raise PacketValidationError(f"unknown source fields: {sorted(unknown)}")
        missing = {"path", "expected_sha256"} - set(row)
        if missing:
            raise PacketValidationError(f"missing source fields: {sorted(missing)}")
        return cls(
            path=row["path"],
            expected_sha256=row["expected_sha256"],
            symbol=row.get("symbol"),
            line_start=row.get("line_start"),
            line_end=row.get("line_end"),
        )

    def coordinate_key(self) -> tuple[str, str, int | None, int | None]:
        return (self.path, self.symbol or "", self.line_start, self.line_end)

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "path": self.path,
            "expected_sha256": self.expected_sha256,
        }
        if self.symbol is not None:
            row["symbol"] = self.symbol
        if self.line_start is not None:
            row["line_start"] = self.line_start
            row["line_end"] = self.line_end
        return row


@dataclass(frozen=True)
class ContextPacket:
    packet_id: str
    repo_id: str
    revision: str
    sources: tuple[SourceCoordinate, ...]
    schema_version: str = SCHEMA_VERSION
    verification_policy: str = VERIFY_BEFORE_EVIDENCE

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "packet_id", _nonempty_string(self.packet_id, "packet_id")
        )
        object.__setattr__(self, "repo_id", _nonempty_string(self.repo_id, "repo_id"))
        object.__setattr__(
            self, "revision", _nonempty_string(self.revision, "revision")
        )
        if self.schema_version != SCHEMA_VERSION:
            raise PacketValidationError(
                f"schema_version must equal {SCHEMA_VERSION!r}"
            )
        if self.verification_policy != VERIFY_BEFORE_EVIDENCE:
            raise PacketValidationError("unknown verification_policy")
        sources = tuple(self.sources)
        if not sources:
            raise PacketValidationError(
                "sources must contain at least one source coordinate"
            )
        keys = [source.coordinate_key() for source in sources]
        if len(set(keys)) != len(keys):
            raise PacketValidationError("duplicate source coordinate")
        object.__setattr__(self, "sources", sources)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ContextPacket":
        if not isinstance(payload, Mapping):
            raise PacketValidationError("packet must be an object")
        allowed = {
            "schema_version",
            "packet_id",
            "repo_id",
            "revision",
            "sources",
            "verification_policy",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise PacketValidationError(f"unknown packet fields: {sorted(unknown)}")
        missing = allowed - set(payload)
        if missing:
            raise PacketValidationError(f"missing packet fields: {sorted(missing)}")
        rows = payload["sources"]
        if not isinstance(rows, list):
            raise PacketValidationError("sources must be an array")
        return cls(
            schema_version=payload["schema_version"],
            packet_id=payload["packet_id"],
            repo_id=payload["repo_id"],
            revision=payload["revision"],
            sources=tuple(SourceCoordinate.from_dict(row) for row in rows),
            verification_policy=payload["verification_policy"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "packet_id": self.packet_id,
            "repo_id": self.repo_id,
            "revision": self.revision,
            "sources": [
                source.to_dict()
                for source in sorted(
                    self.sources, key=lambda item: item.coordinate_key()
                )
            ],
            "verification_policy": self.verification_policy,
        }


def canonical_serialize(packet: ContextPacket | Mapping[str, Any]) -> str:
    """Return deterministic UTF-8 JSON text without runtime verification state."""

    parsed = packet if isinstance(packet, ContextPacket) else ContextPacket.from_dict(packet)
    return json.dumps(
        parsed.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _resolve_under_root(root: Path, relative: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise PacketValidationError(
            "source path escapes approved root", status="PATH_ESCAPE"
        ) from exc
    return candidate


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repo_head(root: Path) -> str | None:
    """Best-effort provenance check; per-file SHA remains the integrity gate."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    head = completed.stdout.strip()
    if completed.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", head):
        return head.lower()
    return None


def _failure_result(
    status: str, *, message: str, packet_id: str | None = None
) -> dict[str, Any]:
    return {
        "status": status,
        "evidence_eligible": False,
        "packet_id": packet_id,
        "error": message,
        "sources": [],
    }


def rehydrate_and_verify(
    packet: ContextPacket | Mapping[str, Any], root: str | Path
) -> dict[str, Any]:
    """Reopen current sources and return content only after exact SHA verification.

    A matching repository revision is provenance metadata, not a substitute for
    source hashing. Any source or revision failure keeps evidence_eligible false.
    """

    try:
        parsed = (
            packet
            if isinstance(packet, ContextPacket)
            else ContextPacket.from_dict(packet)
        )
    except PacketValidationError as exc:
        packet_id = packet.get("packet_id") if isinstance(packet, Mapping) else None
        return _failure_result(
            exc.status,
            message=str(exc),
            packet_id=packet_id if isinstance(packet_id, str) else None,
        )

    root_path = Path(root)
    observed_revision = _repo_head(root_path)
    revision_status = "NOT_CHECKED"
    if observed_revision is not None:
        revision_status = (
            "MATCH" if observed_revision == parsed.revision.lower() else "MISMATCH"
        )

    source_results: list[dict[str, Any]] = []
    first_failure: str | None = None
    for source in sorted(parsed.sources, key=lambda item: item.coordinate_key()):
        base = {
            "path": source.path,
            "expected_sha256": source.expected_sha256,
            "symbol": source.symbol,
            "line_start": source.line_start,
            "line_end": source.line_end,
        }
        try:
            path = _resolve_under_root(root_path, source.path)
        except PacketValidationError as exc:
            row = {
                **base,
                "status": exc.status,
                "source_verified": False,
                "error": str(exc),
            }
            source_results.append(row)
            first_failure = first_failure or exc.status
            continue
        if not path.is_file():
            row = {**base, "status": "MISSING_SOURCE", "source_verified": False}
            source_results.append(row)
            first_failure = first_failure or "MISSING_SOURCE"
            continue

        data = path.read_bytes()
        observed_sha = _sha256_bytes(data)
        if observed_sha != source.expected_sha256:
            row = {
                **base,
                "status": "HASH_MISMATCH",
                "source_verified": False,
                "observed_sha256": observed_sha,
            }
            source_results.append(row)
            first_failure = first_failure or "HASH_MISMATCH"
            continue

        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            row = {
                **base,
                "status": "INVALID_PACKET",
                "source_verified": False,
                "observed_sha256": observed_sha,
                "error": "verified source is not UTF-8 text",
            }
            source_results.append(row)
            first_failure = first_failure or "INVALID_PACKET"
            continue

        returned_scope = "FULL_SOURCE"
        content = text
        if source.line_start is not None:
            lines = text.splitlines(keepends=True)
            if source.line_end is None or source.line_end > len(lines):
                row = {
                    **base,
                    "status": "INVALID_PACKET",
                    "source_verified": False,
                    "observed_sha256": observed_sha,
                    "error": "verified line span exceeds source length",
                }
                source_results.append(row)
                first_failure = first_failure or "INVALID_PACKET"
                continue
            content = "".join(lines[source.line_start - 1 : source.line_end])
            returned_scope = "SPAN"

        source_results.append(
            {
                **base,
                "status": "VERIFIED",
                "source_verified": True,
                "observed_sha256": observed_sha,
                "returned_scope": returned_scope,
                "content": content,
            }
        )

    overall_status = first_failure or (
        "REVISION_MISMATCH" if revision_status == "MISMATCH" else "VERIFIED"
    )
    return {
        "status": overall_status,
        "evidence_eligible": overall_status == "VERIFIED",
        "schema_version": parsed.schema_version,
        "packet_id": parsed.packet_id,
        "repo_id": parsed.repo_id,
        "revision": parsed.revision,
        "observed_revision": observed_revision,
        "revision_status": revision_status,
        "verification_policy": parsed.verification_policy,
        "sources": source_results,
    }
