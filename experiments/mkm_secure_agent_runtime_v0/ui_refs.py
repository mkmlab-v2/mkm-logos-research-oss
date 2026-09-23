"""Ephemeral local UI observation references for MKM V0.6."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any
import uuid


class UIRefError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class UIRefStore:
    """Stores UI selectors outside model-accessible roots.

    The model receives only opaque ui_ref ids plus sanitized summaries.
    """

    def __init__(self, state_dir: Path, *, ttl_seconds: int = 180):
        self.root = state_dir.expanduser().resolve() / "ui_refs"
        self.root.mkdir(parents=True, exist_ok=True)
        if ttl_seconds < 30 or ttl_seconds > 900:
            raise UIRefError("ttl_seconds must be between 30 and 900")
        self.ttl_seconds = ttl_seconds

    def _path(self, ui_ref: str) -> Path:
        if not ui_ref.startswith("ui_") or any(
            ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for ch in ui_ref
        ):
            raise UIRefError("invalid ui_ref")
        return self.root / f"{ui_ref}.json"

    def _write(self, path: Path, payload: dict[str, Any]) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=".mkm-uiref-", suffix=".tmp", dir=path.parent)
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

    def issue(self, *, kind: str, selector: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        ui_ref = "ui_" + uuid.uuid4().hex
        payload = {
            "schema": "mkm_ui_ref_v0_6",
            "ui_ref": ui_ref,
            "kind": kind,
            "selector": selector,
            "summary": summary,
            "created_at": _iso(now),
            "expires_at": _iso(now + timedelta(seconds=self.ttl_seconds)),
        }
        self._write(self._path(ui_ref), payload)
        return {
            "ui_ref": ui_ref,
            "kind": kind,
            "summary": summary,
            "expires_at": payload["expires_at"],
        }

    def resolve(self, ui_ref: str, *, expected_kind: str | None = None) -> dict[str, Any]:
        path = self._path(ui_ref)
        if not path.is_file():
            raise UIRefError("ui_ref not found")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if _now() > _parse(payload["expires_at"]):
            raise UIRefError("ui_ref expired")
        if expected_kind and payload.get("kind") != expected_kind:
            raise UIRefError("ui_ref kind mismatch")
        return payload

    def purge_expired(self) -> int:
        removed = 0
        for path in self.root.glob("ui_*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                if _now() > _parse(payload["expires_at"]):
                    path.unlink()
                    removed += 1
            except Exception:
                continue
        return removed
