"""Bounded Windows UI Automation layer for MKM Secure Agent Runtime V0.6.

All pywinauto/UIA calls run in an isolated subprocess. The parent MCP runtime
stores opaque ephemeral refs and applies policy before mutations.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import psutil

from privacy import scan_text
from ui_refs import UIRefStore


class DesktopUIError(RuntimeError):
    pass


_BLOCKED_PROCESSES = {
    "consent.exe", "credentialuibroker.exe", "lsass.exe",
    "1password.exe", "bitwarden.exe", "keepass.exe", "keepassxc.exe",
}
_HIGH_RISK_LABEL = re.compile(
    r"(?i)\b(delete|remove|uninstall|erase|wipe|send|submit|pay|purchase|buy|"
    r"transfer|wire|withdraw|deploy|publish|push)\b|"
    r"(삭제|제거|초기화|전송|보내기|제출|결제|구매|송금|이체|출금|배포|게시)"
)
_ACTION_LABEL_TYPES = {
    "Button", "MenuItem", "TabItem", "Hyperlink", "CheckBox",
    "RadioButton", "ListItem", "TreeItem",
}


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _safe_text(value: str | None, *, max_chars: int = 120) -> dict[str, Any]:
    raw = (value or "").strip()
    result = scan_text(raw)
    if result.release_decision != "ALLOW":
        return {
            "text": "[SENSITIVE_TEXT]", "sensitive": True,
            "privacy_state": result.state, "sha256": _hash_text(raw),
        }
    return {
        "text": raw[:max_chars], "sensitive": False, "sha256": _hash_text(raw),
        "truncated": len(raw) > max_chars,
    }


def _process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name().lower()
    except Exception:
        return "unknown"


@dataclass(frozen=True)
class ResolvedControl:
    selector: dict[str, Any]
    safe_summary: dict[str, Any]


class DesktopActionLayer:
    def __init__(self, ui_refs: UIRefStore, *, worker_timeout: float = 12.0):
        if os.name != "nt":
            raise DesktopUIError("V0.6 DesktopActionLayer supports Windows only")
        self.ui_refs = ui_refs
        self.worker_timeout = worker_timeout
        self.worker_path = Path(__file__).with_name("desktop_worker.py").resolve()
        if not self.worker_path.is_file():
            raise DesktopUIError("desktop_worker.py missing")

    def _worker(self, payload: dict[str, Any], *, timeout: float | None = None) -> dict[str, Any]:
        try:
            env = dict(os.environ)
            env["PYTHONUTF8"] = "1"
            cp = subprocess.run(
                [sys.executable, str(self.worker_path)],
                input=json.dumps(payload, ensure_ascii=False),
                text=True,
                encoding="utf-8",
                errors="strict",
                capture_output=True,
                timeout=timeout or self.worker_timeout,
                shell=False,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise DesktopUIError("UI worker timeout") from exc

        if cp.returncode != 0:
            detail = cp.stdout.strip()[-1000:] or cp.stderr.strip()[-1000:]
            raise DesktopUIError(f"UI worker failed rc={cp.returncode}: {detail}")
        try:
            envelope = json.loads(cp.stdout)
        except Exception as exc:
            raise DesktopUIError("UI worker returned invalid JSON") from exc
        if not envelope.get("ok"):
            raise DesktopUIError(str(envelope.get("error") or "UI worker error"))
        return envelope["result"]

    def _deny_process(self, pid: int) -> None:
        name = _process_name(pid)
        if name in _BLOCKED_PROCESSES:
            raise DesktopUIError(f"process blocked by V0.6 policy: {name}")

    def list_windows(self, *, max_windows: int = 50) -> list[dict[str, Any]]:
        if max_windows < 1 or max_windows > 100:
            raise DesktopUIError("max_windows must be 1..100")
        result = self._worker({"op": "list_windows", "max_windows": max_windows})
        rows = []
        for item in result["windows"]:
            selector = item["selector"]
            raw_title = str(selector.get("name") or "")
            summary = {
                "title": {
                    "text": "[WINDOW_TITLE_HIDDEN]",
                    "sensitive": True,
                    "sha256": _hash_text(raw_title),
                    "reason": "DEFAULT_TITLE_NON_DISCLOSURE",
                },
                "process_id": int(selector["process_id"]),
                "process_name": item.get("process_name", "unknown"),
                "class_name": selector.get("class_name", ""),
                "control_type": selector.get("control_type", ""),
                "rectangle": item.get("rectangle"),
            }
            rows.append(self.ui_refs.issue(kind="window", selector=selector, summary=summary))
        return rows

    def _window_payload(self, window_ref: str) -> dict[str, Any]:
        payload = self.ui_refs.resolve(window_ref, expected_kind="window")
        self._deny_process(int(payload["selector"]["process_id"]))
        return payload

    def inspect_window(self, window_ref: str, *, max_controls: int = 100) -> dict[str, Any]:
        if max_controls < 1 or max_controls > 250:
            raise DesktopUIError("max_controls must be 1..250")
        window_payload = self._window_payload(window_ref)
        result = self._worker({
            "op": "inspect_window",
            "selector": window_payload["selector"],
            "max_controls": max_controls,
        })
        rows = []
        for item in result["controls"]:
            selector = item["selector"]
            ctype = str(selector.get("control_type") or "")
            raw_name = str(selector.get("name") or "")
            if selector.get("is_password"):
                name = {"text": "[PASSWORD_CONTROL]", "sensitive": True, "sha256": _hash_text(raw_name)}
            elif ctype in {"Edit", "Text", "Document"}:
                name = {
                    "text": f"[{ctype.upper()}_CONTENT_HIDDEN]",
                    "sensitive": True,
                    "sha256": _hash_text(raw_name),
                    "reason": "CONTENT_BEARING_CONTROL_NON_DISCLOSURE",
                }
            elif ctype in _ACTION_LABEL_TYPES:
                name = _safe_text(raw_name)
            else:
                name = {
                    "text": f"[{ctype or 'CONTROL'}]",
                    "sensitive": False,
                    "sha256": _hash_text(raw_name),
                }
            summary = {
                "name": name,
                "control_type": ctype,
                "automation_id": selector.get("automation_id", ""),
                "class_name": selector.get("class_name", ""),
                "enabled": bool(item.get("enabled")),
                "visible": bool(item.get("visible")),
                "is_password": bool(selector.get("is_password")),
                "rectangle": item.get("rectangle"),
                "process_name": item.get("process_name", "unknown"),
            }
            rows.append(self.ui_refs.issue(kind="control", selector=selector, summary=summary))
        return {
            "window_ref": window_ref,
            "control_count": len(rows),
            "controls": rows,
            "truncated": bool(result.get("truncated")),
        }

    def resolve_control(self, control_ref: str) -> ResolvedControl:
        payload = self.ui_refs.resolve(control_ref, expected_kind="control")
        selector = payload["selector"]
        self._deny_process(int(selector["process_id"]))
        result = self._worker({"op": "resolve_control", "selector": selector})
        current = result["selector"]
        if current.get("fingerprint") != selector.get("fingerprint"):
            raise DesktopUIError("UI control fingerprint changed")
        return ResolvedControl(selector=current, safe_summary=payload["summary"])

    def action_policy(self, control_ref: str, *, action: str, text: str | None = None) -> dict[str, Any]:
        resolved = self.resolve_control(control_ref)
        name = str(resolved.selector.get("name") or "")
        ctype = str(resolved.selector.get("control_type") or "")
        if resolved.selector.get("is_password"):
            return {"decision": "DENY", "reason": "PASSWORD_CONTROL"}
        if _HIGH_RISK_LABEL.search(name):
            return {"decision": "DENY", "reason": "HIGH_RISK_CONTROL_LABEL"}

        if action == "click":
            return {"decision": "HUMAN_GATE", "reason": "UI_MUTATION"}

        if action == "set_text":
            if ctype != "Edit":
                return {"decision": "DENY", "reason": "TEXT_ONLY_ALLOWED_FOR_EDIT_CONTROL"}
            if text is None:
                return {"decision": "DENY", "reason": "TEXT_REQUIRED"}
            scan = scan_text(text)
            if scan.release_decision != "ALLOW":
                return {"decision": "DENY", "reason": f"TEXT_PRIVACY_{scan.state}"}
            if len(text) > 4000:
                return {"decision": "DENY", "reason": "TEXT_TOO_LONG"}
            return {"decision": "HUMAN_GATE", "reason": "UI_TEXT_MUTATION"}

        return {"decision": "DENY", "reason": "UNSUPPORTED_UI_ACTION"}

    def click(self, control_ref: str) -> dict[str, Any]:
        resolved = self.resolve_control(control_ref)
        policy = self.action_policy(control_ref, action="click")
        if policy["decision"] != "HUMAN_GATE":
            raise DesktopUIError(policy["reason"])
        result = self._worker({"op": "click", "selector": resolved.selector})
        return {
            "executed": bool(result.get("executed")),
            "action": "click",
            "control_ref": control_ref,
            "control_type": resolved.selector.get("control_type"),
            "name": resolved.safe_summary.get("name"),
        }

    def set_text(self, control_ref: str, text: str) -> dict[str, Any]:
        resolved = self.resolve_control(control_ref)
        policy = self.action_policy(control_ref, action="set_text", text=text)
        if policy["decision"] != "HUMAN_GATE":
            raise DesktopUIError(policy["reason"])
        result = self._worker({"op": "set_text", "selector": resolved.selector, "text": text})
        return {
            "executed": bool(result.get("executed")),
            "action": "set_text",
            "control_ref": control_ref,
            "text_sha256": _hash_text(text),
            "text_length": len(text),
        }

    def get_value_for_test(self, control_ref: str) -> str:
        """Test-only helper. Not exposed as MCP tool."""
        resolved = self.resolve_control(control_ref)
        result = self._worker({"op": "get_value", "selector": resolved.selector})
        return str(result["value"])
