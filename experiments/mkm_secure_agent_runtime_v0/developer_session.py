"""Dedicated Cursor developer worker sessions for MKM Secure Agent Runtime V0.9.

A V0.9 session does not infer an existing window/workspace relationship.
It creates a dedicated Cursor instance with:
- explicit approved workspace
- unique user-data-dir under MKM_AGENT_STATE
- generated .code-workspace outside the project
- unique window.title marker
- extensions disabled for bounded validation

BOUND_ESTABLISHED requires:
1) generated workspace file still matches the approved workspace,
2) visible cursor.exe window title contains the unique local marker,
3) that window PID belongs to a Cursor process whose command line contains the
   exact session user-data-dir.

Raw window titles are never returned through MCP.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import psutil
import subprocess
import tempfile
import time
from typing import Any
import uuid

from desktop_ui import DesktopActionLayer
from runtime import RuntimeConfig


class DeveloperSessionError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_text(value: str) -> str:
    return _sha_bytes(value.encode("utf-8"))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class CursorCLI:
    executable: str
    cli_js: str
    version: str | None


def find_cursor_cli() -> CursorCLI:
    candidates: list[Path] = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Programs" / "cursor" / "Cursor.exe")
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            if str(proc.info.get("name") or "").lower() == "cursor.exe":
                exe = proc.info.get("exe")
                if exe:
                    candidates.insert(0, Path(exe))
        except Exception:
            continue

    seen: set[str] = set()
    for exe in candidates:
        try:
            exe = exe.expanduser().resolve()
        except Exception:
            continue
        key = str(exe).lower()
        if key in seen:
            continue
        seen.add(key)
        cli_js = exe.parent / "resources" / "app" / "out" / "cli.js"
        if exe.is_file() and cli_js.is_file():
            version = None
            env = dict(os.environ)
            env["ELECTRON_RUN_AS_NODE"] = "1"
            env["VSCODE_DEV"] = ""
            try:
                cp = subprocess.run(
                    [str(exe), str(cli_js), "--version"],
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    timeout=8,
                    shell=False,
                    env=env,
                )
                if cp.returncode == 0:
                    first = next((x.strip() for x in cp.stdout.splitlines() if x.strip()), None)
                    version = first
            except Exception:
                pass
            return CursorCLI(str(exe), str(cli_js), version)
    raise DeveloperSessionError("Cursor CLI not found")


class DeveloperSessionManager:
    def __init__(
        self,
        config: RuntimeConfig,
        state_dir: Path,
        desktop: DesktopActionLayer,
    ):
        self.config = config
        self.roots = config.normalized_roots()
        self.state_root = state_dir.expanduser().resolve() / "developer_sessions"
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.desktop = desktop

    def resolve_workspace(self, workspace_path: str | Path) -> Path:
        path = Path(workspace_path).expanduser()
        if not path.is_absolute():
            raise DeveloperSessionError("workspace_path must be absolute")
        resolved = path.resolve(strict=False)
        if not any(_is_relative_to(resolved, root) for root in self.roots):
            raise DeveloperSessionError("workspace_path outside approved roots")
        if not resolved.is_dir():
            raise DeveloperSessionError("workspace_path is not a directory")
        return resolved

    def _session_dir(self, session_id: str) -> Path:
        if not session_id.startswith("devsess_") or any(
            ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for ch in session_id
        ):
            raise DeveloperSessionError("invalid session_id")
        return self.state_root / session_id

    def _record_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "session.json"

    def _atomic_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".mkm-devsession-", suffix=".tmp", dir=path.parent)
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

    def _repo_fact(self, workspace: Path) -> dict[str, Any]:
        def run(args: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["git", *args],
                cwd=str(workspace),
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=8,
                shell=False,
            )
        inside = run(["rev-parse", "--is-inside-work-tree"])
        if inside.returncode != 0 or inside.stdout.strip().lower() != "true":
            return {"is_git": False, "repo_root": None, "head": None}
        root = run(["rev-parse", "--show-toplevel"])
        head = run(["rev-parse", "HEAD"])
        return {
            "is_git": True,
            "repo_root": root.stdout.strip() if root.returncode == 0 else None,
            "head": head.stdout.strip() if head.returncode == 0 else None,
        }

    def prepare(self, workspace_path: str | Path) -> dict[str, Any]:
        workspace = self.resolve_workspace(workspace_path)
        cli = find_cursor_cli()
        session_id = "devsess_" + uuid.uuid4().hex
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=False)
        user_data_dir = session_dir / "cursor-user-data"
        user_data_dir.mkdir()
        marker = "MKM-WORKER-" + session_id
        workspace_file = session_dir / f"{session_id}.code-workspace"
        workspace_payload = {
            "folders": [{"path": str(workspace)}],
            "settings": {
                "window.title": marker,
            },
        }
        raw = json.dumps(workspace_payload, ensure_ascii=False, indent=2).encode("utf-8")
        workspace_file.write_bytes(raw)
        repo = self._repo_fact(workspace)

        launch_argv = [
            cli.executable,
            cli.cli_js,
            "--new-window",
            "--user-data-dir", str(user_data_dir),
            "--disable-extensions",
            "--suppress-popups-on-startup",
            str(workspace_file),
        ]
        record = {
            "schema": "mkm_developer_worker_session_v0_9",
            "session_id": session_id,
            "status": "PREPARED_NOT_STARTED",
            "created_at": _now(),
            "workspace_path": str(workspace),
            "workspace_file": str(workspace_file),
            "workspace_file_sha256": _sha_bytes(raw),
            "window_marker": marker,
            "window_marker_sha256": _sha_text(marker),
            "user_data_dir": str(user_data_dir),
            "cursor_executable": cli.executable,
            "cursor_cli_js": cli.cli_js,
            "cursor_version": cli.version,
            "launch_argv_sha256": _sha_text(json.dumps(launch_argv, ensure_ascii=False)),
            "repo": repo,
            "bound_window_pid": None,
            "bound_window_title_sha256": None,
            "started_at": None,
            "verified_at": None,
            "closed_at": None,
        }
        self._atomic_json(self._record_path(session_id), record)
        return self._public(record)

    def _load(self, session_id: str) -> dict[str, Any]:
        path = self._record_path(session_id)
        if not path.is_file():
            raise DeveloperSessionError("session not found")
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _save(self, record: dict[str, Any]) -> None:
        self._atomic_json(self._record_path(record["session_id"]), record)

    def _validate_workspace_file(self, record: dict[str, Any]) -> None:
        path = Path(record["workspace_file"])
        if not path.is_file():
            raise DeveloperSessionError("session workspace file missing")
        raw = path.read_bytes()
        if _sha_bytes(raw) != record["workspace_file_sha256"]:
            raise DeveloperSessionError("session workspace file changed")
        payload = json.loads(raw.decode("utf-8"))
        folders = payload.get("folders")
        settings = payload.get("settings") or {}
        if folders != [{"path": record["workspace_path"]}]:
            raise DeveloperSessionError("session workspace mapping changed")
        if settings.get("window.title") != record["window_marker"]:
            raise DeveloperSessionError("session window marker changed")

    def _session_pids(self, record: dict[str, Any]) -> set[int]:
        needle = os.path.normcase(os.path.abspath(record["user_data_dir"]))
        pids: set[int] = set()
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if str(proc.info.get("name") or "").lower() != "cursor.exe":
                    continue
                cmdline = proc.info.get("cmdline") or []
                normalized = [os.path.normcase(os.path.abspath(x)) if os.path.isabs(x) else os.path.normcase(x) for x in cmdline]
                joined = "\n".join(normalized)
                if needle in joined:
                    pids.add(int(proc.info["pid"]))
            except Exception:
                continue
        return pids

    def _matching_window(self, record: dict[str, Any]) -> dict[str, Any] | None:
        marker = record["window_marker"]
        session_pids = self._session_pids(record)
        if not session_pids:
            return None
        for ref in self.desktop.list_windows(max_windows=100):
            try:
                payload = self.desktop.ui_refs.resolve(ref["ui_ref"], expected_kind="window")
                selector = payload["selector"]
                pid = int(selector["process_id"])
                raw_title = str(selector.get("name") or "")
                if pid in session_pids and marker in raw_title:
                    return {
                        "window_ref": ref["ui_ref"],
                        "window_pid": pid,
                        "window_title_sha256": _sha_text(raw_title),
                        "session_process_count": len(session_pids),
                    }
            except Exception:
                continue
        return None

    def _launch(self, record: dict[str, Any]) -> None:
        env = dict(os.environ)
        env["ELECTRON_RUN_AS_NODE"] = "1"
        env["VSCODE_DEV"] = ""
        argv = [
            record["cursor_executable"],
            record["cursor_cli_js"],
            "--new-window",
            "--user-data-dir", record["user_data_dir"],
            "--disable-extensions",
            "--suppress-popups-on-startup",
            record["workspace_file"],
        ]
        cp = subprocess.run(
            argv,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=15,
            shell=False,
            env=env,
        )
        if cp.returncode != 0:
            raise DeveloperSessionError(
                "Cursor CLI launch failed: " + (cp.stderr.strip()[-500:] or str(cp.returncode))
            )

    def start(self, session_id: str, *, wait_seconds: float = 20.0) -> dict[str, Any]:
        record = self._load(session_id)
        if record["status"] != "PREPARED_NOT_STARTED":
            raise DeveloperSessionError(f"cannot start status={record['status']}")
        self._validate_workspace_file(record)
        self.resolve_workspace(record["workspace_path"])
        self._launch(record)
        deadline = time.monotonic() + max(1.0, wait_seconds)
        match = None
        while time.monotonic() <= deadline:
            match = self._matching_window(record)
            if match:
                break
            time.sleep(0.25)
        if not match:
            # Fail closed and terminate only Cursor processes that carry the
            # unique session user-data-dir.
            self._terminate_session_processes(record)
            record["status"] = "START_FAILED_NO_BOUND_WINDOW"
            self._save(record)
            raise DeveloperSessionError("Cursor session window binding not established")

        record["status"] = "BOUND_ESTABLISHED"
        record["bound_window_pid"] = match["window_pid"]
        record["bound_window_title_sha256"] = match["window_title_sha256"]
        record["started_at"] = _now()
        record["verified_at"] = _now()
        self._save(record)
        return {
            **self._public(record),
            "window_ref": match["window_ref"],
            "session_process_count": match["session_process_count"],
        }

    def verify(self, session_id: str) -> dict[str, Any]:
        record = self._load(session_id)
        if record["status"] not in {"BOUND_ESTABLISHED", "BOUND_STALE"}:
            raise DeveloperSessionError(f"session not active: {record['status']}")
        self._validate_workspace_file(record)
        self.resolve_workspace(record["workspace_path"])
        match = self._matching_window(record)
        if not match:
            record["status"] = "BOUND_STALE"
            self._save(record)
            return {
                **self._public(record),
                "binding_state": "BOUND_STALE",
                "window_ref": None,
                "session_process_count": len(self._session_pids(record)),
            }
        if int(match["window_pid"]) != int(record["bound_window_pid"]):
            # A restarted dedicated instance may be legitimate, but V0.9 does
            # not silently rebind.
            record["status"] = "BOUND_STALE"
            self._save(record)
            return {
                **self._public(record),
                "binding_state": "BOUND_STALE_PID_CHANGED",
                "window_ref": None,
                "observed_window_pid": match["window_pid"],
                "session_process_count": match["session_process_count"],
            }
        if match["window_title_sha256"] != record["bound_window_title_sha256"]:
            record["status"] = "BOUND_STALE"
            self._save(record)
            return {
                **self._public(record),
                "binding_state": "BOUND_STALE_TITLE_CHANGED",
                "window_ref": None,
                "session_process_count": match["session_process_count"],
            }

        record["status"] = "BOUND_ESTABLISHED"
        record["verified_at"] = _now()
        self._save(record)
        return {
            **self._public(record),
            "binding_state": "BOUND_ESTABLISHED",
            "window_ref": match["window_ref"],
            "session_process_count": match["session_process_count"],
        }

    def _terminate_session_processes(self, record: dict[str, Any]) -> int:
        pids = sorted(self._session_pids(record), reverse=True)
        procs = []
        for pid in pids:
            try:
                procs.append(psutil.Process(pid))
            except Exception:
                continue
        for proc in procs:
            try:
                proc.terminate()
            except Exception:
                pass
        _, alive = psutil.wait_procs(procs, timeout=4)
        for proc in alive:
            try:
                proc.kill()
            except Exception:
                pass
        return len(procs)

    def close(self, session_id: str) -> dict[str, Any]:
        record = self._load(session_id)
        count = self._terminate_session_processes(record)
        record["status"] = "CLOSED_PROCESS_ONLY"
        record["closed_at"] = _now()
        self._save(record)
        return {
            **self._public(record),
            "terminated_process_count": count,
            "session_state_retained": True,
            "user_data_deleted": False,
        }

    def _public(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "session_id": record["session_id"],
            "status": record["status"],
            "binding_state": (
                "BOUND_ESTABLISHED"
                if record["status"] == "BOUND_ESTABLISHED"
                else record["status"]
            ),
            "workspace_path": record["workspace_path"],
            "workspace_file_sha256": record["workspace_file_sha256"],
            "window_marker_sha256": record["window_marker_sha256"],
            "launch_argv_sha256": record["launch_argv_sha256"],
            "cursor_version": record["cursor_version"],
            "repo": record["repo"],
            "bound_window_pid": record["bound_window_pid"],
            "created_at": record["created_at"],
            "started_at": record["started_at"],
            "verified_at": record["verified_at"],
            "closed_at": record["closed_at"],
            "send_gate": "HOLD",
        }
