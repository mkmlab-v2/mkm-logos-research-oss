"""Windows DPAPI-backed local secret store for MKM Secure Agent Runtime V0.3.

Security boundary:
- Windows current-user DPAPI only (no LOCAL_MACHINE flag)
- secret material is never returned by MCP tools
- metadata and ciphertext are stored locally under MKM_AGENT_STATE
- this module does not inject secrets into subprocesses or browsers
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


class SecretStoreError(RuntimeError):
    pass


CRYPTPROTECT_UI_FORBIDDEN = 0x1


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_windows() -> None:
    if os.name != "nt":
        raise SecretStoreError("Windows DPAPI provider requires Windows")


def _input_blob(data: bytes) -> tuple[DATA_BLOB, Any]:
    if not data:
        buf = ctypes.create_string_buffer(b"\x00", 1)
        return DATA_BLOB(0, ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))), buf
    buf = ctypes.create_string_buffer(data, len(data))
    return DATA_BLOB(
        len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))
    ), buf


def _protect(data: bytes, *, description: str) -> bytes:
    _require_windows()
    in_blob, _keepalive = _input_blob(data)
    out_blob = DATA_BLOB()
    crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        wintypes.LPCWSTR,
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL

    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        description,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise SecretStoreError(f"CryptProtectData failed: {ctypes.get_last_error()}")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))


def _unprotect(ciphertext: bytes) -> bytes:
    _require_windows()
    in_blob, _keepalive = _input_blob(ciphertext)
    out_blob = DATA_BLOB()
    description_ptr = wintypes.LPWSTR()
    crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL

    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        ctypes.byref(description_ptr),
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise SecretStoreError(f"CryptUnprotectData failed: {ctypes.get_last_error()}")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)
        if description_ptr:
            kernel32.LocalFree(ctypes.cast(description_ptr, ctypes.c_void_p))


def dpapi_protect_bytes(data: bytes, *, description: str) -> bytes:
    """Protect arbitrary bounded local bytes with current-user Windows DPAPI."""
    return _protect(data, description=description)


def dpapi_unprotect_bytes(ciphertext: bytes) -> bytes:
    """Unprotect bytes for trusted local code only."""
    return _unprotect(ciphertext)


def _normalize_handle(handle: str) -> str:
    handle = handle.strip()
    if not handle.startswith("secret://"):
        raise SecretStoreError("handle must start with secret://")
    suffix = handle[len("secret://"):]
    if not suffix or any(ch.isspace() for ch in suffix):
        raise SecretStoreError("invalid secret handle")
    if any(ord(ch) < 32 for ch in suffix):
        raise SecretStoreError("invalid secret handle")
    return handle


def _file_id(handle: str) -> str:
    return hashlib.sha256(handle.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SecretMetadata:
    handle: str
    service: str
    label: str
    created_at: str
    updated_at: str
    provider: str
    secret_material_exposed: bool = False


class DPAPISecretStore:
    def __init__(self, state_dir: Path):
        _require_windows()
        self.root = state_dir.expanduser().resolve() / "secrets"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, handle: str) -> Path:
        return self.root / f"{_file_id(_normalize_handle(handle))}.json"

    def _atomic_write(self, path: Path, payload: dict[str, Any]) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=".mkm-secret-", suffix=".tmp", dir=path.parent)
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

    def set_secret(
        self,
        handle: str,
        secret: bytes,
        *,
        service: str,
        label: str = "",
    ) -> SecretMetadata:
        handle = _normalize_handle(handle)
        if not secret:
            raise SecretStoreError("secret must not be empty")
        service = service.strip()
        if not service:
            raise SecretStoreError("service must not be empty")
        path = self._path(handle)
        old = None
        if path.is_file():
            old = json.loads(path.read_text(encoding="utf-8-sig"))
        created = old.get("created_at") if old else _now()
        updated = _now()
        ciphertext = _protect(
            bytes(secret),
            description=f"MKM Secure Agent Runtime:{handle}",
        )
        payload = {
            "schema": "mkm_dpapi_secret_v0_3",
            "handle": handle,
            "service": service,
            "label": label.strip(),
            "created_at": created,
            "updated_at": updated,
            "provider": "WINDOWS_DPAPI_CURRENT_USER",
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        }
        self._atomic_write(path, payload)
        return SecretMetadata(
            handle=handle,
            service=service,
            label=label.strip(),
            created_at=created,
            updated_at=updated,
            provider="WINDOWS_DPAPI_CURRENT_USER",
        )

    def metadata(self, handle: str) -> SecretMetadata:
        payload = self._load(handle)
        return SecretMetadata(
            handle=payload["handle"],
            service=payload["service"],
            label=payload.get("label", ""),
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            provider=payload["provider"],
        )

    def _load(self, handle: str) -> dict[str, Any]:
        path = self._path(handle)
        if not path.is_file():
            raise SecretStoreError("secret handle not found")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if payload.get("handle") != _normalize_handle(handle):
            raise SecretStoreError("secret metadata handle mismatch")
        if payload.get("provider") != "WINDOWS_DPAPI_CURRENT_USER":
            raise SecretStoreError("unsupported secret provider")
        return payload

    def materialize_for_local_consumer(self, handle: str) -> bytearray:
        """Decrypt for trusted local code only. Never expose this through MCP."""
        payload = self._load(handle)
        try:
            ciphertext = base64.b64decode(payload["ciphertext_b64"], validate=True)
        except Exception as exc:
            raise SecretStoreError("invalid secret ciphertext encoding") from exc
        return bytearray(_unprotect(ciphertext))

    @staticmethod
    def wipe(buffer: bytearray) -> None:
        for i in range(len(buffer)):
            buffer[i] = 0

    def verify(self, handle: str) -> dict[str, Any]:
        material = self.materialize_for_local_consumer(handle)
        try:
            length = len(material)
            digest = hashlib.sha256(material).hexdigest()
            return {
                "ok": True,
                "bytes": length,
                "sha256": digest,
                "secret_material_exposed": False,
            }
        finally:
            self.wipe(material)

    def list_metadata(self) -> list[SecretMetadata]:
        rows: list[SecretMetadata] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                rows.append(SecretMetadata(
                    handle=payload["handle"],
                    service=payload["service"],
                    label=payload.get("label", ""),
                    created_at=payload["created_at"],
                    updated_at=payload["updated_at"],
                    provider=payload["provider"],
                ))
            except Exception:
                continue
        return rows

    def remove(self, handle: str) -> bool:
        path = self._path(handle)
        if not path.exists():
            return False
        path.unlink()
        return True
