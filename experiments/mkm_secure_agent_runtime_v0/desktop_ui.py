"""Bounded Windows UI Automation layer for MKM Secure Agent Runtime V0.6.

This module exposes observation + low-risk interaction candidates through opaque
ephemeral UI refs. It does not expose arbitrary coordinates, raw keyboard
sequences, password fields, credential prompts, SEND, payment, deletion, or
other high-risk controls.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import re
from typing import Any

import psutil
from pywinauto import Desktop

from privacy import scan_text
from ui_refs import UIRefStore, UIRefError


class DesktopUIError(RuntimeError):
    pass


_BLOCKED_PROCESSES = {
    "consent.exe",
    "credentialuibroker.exe",
    "lsass.exe",
    "1password.exe",
    "bitwarden.exe",
    "keepass.exe",
    "keepassxc.exe",
}

_HIGH_RISK_LABEL = re.compile(
    r"(?i)\b(delete|remove|uninstall|erase|wipe|send|submit|pay|purchase|buy|"
    r"transfer|wire|withdraw|deploy|publish|push)\b|"
    r"(삭제|제거|초기화|전송|보내기|제출|결제|구매|송금|이체|출금|배포|게시)"
)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


_ACTION_LABEL_TYPES = {
    "Button", "MenuItem", "TabItem", "Hyperlink", "CheckBox",
    "RadioButton", "ListItem", "TreeItem",
}


def _safe_text(value: str | None, *, max_chars: int = 120) -> dict[str, Any]:
    raw = (value or "").strip()
    if not raw:
        return {"text": "", "sensitive": False, "sha256": _hash_text("")}
    result = scan_text(raw)
    if result.release_decision != "ALLOW":
        return {
            "text": "[SENSITIVE_TEXT]",
            "sensitive": True,
            "privacy_state": result.state,
            "sha256": _hash_text(raw),
        }
    return {
        "text": raw[:max_chars],
        "sensitive": False,
        "sha256": _hash_text(raw),
        "truncated": len(raw) > max_chars,
    }


def _process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name().lower()
    except Exception:
        return "unknown"


def _runtime_id(wrapper) -> list[int] | None:
    try:
        value = wrapper.element_info.runtime_id
        if value is None:
            return None
        return [int(x) for x in value]
    except Exception:
        return None


def _rect(wrapper) -> dict[str, int] | None:
    try:
        r = wrapper.rectangle()
        return {
            "left": int(r.left),
            "top": int(r.top),
            "right": int(r.right),
            "bottom": int(r.bottom),
        }
    except Exception:
        return None


def _is_password(wrapper) -> bool:
    try:
        return bool(getattr(wrapper.element_info, "is_password", False))
    except Exception:
        return False


def _summary_name(wrapper) -> str:
    try:
        return wrapper.window_text() or ""
    except Exception:
        return ""


def _selector_for(wrapper, *, top_handle: int) -> dict[str, Any]:
    info = wrapper.element_info
    return {
        "top_handle": int(top_handle),
        "runtime_id": _runtime_id(wrapper),
        "handle": int(getattr(wrapper, "handle", 0) or 0),
        "process_id": int(getattr(info, "process_id", 0) or 0),
        "control_type": str(getattr(info, "control_type", "") or ""),
        "automation_id": str(getattr(info, "automation_id", "") or ""),
        "class_name": str(getattr(info, "class_name", "") or ""),
        "name": _summary_name(wrapper),
        "is_password": _is_password(wrapper),
    }


def _fingerprint(selector: dict[str, Any]) -> str:
    stable = {
        k: selector.get(k)
        for k in (
            "top_handle",
            "runtime_id",
            "handle",
            "process_id",
            "control_type",
            "automation_id",
            "class_name",
            "name",
            "is_password",
        )
    }
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ResolvedControl:
    wrapper: Any
    selector: dict[str, Any]
    safe_summary: dict[str, Any]


class DesktopActionLayer:
    def __init__(self, ui_refs: UIRefStore):
        if os.name != "nt":
            raise DesktopUIError("V0.6 DesktopActionLayer supports Windows only")
        self.ui_refs = ui_refs

    def _desktop(self):
        return Desktop(backend="uia")

    def _deny_process(self, pid: int) -> None:
        name = _process_name(pid)
        if name in _BLOCKED_PROCESSES:
            raise DesktopUIError(f"process blocked by V0.6 policy: {name}")

    def list_windows(self, *, max_windows: int = 50) -> list[dict[str, Any]]:
        if max_windows < 1 or max_windows > 100:
            raise DesktopUIError("max_windows must be 1..100")
        rows: list[dict[str, Any]] = []
        for wrapper in self._desktop().windows(visible_only=True):
            try:
                handle = int(wrapper.handle)
                pid = int(wrapper.element_info.process_id)
                if not handle or not pid:
                    continue
                process_name = _process_name(pid)
                if process_name in _BLOCKED_PROCESSES:
                    continue
                raw_title = _summary_name(wrapper)
                title = {
                    "text": "[WINDOW_TITLE_HIDDEN]",
                    "sensitive": True,
                    "sha256": _hash_text(raw_title),
                    "reason": "DEFAULT_TITLE_NON_DISCLOSURE",
                }
                selector = _selector_for(wrapper, top_handle=handle)
                selector["fingerprint"] = _fingerprint(selector)
                summary = {
                    "title": title,
                    "process_id": pid,
                    "process_name": process_name,
                    "class_name": selector["class_name"],
                    "control_type": selector["control_type"],
                    "rectangle": _rect(wrapper),
                }
                ref = self.ui_refs.issue(kind="window", selector=selector, summary=summary)
                rows.append(ref)
                if len(rows) >= max_windows:
                    break
            except Exception:
                continue
        return rows

    def _resolve_window(self, ui_ref: str):
        payload = self.ui_refs.resolve(ui_ref, expected_kind="window")
        selector = payload["selector"]
        self._deny_process(int(selector["process_id"]))
        try:
            wrapper = self._desktop().window(handle=int(selector["top_handle"])).wrapper_object()
        except Exception as exc:
            raise DesktopUIError("window is no longer available") from exc
        current = _selector_for(wrapper, top_handle=int(selector["top_handle"]))
        if int(current["process_id"]) != int(selector["process_id"]):
            raise DesktopUIError("window process changed")
        if current["class_name"] != selector["class_name"]:
            raise DesktopUIError("window identity changed")
        return wrapper, payload

    def inspect_window(self, window_ref: str, *, max_controls: int = 100) -> dict[str, Any]:
        if max_controls < 1 or max_controls > 250:
            raise DesktopUIError("max_controls must be 1..250")
        window, window_payload = self._resolve_window(window_ref)
        rows = []
        try:
            descendants = window.descendants()
        except Exception as exc:
            raise DesktopUIError("failed to enumerate UIA controls") from exc

        for wrapper in descendants[:max_controls]:
            try:
                selector = _selector_for(wrapper, top_handle=int(window_payload["selector"]["top_handle"]))
                ctype = selector["control_type"]
                if selector["is_password"]:
                    name = {
                        "text": "[PASSWORD_CONTROL]",
                        "sensitive": True,
                        "sha256": _hash_text(selector["name"]),
                    }
                elif ctype in {"Edit", "Text", "Document"}:
                    name = {
                        "text": f"[{ctype.upper()}_CONTENT_HIDDEN]",
                        "sensitive": True,
                        "sha256": _hash_text(selector["name"]),
                        "reason": "CONTENT_BEARING_CONTROL_NON_DISCLOSURE",
                    }
                elif ctype in _ACTION_LABEL_TYPES:
                    name = _safe_text(selector["name"])
                else:
                    name = {
                        "text": f"[{ctype or 'CONTROL'}]",
                        "sensitive": False,
                        "sha256": _hash_text(selector["name"]),
                    }
                selector["fingerprint"] = _fingerprint(selector)
                summary = {
                    "name": name,
                    "control_type": selector["control_type"],
                    "automation_id": selector["automation_id"],
                    "class_name": selector["class_name"],
                    "enabled": bool(wrapper.is_enabled()),
                    "visible": bool(wrapper.is_visible()),
                    "is_password": selector["is_password"],
                    "rectangle": _rect(wrapper),
                    "process_name": _process_name(int(selector["process_id"])),
                }
                ref = self.ui_refs.issue(kind="control", selector=selector, summary=summary)
                rows.append(ref)
            except Exception:
                continue

        return {
            "window_ref": window_ref,
            "control_count": len(rows),
            "controls": rows,
            "truncated": len(descendants) > max_controls,
        }

    def resolve_control(self, control_ref: str) -> ResolvedControl:
        payload = self.ui_refs.resolve(control_ref, expected_kind="control")
        selector = payload["selector"]
        pid = int(selector["process_id"])
        self._deny_process(pid)

        try:
            top = self._desktop().window(handle=int(selector["top_handle"])).wrapper_object()
            candidates = top.descendants()
        except Exception as exc:
            raise DesktopUIError("parent window is no longer available") from exc

        runtime_id = selector.get("runtime_id")
        matches = []
        for wrapper in candidates:
            try:
                current = _selector_for(wrapper, top_handle=int(selector["top_handle"]))
                if int(current["process_id"]) != pid:
                    continue
                if runtime_id is not None and current.get("runtime_id") == runtime_id:
                    matches.append((wrapper, current))
                    continue
                if runtime_id is None:
                    keys = ("control_type", "automation_id", "class_name", "name")
                    if all(current.get(k) == selector.get(k) for k in keys):
                        matches.append((wrapper, current))
            except Exception:
                continue

        if len(matches) != 1:
            raise DesktopUIError(f"UI control resolution is ambiguous/stale: matches={len(matches)}")

        wrapper, current = matches[0]
        current_fingerprint = _fingerprint(current)
        if current_fingerprint != selector.get("fingerprint"):
            raise DesktopUIError("UI control fingerprint changed")
        current["fingerprint"] = current_fingerprint
        safe_summary = payload["summary"]
        return ResolvedControl(wrapper=wrapper, selector=current, safe_summary=safe_summary)

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
                return {
                    "decision": "DENY",
                    "reason": f"TEXT_PRIVACY_{scan.state}",
                }
            if len(text) > 4000:
                return {"decision": "DENY", "reason": "TEXT_TOO_LONG"}
            return {"decision": "HUMAN_GATE", "reason": "UI_TEXT_MUTATION"}

        return {"decision": "DENY", "reason": "UNSUPPORTED_UI_ACTION"}

    def click(self, control_ref: str) -> dict[str, Any]:
        resolved = self.resolve_control(control_ref)
        policy = self.action_policy(control_ref, action="click")
        if policy["decision"] == "DENY":
            raise DesktopUIError(policy["reason"])
        try:
            resolved.wrapper.verify_actionable()
            resolved.wrapper.click_input()
        except Exception as exc:
            raise DesktopUIError(f"click failed: {type(exc).__name__}") from exc
        return {
            "executed": True,
            "action": "click",
            "control_ref": control_ref,
            "control_type": resolved.selector["control_type"],
            "name": resolved.safe_summary.get("name"),
        }

    def set_text(self, control_ref: str, text: str) -> dict[str, Any]:
        resolved = self.resolve_control(control_ref)
        policy = self.action_policy(control_ref, action="set_text", text=text)
        if policy["decision"] == "DENY":
            raise DesktopUIError(policy["reason"])
        try:
            resolved.wrapper.verify_actionable()
            if not hasattr(resolved.wrapper, "set_edit_text"):
                raise DesktopUIError("control does not support set_edit_text")
            resolved.wrapper.set_edit_text(text)
        except DesktopUIError:
            raise
        except Exception as exc:
            raise DesktopUIError(f"set_text failed: {type(exc).__name__}") from exc
        return {
            "executed": True,
            "action": "set_text",
            "control_ref": control_ref,
            "text_sha256": _hash_text(text),
            "text_length": len(text),
        }
