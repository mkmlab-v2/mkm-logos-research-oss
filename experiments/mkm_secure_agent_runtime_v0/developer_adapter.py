"""Bounded developer workspace adapter for MKM Secure Agent Runtime V0.8.

Semantic actions only:
- bind an observed VS Code/Cursor window to an explicitly supplied approved workspace
- read Git status / bounded diff
- detect a fixed pytest profile
- request/execute only the exact fixed pytest profile through HUMAN_GATE

No arbitrary terminal strings, git mutation, push, commit, deploy, package install,
secret injection, or SEND.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from app_adapters import AppAdapterLayer
from privacy import scan_text
from runtime import RuntimeConfig, RuntimeErrorV0


class DeveloperAdapterError(RuntimeError):
    pass


DEV_GIT_OBSERVE = "DEV_GIT_OBSERVE"
DEV_TEST_PYTEST = "DEV_TEST_PYTEST"
_DEVELOPER_ADAPTERS = {"editor.vscode.v0", "editor.cursor.v0"}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _scan_release(text: str) -> dict[str, Any]:
    result = scan_text(text)
    if result.release_decision == "ALLOW":
        return {
            "blocked": False,
            "text": text,
            "privacy_state": result.state,
            "release_decision": result.release_decision,
            "sha256": _sha(text),
        }
    return {
        "blocked": True,
        "text": None,
        "privacy_state": result.state,
        "release_decision": result.release_decision,
        "signal_counts": result.signal_counts,
        "limitations": result.limitations,
        "sha256": _sha(text),
    }


@dataclass(frozen=True)
class TestProfile:
    profile_id: str
    argv: tuple[str, ...]
    reason: str


class DeveloperWorkspaceAdapter:
    def __init__(self, config: RuntimeConfig, app_layer: AppAdapterLayer):
        self.config = config
        self.app_layer = app_layer
        self.roots = config.normalized_roots()

    def resolve_workspace(self, workspace_path: str | Path) -> Path:
        path = Path(workspace_path).expanduser()
        if not path.is_absolute():
            raise DeveloperAdapterError("workspace_path must be absolute")
        resolved = path.resolve(strict=False)
        if not any(_is_relative_to(resolved, root) for root in self.roots):
            raise DeveloperAdapterError("workspace_path outside approved roots")
        if not resolved.is_dir():
            raise DeveloperAdapterError("workspace_path is not a directory")
        return resolved

    def bind(self, window_ref: str, workspace_path: str | Path) -> dict[str, Any]:
        identity = self.app_layer.identify_window(window_ref)
        adapter = identity["adapter"]
        adapter_id = adapter["adapter_id"]
        if adapter_id not in _DEVELOPER_ADAPTERS:
            raise DeveloperAdapterError(
                f"developer workspace adapter denied for app: {adapter_id}"
            )
        workspace = self.resolve_workspace(workspace_path)
        return {
            "window_ref": window_ref,
            "workspace_path": str(workspace),
            "adapter_id": adapter_id,
            "process_name": identity["process_name"],
            "binding_state": "REQUEST_SCOPED_PAIR_ASSOCIATION_NOT_ESTABLISHED",
        }

    def _git(self, workspace: Path, argv: list[str], *, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
        safe = ["git", *argv]
        # Only fixed read-only subcommands are reachable here.
        if not argv or argv[0] not in {"status", "diff", "rev-parse"}:
            raise DeveloperAdapterError("developer git operation not allowed")
        try:
            return subprocess.run(
                safe,
                cwd=str(workspace),
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DeveloperAdapterError("developer git operation timed out") from exc

    def _ensure_git_repo(self, workspace: Path) -> None:
        cp = self._git(workspace, ["rev-parse", "--is-inside-work-tree"])
        if cp.returncode != 0 or cp.stdout.strip().lower() != "true":
            raise DeveloperAdapterError("workspace is not a Git worktree")

    def status(self, window_ref: str, workspace_path: str | Path) -> dict[str, Any]:
        binding = self.bind(window_ref, workspace_path)
        workspace = Path(binding["workspace_path"])
        self._ensure_git_repo(workspace)
        cp = self._git(workspace, ["status", "--porcelain=v1", "-b"])
        if cp.returncode != 0:
            raise DeveloperAdapterError("git status failed")
        lines = [line for line in cp.stdout.splitlines() if line.strip()]
        branch_line = lines[0] if lines and lines[0].startswith("## ") else ""
        entries = lines[1:] if branch_line else lines
        safe_entries = []
        blocked_count = 0
        for line in entries[:500]:
            released = _scan_release(line)
            if released["blocked"]:
                blocked_count += 1
                safe_entries.append({
                    "status": line[:2],
                    "path": "[SENSITIVE_PATH]",
                    "sha256": released["sha256"],
                    "privacy_state": released["privacy_state"],
                })
            else:
                safe_entries.append({
                    "status": line[:2],
                    "path": line[3:] if len(line) > 3 else "",
                })
        return {
            **binding,
            "git": {
                "branch": _scan_release(branch_line),
                "entry_count": len(entries),
                "entries": safe_entries,
                "truncated": len(entries) > 500,
                "sensitive_entry_count": blocked_count,
            },
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        }

    def diff(
        self,
        window_ref: str,
        workspace_path: str | Path,
        *,
        staged: bool = False,
        max_chars: int = 120000,
    ) -> dict[str, Any]:
        if max_chars < 1 or max_chars > 300000:
            raise DeveloperAdapterError("max_chars must be 1..300000")
        binding = self.bind(window_ref, workspace_path)
        workspace = Path(binding["workspace_path"])
        self._ensure_git_repo(workspace)
        argv = ["diff", "--no-ext-diff", "--no-color"]
        if staged:
            argv.append("--cached")
        cp = self._git(workspace, argv, timeout=15.0)
        if cp.returncode != 0:
            raise DeveloperAdapterError("git diff failed")
        raw = cp.stdout
        clipped = raw[:max_chars]
        release = _scan_release(clipped)
        return {
            **binding,
            "staged": staged,
            "diff": release,
            "truncated": len(raw) > max_chars,
            "total_chars": len(raw),
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        }

    def detect_test_profile(
        self,
        window_ref: str,
        workspace_path: str | Path,
    ) -> dict[str, Any]:
        binding = self.bind(window_ref, workspace_path)
        workspace = Path(binding["workspace_path"])
        markers = [
            workspace / "pytest.ini",
            workspace / "pyproject.toml",
            workspace / "setup.cfg",
            workspace / "tox.ini",
            workspace / "tests",
        ]
        observed = [p.name for p in markers if p.exists()]
        if not observed:
            return {
                **binding,
                "profile": None,
                "status": "NOT_ESTABLISHED",
                "reason": "NO_PYTEST_MARKER_OBSERVED",
                "send_gate": "HOLD",
            }
        profile = TestProfile(
            profile_id="pytest.quiet.v0",
            argv=("python", "-m", "pytest", "-q"),
            reason="PYTEST_MARKER_OBSERVED",
        )
        return {
            **binding,
            "profile": {
                "profile_id": profile.profile_id,
                "argv": list(profile.argv),
                "reason": profile.reason,
                "markers": observed,
            },
            "status": "CANDIDATE",
            "send_gate": "HOLD",
        }

    def exact_test_argv(
        self,
        window_ref: str,
        workspace_path: str | Path,
        profile_id: str,
    ) -> tuple[dict[str, Any], list[str]]:
        detected = self.detect_test_profile(window_ref, workspace_path)
        profile = detected.get("profile")
        if profile is None or profile.get("profile_id") != profile_id:
            raise DeveloperAdapterError("test profile not available")
        argv = list(profile["argv"])
        return detected, argv

    def sanitize_test_output(self, stdout: str, stderr: str) -> dict[str, Any]:
        return {
            "stdout": _scan_release(stdout[-200000:]),
            "stderr": _scan_release(stderr[-100000:]),
        }
