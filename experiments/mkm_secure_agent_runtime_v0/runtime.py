"""MKM Secure Agent Runtime V0.

Local-first execution layer for bounded desktop-agent actions.

V0 properties:
- explicit approved roots
- fail-closed path checks
- real list/read/write file tools
- argv-only command execution (never shell=True)
- HUMAN_GATE for writes/commands/secret use
- local-only Ollama endpoint guard
- secret handles only; secret material is never stored here
- thin file coordinates with SHA-256 identity
- append-only JSONL action receipts without prompt/file contents

Not authorized in V0:
- password retrieval/storage
- browser GUI automation
- remote relay
- PHI production workflow
- arbitrary shell strings
- delete/move/destructive cleanup
- git push / deploy / SEND
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import uuid


class RuntimeErrorV0(RuntimeError):
    pass


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    HUMAN_GATE = "HUMAN_GATE"
    HOLD = "HOLD"


class Privacy(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    PERSONAL = "PERSONAL"
    PHI = "PHI"
    SECRET = "SECRET"


@dataclass(frozen=True)
class ThinCoordinate:
    kind: str
    domain: str
    topic: str
    state: str
    privacy: str
    source_id: str
    hash: str | None
    path: str | None
    relations: list[dict[str, str]]


@dataclass(frozen=True)
class ActionReceipt:
    schema: str
    receipt_id: str
    created_at: str
    action: str
    decision: str
    target: str | None
    args_sha256: str
    success: bool
    result_meta: dict[str, Any]
    semantic_state: str
    send_gate: str


@dataclass
class RuntimeConfig:
    approved_roots: list[Path]
    audit_log: Path
    allowed_executables: tuple[str, ...] = ("git", "python", "python3", "pytest")
    blocked_git_subcommands: tuple[str, ...] = (
        "push", "fetch", "pull", "clone", "remote", "gc", "clean", "reset",
        "checkout", "switch", "branch", "merge", "rebase", "tag", "commit",
    )
    ollama_base_url: str = "http://127.0.0.1:11434"
    allow_phi_local_model: bool = False

    def normalized_roots(self) -> list[Path]:
        roots = [p.expanduser().resolve() for p in self.approved_roots]
        if not roots:
            raise RuntimeErrorV0("at least one approved root is required")
        return roots


class SecretHandle:
    """Opaque reference only. This class intentionally cannot hold a secret value."""

    __slots__ = ("_ref",)

    def __init__(self, ref: str):
        ref = ref.strip()
        if not ref.startswith("secret://") or len(ref) <= len("secret://"):
            raise RuntimeErrorV0("secret handle must use secret://<id>")
        if any(ch.isspace() for ch in ref):
            raise RuntimeErrorV0("secret handle cannot contain whitespace")
        self._ref = ref

    @property
    def ref(self) -> str:
        return self._ref

    def __repr__(self) -> str:
        return "SecretHandle(<opaque>)"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256_bytes(raw.encode("utf-8"))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


class PolicyEngine:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.roots = config.normalized_roots()

    def resolve_path(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            raise RuntimeErrorV0("target path must be absolute")
        resolved = path.resolve(strict=False)
        if not any(_is_relative_to(resolved, root) for root in self.roots):
            raise RuntimeErrorV0("target path is outside approved roots")
        return resolved

    def decide(self, action: str, *, privacy: Privacy = Privacy.INTERNAL,
               human_approved: bool = False) -> Decision:
        if privacy == Privacy.SECRET and action not in {"secret_handle_use"}:
            return Decision.DENY

        if action in {"list_directory", "read_file", "thin_coordinate"}:
            return Decision.ALLOW

        if action == "ollama_generate":
            if privacy == Privacy.SECRET:
                return Decision.DENY
            if privacy == Privacy.PHI and not self.config.allow_phi_local_model:
                return Decision.HOLD
            return Decision.ALLOW

        if action in {"write_file", "run_command", "secret_handle_use"}:
            return Decision.ALLOW if human_approved else Decision.HUMAN_GATE

        if action in {
            "delete_file", "move_file", "git_push", "deploy", "send",
            "credential_read", "credential_export", "remote_control",
        }:
            return Decision.DENY

        return Decision.HOLD

    def validate_argv(self, argv: list[str]) -> list[str]:
        if not argv or not all(isinstance(x, str) and x for x in argv):
            raise RuntimeErrorV0("argv must be a non-empty list of strings")
        exe = Path(argv[0]).name.lower()
        allowed = {x.lower() for x in self.config.allowed_executables}
        if exe.endswith(".exe"):
            exe = exe[:-4]
        if exe not in allowed:
            raise RuntimeErrorV0(f"executable not allowed: {argv[0]}")

        if exe == "git" and len(argv) >= 2:
            sub = argv[1].lower()
            if sub in {x.lower() for x in self.config.blocked_git_subcommands}:
                raise RuntimeErrorV0(f"git subcommand blocked in V0: {sub}")
        return argv


class ReceiptLog:
    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()

    def append(self, receipt: ActionReceipt) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(receipt), ensure_ascii=False, sort_keys=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")


class OllamaGateway:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"}:
            raise RuntimeErrorV0("Ollama URL must be http(s)")
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise RuntimeErrorV0("V0 Ollama endpoint must be loopback-only")

    def health(self, timeout: float = 2.0) -> dict[str, Any]:
        req = Request(self.base_url + "/api/tags", method="GET")
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return {"status": resp.status, "bytes": len(body)}

    def generate(self, *, model: str, prompt: str, timeout: float = 60.0) -> str:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")
        req = Request(
            self.base_url + "/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        value = data.get("response")
        if not isinstance(value, str):
            raise RuntimeErrorV0("invalid Ollama response")
        return value


class SecureAgentRuntime:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.policy = PolicyEngine(config)
        self.receipts = ReceiptLog(config.audit_log)
        self.ollama = OllamaGateway(config.ollama_base_url)

    def _receipt(self, *, action: str, decision: Decision, target: str | None,
                 args: Any, success: bool, result_meta: dict[str, Any]) -> ActionReceipt:
        receipt = ActionReceipt(
            schema="mkm_secure_agent_action_receipt_v0",
            receipt_id=f"rcpt:{uuid.uuid4().hex}",
            created_at=_now(),
            action=action,
            decision=decision.value,
            target=target,
            args_sha256=_json_digest(args),
            success=success,
            result_meta=result_meta,
            semantic_state="NOT_ADJUDICATED",
            send_gate="HOLD",
        )
        self.receipts.append(receipt)
        return receipt

    def list_directory(self, path: str | Path) -> tuple[list[dict[str, Any]], ActionReceipt]:
        target = self.policy.resolve_path(path)
        decision = self.policy.decide("list_directory")
        if decision != Decision.ALLOW:
            raise RuntimeErrorV0(f"list denied: {decision.value}")
        if not target.is_dir():
            raise RuntimeErrorV0("target is not a directory")
        rows = [
            {"name": p.name, "type": "dir" if p.is_dir() else "file"}
            for p in sorted(target.iterdir(), key=lambda x: x.name.lower())
        ]
        receipt = self._receipt(
            action="list_directory", decision=decision, target=str(target),
            args={"path": str(target)}, success=True, result_meta={"entries": len(rows)},
        )
        return rows, receipt

    def read_file(self, path: str | Path, *, max_bytes: int = 1024 * 1024,
                  privacy: Privacy = Privacy.INTERNAL) -> tuple[bytes, ActionReceipt]:
        target = self.policy.resolve_path(path)
        decision = self.policy.decide("read_file", privacy=privacy)
        if decision != Decision.ALLOW:
            raise RuntimeErrorV0(f"read denied: {decision.value}")
        if not target.is_file():
            raise RuntimeErrorV0("target is not a file")
        size = target.stat().st_size
        if size > max_bytes:
            raise RuntimeErrorV0(f"file exceeds max_bytes ({size} > {max_bytes})")
        data = target.read_bytes()
        receipt = self._receipt(
            action="read_file", decision=decision, target=str(target),
            args={"path": str(target), "max_bytes": max_bytes, "privacy": privacy.value},
            success=True,
            result_meta={"bytes": len(data), "sha256": _sha256_bytes(data)},
        )
        return data, receipt

    def write_file(self, path: str | Path, data: bytes, *,
                   human_approved: bool = False,
                   privacy: Privacy = Privacy.INTERNAL) -> ActionReceipt:
        target = self.policy.resolve_path(path)
        decision = self.policy.decide(
            "write_file", privacy=privacy, human_approved=human_approved
        )
        if decision != Decision.ALLOW:
            receipt = self._receipt(
                action="write_file", decision=decision, target=str(target),
                args={"path": str(target), "bytes": len(data), "privacy": privacy.value},
                success=False, result_meta={"executed": False},
            )
            raise RuntimeErrorV0(f"write requires gate: {receipt.decision}")

        target.parent.mkdir(parents=True, exist_ok=True)
        before_hash = _sha256_file(target) if target.is_file() else None
        tmp = target.with_name(target.name + f".mkm-tmp-{uuid.uuid4().hex[:8]}")
        tmp.write_bytes(data)
        tmp.replace(target)
        return self._receipt(
            action="write_file", decision=decision, target=str(target),
            args={"path": str(target), "bytes": len(data), "privacy": privacy.value},
            success=True,
            result_meta={
                "executed": True,
                "before_sha256": before_hash,
                "after_sha256": _sha256_bytes(data),
            },
        )

    def thin_coordinate(self, path: str | Path, *, domain: str = "LOCAL",
                        topic: str | None = None,
                        privacy: Privacy = Privacy.INTERNAL) -> tuple[ThinCoordinate, ActionReceipt]:
        target = self.policy.resolve_path(path)
        decision = self.policy.decide("thin_coordinate", privacy=privacy)
        if decision != Decision.ALLOW:
            raise RuntimeErrorV0(f"coordinate denied: {decision.value}")
        if not target.is_file():
            raise RuntimeErrorV0("coordinate target must be a file")
        digest = _sha256_file(target)
        coord = ThinCoordinate(
            kind="SOURCE",
            domain=domain,
            topic=topic or target.name,
            state="CANDIDATE",
            privacy=privacy.value,
            source_id=f"src:{digest[:16]}",
            hash=digest,
            path=str(target),
            relations=[],
        )
        receipt = self._receipt(
            action="thin_coordinate", decision=decision, target=str(target),
            args={"path": str(target), "domain": domain, "topic": topic, "privacy": privacy.value},
            success=True, result_meta={"source_id": coord.source_id, "sha256": digest},
        )
        return coord, receipt

    def run_command(self, argv: list[str], *, cwd: str | Path,
                    human_approved: bool = False, timeout: float = 30.0) -> tuple[subprocess.CompletedProcess[str], ActionReceipt]:
        workdir = self.policy.resolve_path(cwd)
        decision = self.policy.decide("run_command", human_approved=human_approved)
        safe_argv = self.policy.validate_argv(argv)
        if decision != Decision.ALLOW:
            receipt = self._receipt(
                action="run_command", decision=decision, target=str(workdir),
                args={"argv": safe_argv, "cwd": str(workdir), "timeout": timeout},
                success=False, result_meta={"executed": False},
            )
            raise RuntimeErrorV0(f"command requires gate: {receipt.decision}")
        cp = subprocess.run(
            safe_argv, cwd=str(workdir), text=True, capture_output=True,
            timeout=timeout, shell=False,
        )
        receipt = self._receipt(
            action="run_command", decision=decision, target=str(workdir),
            args={"argv": safe_argv, "cwd": str(workdir), "timeout": timeout},
            success=cp.returncode == 0,
            result_meta={
                "executed": True,
                "returncode": cp.returncode,
                "stdout_sha256": _sha256_bytes(cp.stdout.encode("utf-8", errors="replace")),
                "stderr_sha256": _sha256_bytes(cp.stderr.encode("utf-8", errors="replace")),
            },
        )
        return cp, receipt

    def use_secret_handle(self, handle: SecretHandle, *, purpose: str,
                          human_approved: bool = False) -> ActionReceipt:
        decision = self.policy.decide("secret_handle_use", privacy=Privacy.SECRET,
                                      human_approved=human_approved)
        # V0 never resolves a real secret. Approval only records that the opaque
        # reference may be handed to a future OS-backed broker.
        return self._receipt(
            action="secret_handle_use", decision=decision, target=handle.ref,
            args={"secret_ref": handle.ref, "purpose": purpose},
            success=False,
            result_meta={"secret_material_exposed": False, "resolved": False},
        )

    def ollama_generate(self, *, model: str, prompt: str,
                        privacy: Privacy = Privacy.INTERNAL,
                        timeout: float = 60.0) -> tuple[str, ActionReceipt]:
        decision = self.policy.decide("ollama_generate", privacy=privacy)
        if decision != Decision.ALLOW:
            receipt = self._receipt(
                action="ollama_generate", decision=decision, target=self.config.ollama_base_url,
                args={"model": model, "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")), "privacy": privacy.value},
                success=False, result_meta={"executed": False, "prompt_logged": False},
            )
            raise RuntimeErrorV0(f"Ollama request blocked: {receipt.decision}")
        result = self.ollama.generate(model=model, prompt=prompt, timeout=timeout)
        receipt = self._receipt(
            action="ollama_generate", decision=decision, target=self.config.ollama_base_url,
            args={"model": model, "prompt_sha256": _sha256_bytes(prompt.encode("utf-8")), "privacy": privacy.value},
            success=True,
            result_meta={
                "executed": True,
                "prompt_logged": False,
                "response_bytes": len(result.encode("utf-8")),
                "response_sha256": _sha256_bytes(result.encode("utf-8")),
            },
        )
        return result, receipt
