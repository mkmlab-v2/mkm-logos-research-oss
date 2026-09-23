"""One-time local approval broker for MKM Secure Agent Runtime V0.1.

Approval payloads persist only action metadata + argument digest.
Raw file content, prompts, command stdout/stderr, and secrets are not persisted here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any
import uuid


class ApprovalError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


class ApprovalBroker:
    def __init__(self, state_dir: Path, *, protected_roots: list[Path]):
        self.state_dir = state_dir.expanduser().resolve()
        roots = [p.expanduser().resolve() for p in protected_roots]
        if any(_is_relative_to(self.state_dir, root) for root in roots):
            raise ApprovalError(
                "approval state_dir must be outside every model-accessible approved root"
            )
        self.request_dir = self.state_dir / "approval_requests"
        self.request_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, approval_id: str) -> Path:
        if not approval_id.startswith("apr_") or any(
            ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for ch in approval_id
        ):
            raise ApprovalError("invalid approval id")
        return self.request_dir / f"{approval_id}.json"

    def _atomic_write(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".mkm-approval-", suffix=".tmp", dir=path.parent)
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

    def request(
        self,
        *,
        action: str,
        target: str,
        args_sha256: str,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        if ttl_seconds < 30 or ttl_seconds > 3600:
            raise ApprovalError("ttl_seconds must be between 30 and 3600")
        now = _now()
        approval_id = "apr_" + uuid.uuid4().hex
        payload = {
            "schema": "mkm_local_approval_v0_1",
            "approval_id": approval_id,
            "action": action,
            "target": target,
            "args_sha256": args_sha256,
            "status": "REQUESTED",
            "created_at": _iso(now),
            "expires_at": _iso(now + timedelta(seconds=ttl_seconds)),
            "approved_at": None,
            "denied_at": None,
            "consumed_at": None,
            "approved_via": None,
        }
        self._atomic_write(self._path(approval_id), payload)
        return payload

    def read(self, approval_id: str) -> dict[str, Any]:
        path = self._path(approval_id)
        if not path.is_file():
            raise ApprovalError("approval request not found")
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def approve(self, approval_id: str) -> dict[str, Any]:
        payload = self.read(approval_id)
        if payload["status"] != "REQUESTED":
            raise ApprovalError(f"cannot approve status={payload['status']}")
        if _now() > _parse_iso(payload["expires_at"]):
            payload["status"] = "EXPIRED"
            self._atomic_write(self._path(approval_id), payload)
            raise ApprovalError("approval request expired")
        payload["status"] = "APPROVED"
        payload["approved_at"] = _iso(_now())
        payload["approved_via"] = "LOCAL_CLI"
        self._atomic_write(self._path(approval_id), payload)
        return payload

    def deny(self, approval_id: str) -> dict[str, Any]:
        payload = self.read(approval_id)
        if payload["status"] not in {"REQUESTED", "APPROVED"}:
            raise ApprovalError(f"cannot deny status={payload['status']}")
        payload["status"] = "DENIED"
        payload["denied_at"] = _iso(_now())
        self._atomic_write(self._path(approval_id), payload)
        return payload

    def consume(
        self,
        approval_id: str,
        *,
        action: str,
        target: str,
        args_sha256: str,
    ) -> dict[str, Any]:
        payload = self.read(approval_id)
        if payload["status"] != "APPROVED":
            raise ApprovalError(f"approval is not usable: status={payload['status']}")
        if _now() > _parse_iso(payload["expires_at"]):
            payload["status"] = "EXPIRED"
            self._atomic_write(self._path(approval_id), payload)
            raise ApprovalError("approval request expired")
        if payload.get("approved_via") != "LOCAL_CLI":
            raise ApprovalError("approval was not granted by local CLI")
        expected = (payload["action"], payload["target"], payload["args_sha256"])
        observed = (action, target, args_sha256)
        if observed != expected:
            raise ApprovalError("approval does not match requested action")
        # Consume before execution. A failed action never makes a token reusable.
        payload["status"] = "CONSUMED"
        payload["consumed_at"] = _iso(_now())
        self._atomic_write(self._path(approval_id), payload)
        return payload

    def list_requests(self) -> list[dict[str, Any]]:
        rows = []
        for path in sorted(self.request_dir.glob("apr_*.json")):
            try:
                rows.append(json.loads(path.read_text(encoding="utf-8-sig")))
            except Exception:
                rows.append({
                    "approval_id": path.stem,
                    "status": "UNREADABLE",
                    "path": str(path),
                })
        return rows
