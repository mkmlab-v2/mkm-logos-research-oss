"""MKM Secure Agent Runtime V0.1 MCP stdio server.

Run directly:
    python mcp_server.py

Required environment:
    MKM_AGENT_ROOTS=C:\\workspace\\safe;F:\\MKM_SAFE
    MKM_AGENT_STATE=C:\\Users\\<user>\\.mkm-agent-runtime

Optional:
    MKM_OLLAMA_BASE_URL=http://127.0.0.1:11434

The approval state directory MUST be outside all model-accessible approved roots.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from approval import ApprovalBroker, ApprovalError
from runtime import Privacy, RuntimeConfig, RuntimeErrorV0, SecureAgentRuntime


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _privacy(value: str) -> Privacy:
    try:
        return Privacy(value.upper())
    except ValueError as exc:
        raise ValueError("privacy must be PUBLIC, INTERNAL, PERSONAL, PHI, or SECRET") from exc


def _roots_from_env() -> list[Path]:
    raw = os.environ.get("MKM_AGENT_ROOTS", "")
    roots = [Path(x) for x in raw.split(os.pathsep) if x.strip()]
    if not roots:
        raise RuntimeError(
            "MKM_AGENT_ROOTS is required; no filesystem root is exposed by default"
        )
    return roots


def build_runtime_from_env() -> tuple[SecureAgentRuntime, ApprovalBroker]:
    roots = _roots_from_env()
    state_raw = os.environ.get("MKM_AGENT_STATE", "").strip()
    if not state_raw:
        raise RuntimeError(
            "MKM_AGENT_STATE is required and must be outside approved roots"
        )
    state = Path(state_raw)
    config = RuntimeConfig(
        approved_roots=roots,
        audit_log=state / "audit" / "actions.jsonl",
        ollama_base_url=os.environ.get(
            "MKM_OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        ),
    )
    runtime = SecureAgentRuntime(config)
    broker = ApprovalBroker(state, protected_roots=config.normalized_roots())
    return runtime, broker


def create_server(runtime: SecureAgentRuntime, broker: ApprovalBroker) -> MCPServer:
    mcp = MCPServer(
        "MKM Secure Agent Runtime",
        instructions=(
            "Local-first bounded desktop tools. Reads are limited to approved roots. "
            "Writes and commands require an out-of-band local CLI approval. "
            "Never claim an approval was granted unless execute_* succeeds."
        ),
    )

    @mcp.tool()
    def runtime_status() -> dict[str, Any]:
        """Return bounded runtime configuration without secret material."""
        return {
            "approved_roots": [str(p) for p in runtime.config.normalized_roots()],
            "ollama_base_url": runtime.config.ollama_base_url,
            "write_policy": "OUT_OF_BAND_LOCAL_APPROVAL_REQUIRED",
            "command_policy": "OUT_OF_BAND_LOCAL_APPROVAL_REQUIRED",
            "delete_policy": "DENY",
            "secret_material_access": "NOT_IMPLEMENTED",
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def list_directory(path: str) -> dict[str, Any]:
        """List one approved local directory."""
        rows, receipt = runtime.list_directory(path)
        return {"entries": rows, "receipt_id": receipt.receipt_id}

    @mcp.tool()
    def read_text_file(
        path: str,
        max_chars: int = 200000,
        privacy: str = "INTERNAL",
    ) -> dict[str, Any]:
        """Read a UTF-8 text file under an approved root. SECRET is denied."""
        if max_chars < 1 or max_chars > 500000:
            raise ValueError("max_chars must be 1..500000")
        p = _privacy(privacy)
        if p == Privacy.SECRET:
            raise RuntimeErrorV0("SECRET file content is not exposed to the model")
        data, receipt = runtime.read_file(
            path, max_bytes=max_chars * 4, privacy=p
        )
        text = data.decode("utf-8-sig")
        if len(text) > max_chars:
            text = text[:max_chars]
        return {
            "text": text,
            "truncated": len(text) >= max_chars,
            "sha256": receipt.result_meta["sha256"],
            "receipt_id": receipt.receipt_id,
        }

    @mcp.tool()
    def thin_coordinate(
        path: str,
        domain: str = "LOCAL",
        topic: str = "",
        privacy: str = "INTERNAL",
    ) -> dict[str, Any]:
        """Create a SHA-256 thin coordinate for an approved local file."""
        coord, receipt = runtime.thin_coordinate(
            path,
            domain=domain,
            topic=topic or None,
            privacy=_privacy(privacy),
        )
        return {
            "coordinate": {
                "kind": coord.kind,
                "domain": coord.domain,
                "topic": coord.topic,
                "state": coord.state,
                "privacy": coord.privacy,
                "source_id": coord.source_id,
                "hash": coord.hash,
                "path": coord.path,
                "relations": coord.relations,
            },
            "receipt_id": receipt.receipt_id,
        }

    @mcp.tool()
    def request_write_text(
        path: str,
        content: str,
        privacy: str = "INTERNAL",
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Request a one-time local approval for a text write; does not write."""
        target = runtime.policy.resolve_path(path)
        p = _privacy(privacy)
        if p == Privacy.SECRET:
            raise RuntimeErrorV0("SECRET content may not be submitted through this tool")
        args = {
            "path": str(target),
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "privacy": p.value,
        }
        request = broker.request(
            action="write_text",
            target=str(target),
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": request["approval_id"],
            "status": "HUMAN_GATE",
            "expires_at": request["expires_at"],
            "content_sha256": args["content_sha256"],
            "executed": False,
        }

    @mcp.tool()
    def execute_write_text(
        path: str,
        content: str,
        approval_id: str,
        privacy: str = "INTERNAL",
    ) -> dict[str, Any]:
        """Execute an exact previously requested write after LOCAL CLI approval."""
        target = runtime.policy.resolve_path(path)
        p = _privacy(privacy)
        if p == Privacy.SECRET:
            raise RuntimeErrorV0("SECRET content may not be submitted through this tool")
        args = {
            "path": str(target),
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "privacy": p.value,
        }
        broker.consume(
            approval_id,
            action="write_text",
            target=str(target),
            args_sha256=_digest(args),
        )
        receipt = runtime.write_file(
            target,
            content.encode("utf-8"),
            human_approved=True,
            privacy=p,
        )
        return {
            "executed": True,
            "receipt_id": receipt.receipt_id,
            "after_sha256": receipt.result_meta["after_sha256"],
            "semantic_state": receipt.semantic_state,
            "send_gate": receipt.send_gate,
        }

    @mcp.tool()
    def request_command(
        argv: list[str],
        cwd: str,
        timeout_seconds: float = 30.0,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Request local approval for an exact argv command; does not execute."""
        target = runtime.policy.resolve_path(cwd)
        safe_argv = runtime.policy.validate_argv(argv)
        if timeout_seconds <= 0 or timeout_seconds > 300:
            raise ValueError("timeout_seconds must be >0 and <=300")
        args = {
            "argv": safe_argv,
            "cwd": str(target),
            "timeout_seconds": timeout_seconds,
        }
        request = broker.request(
            action="run_command",
            target=str(target),
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": request["approval_id"],
            "status": "HUMAN_GATE",
            "expires_at": request["expires_at"],
            "argv_sha256": _digest(safe_argv),
            "executed": False,
        }

    @mcp.tool()
    def execute_command(
        argv: list[str],
        cwd: str,
        approval_id: str,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        """Execute an exact command after LOCAL CLI approval."""
        target = runtime.policy.resolve_path(cwd)
        safe_argv = runtime.policy.validate_argv(argv)
        if timeout_seconds <= 0 or timeout_seconds > 300:
            raise ValueError("timeout_seconds must be >0 and <=300")
        args = {
            "argv": safe_argv,
            "cwd": str(target),
            "timeout_seconds": timeout_seconds,
        }
        broker.consume(
            approval_id,
            action="run_command",
            target=str(target),
            args_sha256=_digest(args),
        )
        cp, receipt = runtime.run_command(
            safe_argv,
            cwd=target,
            human_approved=True,
            timeout=timeout_seconds,
        )
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout[-200000:],
            "stderr": cp.stderr[-50000:],
            "receipt_id": receipt.receipt_id,
            "semantic_state": receipt.semantic_state,
            "send_gate": receipt.send_gate,
        }

    @mcp.tool()
    def ollama_health() -> dict[str, Any]:
        """Check the configured loopback-only Ollama endpoint."""
        return runtime.ollama.health(timeout=2.0)

    @mcp.tool()
    def ollama_generate(
        model: str,
        prompt: str,
        privacy: str = "INTERNAL",
        timeout_seconds: float = 60.0,
    ) -> dict[str, Any]:
        """Run local Ollama inference. PHI defaults to HOLD; SECRET is denied."""
        result, receipt = runtime.ollama_generate(
            model=model,
            prompt=prompt,
            privacy=_privacy(privacy),
            timeout=timeout_seconds,
        )
        return {
            "response": result,
            "receipt_id": receipt.receipt_id,
            "semantic_state": receipt.semantic_state,
        }

    return mcp


def main() -> None:
    runtime, broker = build_runtime_from_env()
    mcp = create_server(runtime, broker)
    mcp.run()


if __name__ == "__main__":
    main()
