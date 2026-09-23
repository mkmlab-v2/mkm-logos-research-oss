"""Fail-closed Cursor desktop Agent bridge for MKM Secure Agent Runtime V1.0.

Uses Cursor's own desktop bridge CLI only when a live discovery record is
present and tied to the exact dedicated session user-data-dir.

No discovery => no send. No exact session instance => no send.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import psutil
import re
import subprocess
from typing import Any

from privacy import scan_text
from developer_session import find_cursor_cli


class CursorAgentBridgeError(RuntimeError):
    pass


_PROTOCOL_VERSION = 1
_DISCOVERY_SUFFIX = ".json"
_ALLOWED_THREAD_SOURCES = {"local", "draft", "claude-code"}
_FORBIDDEN_PROMPT = re.compile(
    r"(?i)\b(git\s+push|deploy|publish|send\s+email|wire\s+transfer|"
    r"bank\s+transfer|delete\s+all|rm\s+-rf|format\s+[a-z]:|"
    r"install\s+extension|uninstall\s+extension)\b|"
    r"(배포|송금|이체|전체\s*삭제|푸시|메일\s*전송)"
)


@dataclass(frozen=True)
class BridgeInstance:
    pid: int
    socket_path: str
    app_name: str
    app_version: str
    user_data_dir: str
    created_at: int


def default_bridge_dir() -> Path:
    override = os.environ.get("CURSOR_DESKTOP_BRIDGE_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".cursor" / "desktop-bridge").resolve()


def _alive(pid: int) -> bool:
    try:
        return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
    except Exception:
        return False


def _normalize(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def discover_instances(bridge_dir: Path | None = None) -> list[BridgeInstance]:
    root = (bridge_dir or default_bridge_dir()).expanduser().resolve()
    if not root.is_dir():
        return []
    rows: list[BridgeInstance] = []
    for path in sorted(root.glob(f"*{_DISCOVERY_SUFFIX}")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if int(payload.get("protocolVersion")) != _PROTOCOL_VERSION:
                continue
            pid = int(payload.get("pid"))
            if not _alive(pid):
                continue
            token = str(payload.get("token") or "")
            if not re.fullmatch(r"[0-9a-f]{64}", token):
                continue
            socket_path = str(payload.get("socketPath") or "")
            user_data_dir = str(payload.get("userDataDir") or "")
            app_name = str(payload.get("appName") or "")
            app_version = str(payload.get("appVersion") or "")
            created_at = int(payload.get("createdAt"))
            if not socket_path or not user_data_dir or not app_name or not app_version:
                continue
            rows.append(BridgeInstance(
                pid=pid,
                socket_path=socket_path,
                app_name=app_name,
                app_version=app_version,
                user_data_dir=user_data_dir,
                created_at=created_at,
            ))
        except Exception:
            continue
    return rows


class CursorAgentBridge:
    def __init__(self, *, bridge_dir: Path | None = None):
        self.bridge_dir = bridge_dir or default_bridge_dir()

    def session_instance(self, user_data_dir: str | Path) -> BridgeInstance:
        target = _normalize(user_data_dir)
        hits = [
            x for x in discover_instances(self.bridge_dir)
            if _normalize(x.user_data_dir) == target
        ]
        if len(hits) != 1:
            if not hits:
                raise CursorAgentBridgeError("CURSOR_DESKTOP_BRIDGE_NOT_ESTABLISHED")
            raise CursorAgentBridgeError("CURSOR_DESKTOP_BRIDGE_AMBIGUOUS")
        return hits[0]

    def _run_desktop(
        self,
        args: list[str],
        *,
        stdin_text: str | None = None,
        timeout: float = 15.0,
    ) -> subprocess.CompletedProcess[str]:
        cli = find_cursor_cli()
        env = dict(os.environ)
        env["ELECTRON_RUN_AS_NODE"] = "1"
        env["VSCODE_DEV"] = ""
        env["CURSOR_DESKTOP_BRIDGE_DIR"] = str(self.bridge_dir)
        argv = [cli.executable, cli.cli_js, "desktop", *args]
        try:
            return subprocess.run(
                argv,
                input=stdin_text,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout,
                shell=False,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise CursorAgentBridgeError("CURSOR_DESKTOP_BRIDGE_TIMEOUT") from exc

    def list_threads(self, user_data_dir: str | Path) -> list[dict[str, Any]]:
        instance = self.session_instance(user_data_dir)
        cp = self._run_desktop(["ls", "--json"])
        if cp.returncode != 0:
            raise CursorAgentBridgeError(
                "CURSOR_DESKTOP_LIST_FAILED:" + (cp.stderr.strip()[-500:] or str(cp.returncode))
            )
        try:
            rows = json.loads(cp.stdout)
        except Exception as exc:
            raise CursorAgentBridgeError("CURSOR_DESKTOP_LIST_INVALID_JSON") from exc
        if not isinstance(rows, list):
            raise CursorAgentBridgeError("CURSOR_DESKTOP_LIST_INVALID_SHAPE")

        target = _normalize(instance.user_data_dir)
        filtered = []
        for row in rows:
            try:
                inst = row.get("instance") or {}
                source = str(row.get("source") or "")
                if _normalize(inst.get("userDataDir") or "") != target:
                    continue
                if source not in _ALLOWED_THREAD_SOURCES:
                    continue
                filtered.append({
                    "id": str(row["id"]),
                    "title": str(row.get("title") or ""),
                    "source": source,
                    "status": str(row.get("status") or "unknown"),
                    "lastUpdatedAt": int(row.get("lastUpdatedAt") or 0),
                    "windowId": int(row.get("windowId") or 0),
                })
            except Exception:
                continue
        filtered.sort(key=lambda x: x["lastUpdatedAt"], reverse=True)
        return filtered

    def validate_prompt(self, text: str) -> dict[str, Any]:
        if not text or not text.strip():
            return {"decision": "DENY", "reason": "EMPTY_PROMPT"}
        if len(text) > 12000:
            return {"decision": "DENY", "reason": "PROMPT_TOO_LONG"}
        privacy = scan_text(text)
        if privacy.release_decision != "ALLOW":
            return {
                "decision": "DENY",
                "reason": f"PROMPT_PRIVACY_{privacy.state}",
            }
        if _FORBIDDEN_PROMPT.search(text):
            return {"decision": "DENY", "reason": "FORBIDDEN_ACTION_DIRECTIVE"}
        return {"decision": "HUMAN_GATE", "reason": "AGENT_EXTERNAL_MUTATION"}

    def send(
        self,
        user_data_dir: str | Path,
        thread_id: str,
        text: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        if force:
            raise CursorAgentBridgeError("FORCE_SEND_DISABLED_V1_0")
        policy = self.validate_prompt(text)
        if policy["decision"] != "HUMAN_GATE":
            raise CursorAgentBridgeError(policy["reason"])
        threads = self.list_threads(user_data_dir)
        hits = [x for x in threads if x["id"] == thread_id]
        if len(hits) != 1:
            raise CursorAgentBridgeError("THREAD_NOT_EXACTLY_BOUND_TO_SESSION")
        cp = self._run_desktop(
            ["send", thread_id, "--stdin", "--json"],
            stdin_text=text,
        )
        if cp.returncode != 0:
            raise CursorAgentBridgeError(
                "CURSOR_DESKTOP_SEND_FAILED:" + (cp.stderr.strip()[-500:] or cp.stdout.strip()[-500:])
            )
        try:
            payload = json.loads(cp.stdout)
        except Exception as exc:
            raise CursorAgentBridgeError("CURSOR_DESKTOP_SEND_INVALID_JSON") from exc
        status = str(payload.get("status") or "")
        if status not in {"submitted", "queued"}:
            raise CursorAgentBridgeError(f"CURSOR_DESKTOP_SEND_STATUS_{status or 'UNKNOWN'}")
        return {
            "status": status,
            "threadId": str(payload.get("threadId") or thread_id),
            "windowId": int(payload.get("windowId") or 0),
            "threadTitle": str(payload.get("threadTitle") or ""),
        }
