"""Headless controller used by the V0.5 Windows tray shell."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from approval import ApprovalBroker, ApprovalError
from ollama_manager import OllamaManager, OllamaManagerError, OllamaStatus


@dataclass(frozen=True)
class ApprovalView:
    approval_id: str
    action: str
    target: str
    args_sha256: str
    status: str
    created_at: str
    expires_at: str


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TrayController:
    def __init__(
        self,
        broker: ApprovalBroker,
        ollama: OllamaManager,
        *,
        on_new_approval: Callable[[ApprovalView], None] | None = None,
    ):
        self.broker = broker
        self.ollama = ollama
        self.on_new_approval = on_new_approval
        self._seen_pending: set[str] = set()

    def pending(self) -> list[ApprovalView]:
        now = datetime.now(timezone.utc)
        rows: list[ApprovalView] = []
        for item in self.broker.list_requests():
            if item.get("status") != "REQUESTED":
                continue
            try:
                if now > _parse_time(item["expires_at"]):
                    continue
            except Exception:
                continue
            rows.append(ApprovalView(
                approval_id=item["approval_id"],
                action=item["action"],
                target=item["target"],
                args_sha256=item["args_sha256"],
                status=item["status"],
                created_at=item["created_at"],
                expires_at=item["expires_at"],
            ))
        rows.sort(key=lambda x: (x.created_at, x.approval_id))
        return rows

    def poll(self) -> list[ApprovalView]:
        rows = self.pending()
        current = {x.approval_id for x in rows}
        new = [x for x in rows if x.approval_id not in self._seen_pending]
        self._seen_pending &= current
        self._seen_pending |= current
        if self.on_new_approval:
            for item in new:
                self.on_new_approval(item)
        return rows

    def approve(self, approval_id: str) -> dict[str, Any]:
        return self.broker.approve(approval_id)

    def deny(self, approval_id: str) -> dict[str, Any]:
        return self.broker.deny(approval_id)

    def ollama_status(self) -> OllamaStatus:
        return self.ollama.status()

    def ensure_ollama(self) -> OllamaStatus:
        return self.ollama.ensure_running()

    def shutdown(self) -> None:
        self.ollama.stop_if_started()
