from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from .models import AuthorityContract, WorkspaceBinding


class AuthorityResolverError(RuntimeError):
    pass


class SourceClass:
    AUTHORITATIVE = "AUTHORITATIVE"
    WORKING_MIRROR = "WORKING_MIRROR"
    TASK_WORKTREE = "TASK_WORKTREE"
    VALIDATION_CLONE = "VALIDATION_CLONE"
    ARCHIVE = "ARCHIVE"
    BACKUP = "BACKUP"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"


_MARKER = ".mkm-source-role.json"
_EXPLICIT_ROLES = {
    SourceClass.VALIDATION_CLONE,
    SourceClass.ARCHIVE,
    SourceClass.BACKUP,
}


def _norm(path: str | Path) -> str:
    return os.path.normcase(str(Path(path).expanduser().resolve()))


def _git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=15,
        shell=False,
    )


def _git_facts(path: str | Path) -> dict[str, Any]:
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return {"state": "UNKNOWN", "reason": "PATH_NOT_FOUND", "path": str(root)}
    cp = _git(root, ["rev-parse", "--show-toplevel"])
    if cp.returncode != 0:
        return {"state": "UNKNOWN", "reason": "NOT_A_GIT_WORKTREE", "path": str(root)}
    repo_root = Path(cp.stdout.strip()).resolve()
    head = _git(repo_root, ["rev-parse", "HEAD"])
    common = _git(repo_root, ["rev-parse", "--git-common-dir"])
    branch = _git(repo_root, ["branch", "--show-current"])
    origin = _git(repo_root, ["remote", "get-url", "origin"])
    common_path = common.stdout.strip()
    if not os.path.isabs(common_path):
        common_path = str((repo_root / common_path).resolve())
    return {
        "state": "FACT",
        "path": str(root),
        "repo_root": str(repo_root),
        "head": head.stdout.strip() if head.returncode == 0 else "UNKNOWN",
        "branch": branch.stdout.strip() if branch.returncode == 0 else "",
        "git_common_dir": _norm(common_path),
        "origin": origin.stdout.strip() if origin.returncode == 0 else None,
    }


