"""Isolated pywinauto UIA worker for MKM V0.6.

Reads one JSON request from stdin and writes one JSON response to stdout.
A COM/UIA crash terminates only this process, not the MCP runtime.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from typing import Any

import psutil
from pywinauto import Desktop


BLOCKED_PROCESSES = {
    "consent.exe",
    "credentialuibroker.exe",
    "lsass.exe",
    "1password.exe",
    "bitwarden.exe",
    "keepass.exe",
    "keepassxc.exe",
}


def _process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name().lower()
    except Exception:
        return "unknown"


def _runtime_id(wrapper) -> list[int] | None:
    try:
        value = wrapper.element_info.runtime_id
        return [int(x) for x in value] if value is not None else None
    except Exception:
        return None


def _name(wrapper) -> str:
    try:
        return wrapper.window_text() or ""
    except Exception:
        return ""


def _password(wrapper) -> bool:
    try:
        return bool(getattr(wrapper.element_info, "is_password", False))
    except Exception:
        return False


def _rect(wrapper) -> dict[str, int] | None:
    try:
        r = wrapper.rectangle()
        return {"left": int(r.left), "top": int(r.top), "right": int(r.right), "bottom": int(r.bottom)}
    except Exception:
        return None


def _selector(wrapper, top_handle: int) -> dict[str, Any]:
    info = wrapper.element_info
    data = {
        "top_handle": int(top_handle),
        "runtime_id": _runtime_id(wrapper),
        "handle": int(getattr(wrapper, "handle", 0) or 0),
        "process_id": int(getattr(info, "process_id", 0) or 0),
        "control_type": str(getattr(info, "control_type", "") or ""),
        "automation_id": str(getattr(info, "automation_id", "") or ""),
        "class_name": str(getattr(info, "class_name", "") or ""),
        "name": _name(wrapper),
        "is_password": _password(wrapper),
    }
    stable = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    data["fingerprint"] = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    return data


def _deny_pid(pid: int) -> None:
    name = _process_name(pid)
    if name in BLOCKED_PROCESSES:
        raise RuntimeError(f"blocked process: {name}")


def _resolve_control(selector: dict[str, Any]):
    pid = int(selector["process_id"])
    _deny_pid(pid)
    top_handle = int(selector["top_handle"])
    top = Desktop(backend="uia").window(handle=top_handle).wrapper_object()
    candidates = top.descendants()
    runtime_id = selector.get("runtime_id")
    matches = []
    for wrapper in candidates:
        try:
            current = _selector(wrapper, top_handle)
            if int(current["process_id"]) != pid:
                continue
            if runtime_id is not None:
                if current.get("runtime_id") == runtime_id:
                    matches.append((wrapper, current))
            else:
                keys = ("control_type", "automation_id", "class_name", "name")
                if all(current.get(k) == selector.get(k) for k in keys):
                    matches.append((wrapper, current))
        except Exception:
            continue
    if len(matches) != 1:
        raise RuntimeError(f"control ambiguous/stale: matches={len(matches)}")
    wrapper, current = matches[0]
    if current["fingerprint"] != selector.get("fingerprint"):
        raise RuntimeError("control fingerprint changed")
    return wrapper, current


def _handle(req: dict[str, Any]) -> dict[str, Any]:
    op = req.get("op")
    if op == "list_windows":
        limit = int(req.get("max_windows", 50))
        rows = []
        for w in Desktop(backend="uia").windows(visible_only=True):
            try:
                handle = int(w.handle)
                pid = int(w.element_info.process_id)
                if not handle or not pid:
                    continue
                pname = _process_name(pid)
                if pname in BLOCKED_PROCESSES:
                    continue
                rows.append({
                    "selector": _selector(w, handle),
                    "process_name": pname,
                    "rectangle": _rect(w),
                })
                if len(rows) >= limit:
                    break
            except Exception:
                continue
        return {"windows": rows}

    if op == "inspect_window":
        selector = req["selector"]
        pid = int(selector["process_id"])
        _deny_pid(pid)
        top = Desktop(backend="uia").window(handle=int(selector["top_handle"])).wrapper_object()
        if int(top.element_info.process_id) != pid:
            raise RuntimeError("window process changed")
        controls = []
        descendants = top.descendants()
        for w in descendants[: int(req.get("max_controls", 100))]:
            try:
                controls.append({
                    "selector": _selector(w, int(selector["top_handle"])),
                    "enabled": bool(w.is_enabled()),
                    "visible": bool(w.is_visible()),
                    "rectangle": _rect(w),
                    "process_name": _process_name(int(w.element_info.process_id)),
                })
            except Exception:
                continue
        return {"controls": controls, "truncated": len(descendants) > int(req.get("max_controls", 100))}

    if op == "resolve_control":
        _w, current = _resolve_control(req["selector"])
        return {"selector": current}

    if op == "click":
        w, current = _resolve_control(req["selector"])
        w.verify_actionable()
        if hasattr(w, "invoke"):
            w.invoke()
        elif hasattr(w, "click"):
            w.click()
        else:
            w.click_input()
        time.sleep(0.15)
        return {"executed": True, "selector": current}

    if op == "set_text":
        w, current = _resolve_control(req["selector"])
        w.verify_actionable()
        if not hasattr(w, "set_edit_text"):
            raise RuntimeError("control does not support set_edit_text")
        w.set_edit_text(str(req.get("text", "")))
        return {"executed": True, "selector": current}

    if op == "get_value":
        w, current = _resolve_control(req["selector"])
        if not hasattr(w, "get_value"):
            raise RuntimeError("control does not support get_value")
        return {"selector": current, "value": w.get_value()}

    raise RuntimeError(f"unknown worker op: {op}")


def main() -> int:
    try:
        req = json.loads(sys.stdin.read())
        result = _handle(req)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
