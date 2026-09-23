from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .ledger import EventLedger
from .measurement import MeasurementRecorder
from .status import StatusBoard


class SharedStatusError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


class SharedStatusPublisher:
    """Publishes a self-checking derived CURRENT_STATUS view.

    The append-only ledger remains authoritative. The published JSON is only a
    cross-chat/process read surface and can become STALE when new ledger events
    are appended.
    """

    STATUS_NAME = "CURRENT_STATUS.json"
    SEAL_NAME = "CURRENT_STATUS.sha256.json"

    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    def build(self) -> dict[str, Any]:
        board = StatusBoard(self.ledger).build()
        measurements = MeasurementRecorder(self.ledger).summarize()
        latest_receipts: dict[str, dict[str, Any]] = {}
        finalized: dict[str, dict[str, Any]] = {}
        for event in self.ledger.events():
            task_id = event.get("task_id")
            if not task_id:
                continue
            if event["event_type"] == "EVIDENCE_RECEIPT_ISSUED":
                latest_receipts[task_id] = {
                    "event_seq": event["seq"],
                    **event["payload"],
                }
            elif event["event_type"] == "DOGFOOD_TASK_FINALIZED":
                finalized[task_id] = {
                    "event_seq": event["seq"],
                    **event["payload"],
                }

        integrity = self.ledger.verify_chain()
        return {
            "schema": "mkm_shared_current_status_v0",
            "schema_version": 1,
            "authoritative_source": "APPEND_ONLY_EVENT_LEDGER",
            "derived_view": True,
            "ledger": integrity,
            "status_board": board,
            "dogfood": measurements,
            "latest_receipts": latest_receipts,
            "finalized_tasks": finalized,
            "global_boundaries": {
                "automatic_next_task": "NO",
                "automatic_merge": "NO",
                "automatic_deploy": "NO",
                "automatic_send": "NO",
                "human_gate_required_for_candidate": True,
                "unknown_is_valid_result": True,
            },
        }

    def publish(self, directory: str | Path) -> dict[str, Any]:
        root = Path(directory).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        payload = self.build()
        raw = _canonical_bytes(payload)
        digest = hashlib.sha256(raw).hexdigest()

        status_path = root / self.STATUS_NAME
        seal_path = root / self.SEAL_NAME
        self._atomic_write(status_path, raw)
        seal = {
            "schema": "mkm_shared_current_status_seal_v0",
            "sha256": digest,
            "status_file": self.STATUS_NAME,
            "covered_event_count": payload["ledger"].get("event_count"),
            "covered_head_hash": payload["ledger"].get("head_hash"),
            "authoritative_source": "APPEND_ONLY_EVENT_LEDGER",
        }
        self._atomic_write(seal_path, _canonical_bytes(seal))
        return {
            "status_path": str(status_path),
            "seal_path": str(seal_path),
            "sha256": digest,
            "covered_event_count": seal["covered_event_count"],
            "covered_head_hash": seal["covered_head_hash"],
            "view_state": "CURRENT_AT_PUBLICATION",
        }

    def verify(self, directory: str | Path) -> dict[str, Any]:
        root = Path(directory).expanduser().resolve()
        status_path = root / self.STATUS_NAME
        seal_path = root / self.SEAL_NAME
        if not status_path.is_file() or not seal_path.is_file():
            return {
                "state": "NOT_ESTABLISHED",
                "reason": "STATUS_OR_SEAL_MISSING",
            }
        try:
            raw = status_path.read_bytes()
            payload = json.loads(raw.decode("utf-8-sig"))
            seal = json.loads(seal_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {
                "state": "INVALID",
                "reason": "STATUS_OR_SEAL_UNREADABLE",
            }
        digest = hashlib.sha256(raw).hexdigest()
        if digest != seal.get("sha256"):
            return {
                "state": "INVALID",
                "reason": "STATUS_SHA256_MISMATCH",
                "observed_sha256": digest,
                "sealed_sha256": seal.get("sha256"),
            }
        if payload.get("derived_view") is not True:
            return {
                "state": "INVALID",
                "reason": "STATUS_NOT_MARKED_DERIVED",
            }
        current = self.ledger.verify_chain()
        if not current.get("valid"):
            return {
                "state": "INVALID",
                "reason": "AUTHORITATIVE_LEDGER_CHAIN_INVALID",
                "ledger": current,
            }
        sealed_head = seal.get("covered_head_hash")
        sealed_count = seal.get("covered_event_count")
        if (
            current.get("head_hash") != sealed_head
            or current.get("event_count") != sealed_count
        ):
            return {
                "state": "STALE",
                "reason": "LEDGER_ADVANCED_SINCE_PUBLICATION",
                "sealed_head_hash": sealed_head,
                "current_head_hash": current.get("head_hash"),
                "sealed_event_count": sealed_count,
                "current_event_count": current.get("event_count"),
                "sha256_valid": True,
            }
        return {
            "state": "CURRENT",
            "reason": "STATUS_SEAL_AND_LEDGER_HEAD_MATCH",
            "sha256": digest,
            "covered_head_hash": sealed_head,
            "covered_event_count": sealed_count,
        }

    @staticmethod
    def _atomic_write(path: Path, raw: bytes) -> None:
        fd, tmp_name = tempfile.mkstemp(
            prefix=".mkm-shared-status-",
            suffix=".tmp",
            dir=path.parent,
        )
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        finally:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass
