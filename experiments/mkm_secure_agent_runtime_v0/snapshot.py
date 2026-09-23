"""DPAPI-encrypted rollback snapshots for MKM Secure Agent Runtime V0.4."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any
import uuid

from secrets_dpapi import dpapi_protect_bytes, dpapi_unprotect_bytes


class SnapshotError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class SnapshotMetadata:
    snapshot_id: str
    target_path: str
    existed_before: bool
    before_sha256: str | None
    bytes_before: int
    created_at: str
    provider: str
    encrypted: bool


class SnapshotStore:
    def __init__(self, state_dir: Path, *, protected_roots: list[Path]):
        self.root = state_dir.expanduser().resolve() / "snapshots"
        self.root.mkdir(parents=True, exist_ok=True)
        self.protected_roots = [p.expanduser().resolve() for p in protected_roots]

    def _validate_target(self, target: Path) -> Path:
        resolved = target.expanduser().resolve(strict=False)
        if not any(_is_relative_to(resolved, root) for root in self.protected_roots):
            raise SnapshotError("snapshot target outside approved roots")
        return resolved

    def _meta_path(self, snapshot_id: str) -> Path:
        if not snapshot_id.startswith("snap_"):
            raise SnapshotError("invalid snapshot id")
        return self.root / f"{snapshot_id}.json"

    def _blob_path(self, snapshot_id: str) -> Path:
        return self.root / f"{snapshot_id}.bin"

    def _atomic_bytes(self, path: Path, data: bytes) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=".mkm-snapshot-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        finally:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass

    def _atomic_json(self, path: Path, payload: dict[str, Any]) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=".mkm-snapshot-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        finally:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass

    def capture(self, target: Path) -> SnapshotMetadata:
        target = self._validate_target(target)
        snapshot_id = "snap_" + uuid.uuid4().hex
        existed = target.is_file()
        before = target.read_bytes() if existed else b""
        before_hash = _sha256(before) if existed else None

        if existed:
            protected = dpapi_protect_bytes(
                before,
                description=f"MKM rollback snapshot:{snapshot_id}",
            )
            self._atomic_bytes(self._blob_path(snapshot_id), protected)

        meta = SnapshotMetadata(
            snapshot_id=snapshot_id,
            target_path=str(target),
            existed_before=existed,
            before_sha256=before_hash,
            bytes_before=len(before),
            created_at=_now(),
            provider="WINDOWS_DPAPI_CURRENT_USER",
            encrypted=True,
        )
        self._atomic_json(self._meta_path(snapshot_id), asdict(meta))
        return meta

    def metadata(self, snapshot_id: str) -> SnapshotMetadata:
        path = self._meta_path(snapshot_id)
        if not path.is_file():
            raise SnapshotError("snapshot not found")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return SnapshotMetadata(**payload)

    def restore(self, snapshot_id: str) -> dict[str, Any]:
        meta = self.metadata(snapshot_id)
        target = self._validate_target(Path(meta.target_path))

        if meta.existed_before:
            blob_path = self._blob_path(snapshot_id)
            if not blob_path.is_file():
                raise SnapshotError("encrypted snapshot blob missing")
            before = dpapi_unprotect_bytes(blob_path.read_bytes())
            if _sha256(before) != meta.before_sha256:
                raise SnapshotError("snapshot plaintext hash mismatch")
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(prefix=".mkm-restore-", suffix=".tmp", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(before)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_name, target)
            finally:
                try:
                    Path(tmp_name).unlink(missing_ok=True)
                except OSError:
                    pass
            return {
                "snapshot_id": snapshot_id,
                "restored": True,
                "action": "RESTORE_BYTES",
                "after_sha256": _sha256(before),
            }

        existed_now = target.exists()
        if existed_now:
            if target.is_dir():
                raise SnapshotError("refuse to delete directory during rollback")
            target.unlink()
        return {
            "snapshot_id": snapshot_id,
            "restored": True,
            "action": "REMOVE_NEW_FILE" if existed_now else "NOOP_ABSENT",
            "after_sha256": None,
        }

    def list_metadata(self) -> list[SnapshotMetadata]:
        rows: list[SnapshotMetadata] = []
        for path in sorted(self.root.glob("snap_*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                rows.append(SnapshotMetadata(**payload))
            except Exception:
                continue
        return rows