def write_role_marker(
    repo_root: str | Path,
    *,
    role: str,
    authority_repository_id: str,
    authority_base_revision: str,
) -> Path:
    if role not in _EXPLICIT_ROLES:
        raise ValueError("role marker may only declare validation/archive/backup")
    root = Path(repo_root).expanduser().resolve()
    path = root / _MARKER
    payload = {
        "schema": "mkm_source_role_v0",
        "role": role,
        "authority_repository_id": authority_repository_id,
        "authority_base_revision": authority_base_revision,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


class AuthorityResolver:
    """Classifies local sources without inferring authority from recency or remote name."""

    def __init__(self, authority: AuthorityContract):
        authority.validate()
        self.authority = authority

    def resolve(
        self,
        candidate_path: str | Path,
        *,
        task_binding: WorkspaceBinding | None = None,
    ) -> dict[str, Any]:
        authoritative = _git_facts(self.authority.repository_path)
        candidate = _git_facts(candidate_path)

        if authoritative.get("state") != "FACT":
            return self._result(
                SourceClass.CONFLICT,
                "DECLARED_AUTHORITY_PATH_NOT_GIT",
                authoritative,
                candidate,
            )

        verify = _git(
            Path(authoritative["repo_root"]),
            ["rev-parse", "--verify", f"{self.authority.base_revision}^{{commit}}"],
        )
        if verify.returncode != 0:
            return self._result(
                SourceClass.CONFLICT,
                "DECLARED_BASE_REVISION_NOT_FOUND_IN_AUTHORITY",
                authoritative,
                candidate,
            )

        if candidate.get("state") != "FACT":
            marker = self._read_marker(Path(candidate_path))
            if marker:
                return self._marker_non_git(marker, authoritative, candidate)
            return self._result(
                SourceClass.UNKNOWN,
                candidate.get("reason", "CANDIDATE_NOT_ESTABLISHED"),
                authoritative,
                candidate,
            )

        if _norm(candidate["repo_root"]) == _norm(authoritative["repo_root"]):
            source_class = (
                SourceClass.AUTHORITATIVE
                if self.authority.source_kind == "AUTHORITATIVE"
                else SourceClass.WORKING_MIRROR
            )
            return self._result(
                source_class,
                "EXACT_DECLARED_REPOSITORY_PATH",
                authoritative,
                candidate,
            )

        if candidate["git_common_dir"] == authoritative["git_common_dir"]:
            if (
                task_binding is not None
                and _norm(candidate["repo_root"]) == _norm(task_binding.worktree_path)
                and task_binding.base_revision == verify.stdout.strip()
            ):
                return self._result(
                    SourceClass.TASK_WORKTREE,
                    "EXACT_TASK_BINDING_AND_SHARED_GIT_COMMON_DIR",
                    authoritative,
                    candidate,
                )
            return self._result(
                SourceClass.UNKNOWN,
                "UNBOUND_LINKED_WORKTREE",
                authoritative,
                candidate,
            )

        marker = self._read_marker(Path(candidate["repo_root"]))
        if marker:
            return self._marker_git(marker, authoritative, candidate)

        same_origin = (
            authoritative.get("origin")
            and candidate.get("origin")
            and authoritative["origin"] == candidate["origin"]
        )
        if same_origin:
            return self._result(
                SourceClass.UNKNOWN,
                "SAME_REMOTE_SEPARATE_CLONE_WITHOUT_ROLE_MARKER",
                authoritative,
                candidate,
            )

        return self._result(
            SourceClass.UNKNOWN,
            "NO_PROVEN_AUTHORITY_RELATION",
            authoritative,
            candidate,
        )

    def _read_marker(self, root: Path) -> dict[str, Any] | None:
        path = root.expanduser().resolve() / _MARKER
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {
                "schema": "INVALID",
                "role": "INVALID",
            }
        return payload

    def _validate_marker(self, marker: dict[str, Any]) -> tuple[bool, str]:
        if marker.get("schema") != "mkm_source_role_v0":
            return False, "ROLE_MARKER_SCHEMA_INVALID"
        role = marker.get("role")
        if role not in _EXPLICIT_ROLES:
            return False, "ROLE_MARKER_ROLE_INVALID"
        if marker.get("authority_repository_id") != self.authority.repository_id:
            return False, "ROLE_MARKER_REPOSITORY_CONFLICT"
        if marker.get("authority_base_revision") != self.authority.base_revision:
            return False, "ROLE_MARKER_BASE_REVISION_CONFLICT"
        return True, role

    def _marker_non_git(
        self,
        marker: dict[str, Any],
        authoritative: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        ok, value = self._validate_marker(marker)
        if not ok:
            return self._result(SourceClass.CONFLICT, value, authoritative, candidate)
        if value in {SourceClass.ARCHIVE, SourceClass.BACKUP}:
            return self._result(
                value,
                "EXPLICIT_ROLE_MARKER_NON_GIT",
                authoritative,
                candidate,
            )
        return self._result(
            SourceClass.CONFLICT,
            "VALIDATION_CLONE_MARKER_REQUIRES_GIT",
            authoritative,
            candidate,
        )

    def _marker_git(
        self,
        marker: dict[str, Any],
        authoritative: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        ok, value = self._validate_marker(marker)
        if not ok:
            return self._result(SourceClass.CONFLICT, value, authoritative, candidate)
        if value == SourceClass.VALIDATION_CLONE:
            base = _git(
                Path(candidate["repo_root"]),
                ["rev-parse", "--verify", f"{self.authority.base_revision}^{{commit}}"],
            )
            if base.returncode != 0:
                return self._result(
                    SourceClass.CONFLICT,
                    "VALIDATION_CLONE_MISSING_DECLARED_BASE",
                    authoritative,
                    candidate,
                )
            if (
                authoritative.get("origin")
                and candidate.get("origin")
                and authoritative["origin"] != candidate["origin"]
            ):
                return self._result(
                    SourceClass.CONFLICT,
                    "VALIDATION_CLONE_REMOTE_CONFLICT",
                    authoritative,
                    candidate,
                )
        return self._result(
            value,
            "EXPLICIT_ROLE_MARKER_MATCH",
            authoritative,
            candidate,
        )

    def _result(
        self,
        source_class: str,
        reason: str,
        authoritative: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "source_class": source_class,
            "reason": reason,
            "authority_repository_id": self.authority.repository_id,
            "declared_source_kind": self.authority.source_kind,
            "declared_base_revision": self.authority.base_revision,
            "authoritative_facts": authoritative,
            "candidate_facts": candidate,
            "promotion_authorized": False,
        }
