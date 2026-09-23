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
from privacy import scan_text
from runtime import Privacy, RuntimeConfig, RuntimeErrorV0, SecureAgentRuntime
from secrets_dpapi import DPAPISecretStore, SecretStoreError
from snapshot import SnapshotStore, SnapshotError
from desktop_ui import DesktopActionLayer, DesktopUIError
from ui_refs import UIRefStore, UIRefError
from app_adapters import (
    AppAdapterLayer,
    AppAdapterRegistry,
    AppAdapterError,
    CLICK_LOW_RISK,
    SET_TEXT_CLEAN,
)
from developer_adapter import DeveloperWorkspaceAdapter, DeveloperAdapterError
from developer_session import DeveloperSessionManager, DeveloperSessionError
from cursor_agent_bridge import CursorAgentBridge, CursorAgentBridgeError


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


def create_server(
    runtime: SecureAgentRuntime,
    broker: ApprovalBroker,
    secret_store: DPAPISecretStore | None = None,
    snapshot_store: SnapshotStore | None = None,
    desktop_layer: DesktopActionLayer | None = None,
    app_layer: AppAdapterLayer | None = None,
    developer_layer: DeveloperWorkspaceAdapter | None = None,
    session_manager: DeveloperSessionManager | None = None,
    cursor_agent_bridge: CursorAgentBridge | None = None,
) -> MCPServer:
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
            "secret_material_access": (
                "LOCAL_DPAPI_METADATA_ONLY" if secret_store is not None else "UNAVAILABLE"
            ),
            "rollback": (
                "LOCAL_DPAPI_SNAPSHOT_AVAILABLE" if snapshot_store is not None else "UNAVAILABLE"
            ),
            "desktop_actions": (
                "WINDOWS_UIA_HUMAN_GATE" if desktop_layer is not None else "UNAVAILABLE"
            ),
            "app_adapters": (
                "REQUIRED_FOR_UI_MUTATION" if app_layer is not None else "UNAVAILABLE"
            ),
            "developer_adapter": (
                "SEMANTIC_VSCODE_CURSOR_BOUNDED" if developer_layer is not None else "UNAVAILABLE"
            ),
            "developer_worker_session": (
                "DEDICATED_CURSOR_BINDING_V0_9" if session_manager is not None else "UNAVAILABLE"
            ),
            "cursor_agent_worker": (
                "FAIL_CLOSED_SESSION_BRIDGE_REQUIRED"
                if cursor_agent_bridge is not None and session_manager is not None
                else "UNAVAILABLE"
            ),
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def list_directory(path: str) -> dict[str, Any]:
        """List one approved local directory."""
        rows, receipt = runtime.list_directory(path)
        return {"entries": rows, "receipt_id": receipt.receipt_id}

    @mcp.tool()
    def secret_handle_info(handle: str) -> dict[str, Any]:
        """Return metadata for a known secret handle. Never returns secret material."""
        if secret_store is None:
            return {
                "available": False,
                "reason": "WINDOWS_DPAPI_STORE_UNAVAILABLE",
                "secret_material_exposed": False,
            }
        try:
            meta = secret_store.metadata(handle)
        except SecretStoreError as exc:
            return {
                "available": False,
                "reason": str(exc),
                "secret_material_exposed": False,
            }
        return {
            "available": True,
            "handle": meta.handle,
            "service": meta.service,
            "label": meta.label,
            "created_at": meta.created_at,
            "updated_at": meta.updated_at,
            "provider": meta.provider,
            "secret_material_exposed": False,
        }

    @mcp.tool()
    def read_text_file(
        path: str,
        max_chars: int = 200000,
        privacy: str = "INTERNAL",
    ) -> dict[str, Any]:
        """Read a UTF-8 text file only after local deterministic privacy scan."""
        if max_chars < 1 or max_chars > 500000:
            raise ValueError("max_chars must be 1..500000")
        declared = _privacy(privacy)
        if declared == Privacy.SECRET:
            raise RuntimeErrorV0("SECRET file content is not exposed to the model")
        data, receipt = runtime.read_file(
            path, max_bytes=max_chars * 4, privacy=Privacy.INTERNAL
        )
        text = data.decode("utf-8-sig")
        if len(text) > max_chars:
            text = text[:max_chars]
            truncated = True
        else:
            truncated = False

        scan = scan_text(text)
        effective_state = scan.state
        if declared.value in {"PERSONAL", "PHI"}:
            effective_state = declared.value

        if scan.state == "SECRET":
            return {
                "text": None,
                "blocked": True,
                "privacy_state": "SECRET",
                "release_decision": "DENY",
                "signal_counts": scan.signal_counts,
                "limitations": scan.limitations,
                "sha256": receipt.result_meta["sha256"],
                "receipt_id": receipt.receipt_id,
            }
        if effective_state in {"PERSONAL", "PHI"}:
            return {
                "text": None,
                "blocked": True,
                "privacy_state": effective_state,
                "release_decision": "HOLD",
                "signal_counts": scan.signal_counts,
                "medical_context": scan.medical_context,
                "manual_review_required": True,
                "limitations": scan.limitations,
                "sha256": receipt.result_meta["sha256"],
                "receipt_id": receipt.receipt_id,
            }

        return {
            "text": text,
            "blocked": False,
            "privacy_state": scan.state,
            "release_decision": scan.release_decision,
            "truncated": truncated,
            "sha256": receipt.result_meta["sha256"],
            "receipt_id": receipt.receipt_id,
        }

    @mcp.tool()
    def privacy_scan_file(
        path: str,
        max_bytes: int = 1048576,
    ) -> dict[str, Any]:
        """Scan a local UTF-8 text file and return metadata only, never the body."""
        if max_bytes < 1 or max_bytes > 4 * 1024 * 1024:
            raise ValueError("max_bytes must be 1..4194304")
        data, receipt = runtime.read_file(
            path, max_bytes=max_bytes, privacy=Privacy.INTERNAL
        )
        text = data.decode("utf-8-sig")
        scan = scan_text(text)
        return {
            "privacy_state": scan.state,
            "release_decision": scan.release_decision,
            "signal_counts": scan.signal_counts,
            "medical_context": scan.medical_context,
            "manual_review_required": scan.manual_review_required,
            "limitations": scan.limitations,
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
        encoded = content.encode("utf-8")
        if len(encoded) > 1024 * 1024:
            raise RuntimeErrorV0("write_text is limited to 1 MiB in V0.4")
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
        encoded = content.encode("utf-8")
        if len(encoded) > 1024 * 1024:
            raise RuntimeErrorV0("write_text is limited to 1 MiB in V0.4")
        args = {
            "path": str(target),
            "content_sha256": hashlib.sha256(encoded).hexdigest(),
            "privacy": p.value,
        }
        broker.consume(
            approval_id,
            action="write_text",
            target=str(target),
            args_sha256=_digest(args),
        )
        snapshot_id = None
        if snapshot_store is not None:
            snapshot = snapshot_store.capture(target)
            snapshot_id = snapshot.snapshot_id
        receipt = runtime.write_file(
            target,
            encoded,
            human_approved=True,
            privacy=p,
        )
        return {
            "executed": True,
            "receipt_id": receipt.receipt_id,
            "after_sha256": receipt.result_meta["after_sha256"],
            "snapshot_id": snapshot_id,
            "rollback": "LOCAL_CLI_ONLY" if snapshot_id else "UNAVAILABLE",
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

    def _require_desktop() -> DesktopActionLayer:
        if desktop_layer is None:
            raise RuntimeErrorV0("Windows Desktop Action Layer unavailable")
        return desktop_layer

    def _ui_target(control_ref: str, resolved) -> str:
        summary = resolved.safe_summary
        name_obj = summary.get("name") or {}
        label = name_obj.get("text") if isinstance(name_obj, dict) else ""
        ctype = summary.get("control_type") or resolved.selector.get("control_type") or "Control"
        return f"uia://{control_ref} | {ctype} | {label or '[label-hidden]'}"

    @mcp.tool()
    def ui_list_windows(max_windows: int = 50) -> dict[str, Any]:
        """Observe visible Windows top-level windows. Titles are hidden by default."""
        layer = _require_desktop()
        return {
            "windows": layer.list_windows(max_windows=max_windows),
            "observation_only": True,
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def ui_inspect_window(window_ref: str, max_controls: int = 100) -> dict[str, Any]:
        """Observe bounded UIA controls and receive ephemeral opaque control refs."""
        layer = _require_desktop()
        result = layer.inspect_window(window_ref, max_controls=max_controls)
        result["observation_only"] = True
        result["send_gate"] = "HOLD"
        return result

    @mcp.tool()
    def request_ui_click(control_ref: str, ttl_seconds: int = 600) -> dict[str, Any]:
        """Legacy V0.6 UI click request. Disabled when V0.7 adapters are active."""
        if app_layer is not None:
            return {
                "status": "DENIED",
                "reason": "APP_ADAPTER_REQUIRED",
                "executed": False,
                "send_gate": "HOLD",
            }
        layer = _require_desktop()
        resolved = layer.resolve_control(control_ref)
        policy = layer.action_policy(control_ref, action="click")
        if policy["decision"] != "HUMAN_GATE":
            return {
                "status": "DENIED",
                "reason": policy["reason"],
                "executed": False,
                "send_gate": "HOLD",
            }
        args = {
            "control_ref": control_ref,
            "fingerprint": resolved.selector["fingerprint"],
            "action": "click",
        }
        target = _ui_target(control_ref, resolved)
        request = broker.request(
            action="ui_click",
            target=target,
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": request["approval_id"],
            "status": "HUMAN_GATE",
            "target": target,
            "expires_at": request["expires_at"],
            "executed": False,
        }

    @mcp.tool()
    def execute_ui_click(control_ref: str, approval_id: str) -> dict[str, Any]:
        """Legacy V0.6 UI click execute. Disabled when V0.7 adapters are active."""
        if app_layer is not None:
            return {
                "status": "DENIED",
                "reason": "APP_ADAPTER_REQUIRED",
                "executed": False,
                "send_gate": "HOLD",
            }
        layer = _require_desktop()
        resolved = layer.resolve_control(control_ref)
        policy = layer.action_policy(control_ref, action="click")
        if policy["decision"] != "HUMAN_GATE":
            raise RuntimeErrorV0(f"UI click blocked: {policy['reason']}")
        args = {
            "control_ref": control_ref,
            "fingerprint": resolved.selector["fingerprint"],
            "action": "click",
        }
        target = _ui_target(control_ref, resolved)
        broker.consume(
            approval_id,
            action="ui_click",
            target=target,
            args_sha256=_digest(args),
        )
        result = layer.click(control_ref)
        result.update({
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        })
        return result

    @mcp.tool()
    def request_ui_set_text(
        control_ref: str,
        text: str,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Legacy V0.6 text request. Disabled when V0.7 adapters are active."""
        if app_layer is not None:
            return {
                "status": "DENIED",
                "reason": "APP_ADAPTER_REQUIRED",
                "executed": False,
                "send_gate": "HOLD",
            }
        layer = _require_desktop()
        resolved = layer.resolve_control(control_ref)
        policy = layer.action_policy(control_ref, action="set_text", text=text)
        if policy["decision"] != "HUMAN_GATE":
            return {
                "status": "DENIED",
                "reason": policy["reason"],
                "executed": False,
                "send_gate": "HOLD",
            }
        args = {
            "control_ref": control_ref,
            "fingerprint": resolved.selector["fingerprint"],
            "action": "set_text",
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text_length": len(text),
        }
        target = _ui_target(control_ref, resolved)
        request = broker.request(
            action="ui_set_text",
            target=target,
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": request["approval_id"],
            "status": "HUMAN_GATE",
            "target": target,
            "text_sha256": args["text_sha256"],
            "text_length": len(text),
            "expires_at": request["expires_at"],
            "executed": False,
        }

    @mcp.tool()
    def execute_ui_set_text(
        control_ref: str,
        text: str,
        approval_id: str,
    ) -> dict[str, Any]:
        """Legacy V0.6 text execute. Disabled when V0.7 adapters are active."""
        if app_layer is not None:
            return {
                "status": "DENIED",
                "reason": "APP_ADAPTER_REQUIRED",
                "executed": False,
                "send_gate": "HOLD",
            }
        layer = _require_desktop()
        resolved = layer.resolve_control(control_ref)
        policy = layer.action_policy(control_ref, action="set_text", text=text)
        if policy["decision"] != "HUMAN_GATE":
            raise RuntimeErrorV0(f"UI set_text blocked: {policy['reason']}")
        args = {
            "control_ref": control_ref,
            "fingerprint": resolved.selector["fingerprint"],
            "action": "set_text",
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text_length": len(text),
        }
        target = _ui_target(control_ref, resolved)
        broker.consume(
            approval_id,
            action="ui_set_text",
            target=target,
            args_sha256=_digest(args),
        )
        result = layer.set_text(control_ref, text)
        result.update({
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        })
        return result

    def _require_app_layer() -> AppAdapterLayer:
        if app_layer is None:
            raise RuntimeErrorV0("App Adapter Layer unavailable")
        return app_layer

    def _app_target(window_ref: str, control_ref: str, adapter_id: str, resolved) -> str:
        summary = resolved.safe_summary
        name_obj = summary.get("name") or {}
        label = name_obj.get("text") if isinstance(name_obj, dict) else ""
        ctype = summary.get("control_type") or resolved.selector.get("control_type") or "Control"
        return (
            f"app://{adapter_id}/{window_ref}/{control_ref} | "
            f"{ctype} | {label or '[label-hidden]'}"
        )

    @mcp.tool()
    def app_identify_window(window_ref: str) -> dict[str, Any]:
        """Identify a window using non-content process/class metadata only."""
        layer = _require_app_layer()
        result = layer.identify_window(window_ref)
        result["send_gate"] = "HOLD"
        return result

    @mcp.tool()
    def app_inspect_window(window_ref: str, max_controls: int = 100) -> dict[str, Any]:
        """Inspect a window through its matched adapter and bounded UI refs."""
        layer = _require_app_layer()
        result = layer.inspect_window(window_ref, max_controls=max_controls)
        result["send_gate"] = "HOLD"
        return result

    @mcp.tool()
    def request_app_click(
        window_ref: str,
        control_ref: str,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Request a click only when both adapter and Desktop policy allow it."""
        layer = _require_app_layer()
        policy = layer.app_policy(
            window_ref, control_ref, action="click"
        )
        if policy["decision"] != "HUMAN_GATE":
            return {
                "status": "DENIED",
                "reason": policy["reason"],
                "adapter_id": policy.get("adapter_id"),
                "executed": False,
                "send_gate": "HOLD",
            }
        resolved = _require_desktop().resolve_control(control_ref)
        adapter_id = policy["adapter_id"]
        args = {
            "window_ref": window_ref,
            "control_ref": control_ref,
            "adapter_id": adapter_id,
            "fingerprint": resolved.selector["fingerprint"],
            "action": "click",
        }
        target = _app_target(window_ref, control_ref, adapter_id, resolved)
        request = broker.request(
            action="app_click",
            target=target,
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": request["approval_id"],
            "status": "HUMAN_GATE",
            "adapter_id": adapter_id,
            "target": target,
            "expires_at": request["expires_at"],
            "executed": False,
        }

    @mcp.tool()
    def execute_app_click(
        window_ref: str,
        control_ref: str,
        approval_id: str,
    ) -> dict[str, Any]:
        """Execute an exact adapter-authorized click after local approval."""
        layer = _require_app_layer()
        policy = layer.app_policy(
            window_ref, control_ref, action="click"
        )
        if policy["decision"] != "HUMAN_GATE":
            return {
                "status": "DENIED",
                "reason": policy["reason"],
                "adapter_id": policy.get("adapter_id"),
                "executed": False,
                "send_gate": "HOLD",
            }
        resolved = _require_desktop().resolve_control(control_ref)
        adapter_id = policy["adapter_id"]
        args = {
            "window_ref": window_ref,
            "control_ref": control_ref,
            "adapter_id": adapter_id,
            "fingerprint": resolved.selector["fingerprint"],
            "action": "click",
        }
        target = _app_target(window_ref, control_ref, adapter_id, resolved)
        broker.consume(
            approval_id,
            action="app_click",
            target=target,
            args_sha256=_digest(args),
        )
        result = _require_desktop().click(control_ref)
        result.update({
            "adapter_id": adapter_id,
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        })
        return result

    @mcp.tool()
    def request_app_set_text(
        window_ref: str,
        control_ref: str,
        text: str,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Request clean Edit text only when adapter and Desktop policy both allow it."""
        layer = _require_app_layer()
        policy = layer.app_policy(
            window_ref, control_ref, action="set_text", text=text
        )
        if policy["decision"] != "HUMAN_GATE":
            return {
                "status": "DENIED",
                "reason": policy["reason"],
                "adapter_id": policy.get("adapter_id"),
                "executed": False,
                "send_gate": "HOLD",
            }
        resolved = _require_desktop().resolve_control(control_ref)
        adapter_id = policy["adapter_id"]
        args = {
            "window_ref": window_ref,
            "control_ref": control_ref,
            "adapter_id": adapter_id,
            "fingerprint": resolved.selector["fingerprint"],
            "action": "set_text",
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text_length": len(text),
        }
        target = _app_target(window_ref, control_ref, adapter_id, resolved)
        request = broker.request(
            action="app_set_text",
            target=target,
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": request["approval_id"],
            "status": "HUMAN_GATE",
            "adapter_id": adapter_id,
            "target": target,
            "text_sha256": args["text_sha256"],
            "text_length": len(text),
            "expires_at": request["expires_at"],
            "executed": False,
        }

    @mcp.tool()
    def execute_app_set_text(
        window_ref: str,
        control_ref: str,
        text: str,
        approval_id: str,
    ) -> dict[str, Any]:
        """Execute exact clean text through an adapter after local approval."""
        layer = _require_app_layer()
        policy = layer.app_policy(
            window_ref, control_ref, action="set_text", text=text
        )
        if policy["decision"] != "HUMAN_GATE":
            return {
                "status": "DENIED",
                "reason": policy["reason"],
                "adapter_id": policy.get("adapter_id"),
                "executed": False,
                "send_gate": "HOLD",
            }
        resolved = _require_desktop().resolve_control(control_ref)
        adapter_id = policy["adapter_id"]
        args = {
            "window_ref": window_ref,
            "control_ref": control_ref,
            "adapter_id": adapter_id,
            "fingerprint": resolved.selector["fingerprint"],
            "action": "set_text",
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text_length": len(text),
        }
        target = _app_target(window_ref, control_ref, adapter_id, resolved)
        broker.consume(
            approval_id,
            action="app_set_text",
            target=target,
            args_sha256=_digest(args),
        )
        result = _require_desktop().set_text(control_ref, text)
        result.update({
            "adapter_id": adapter_id,
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        })
        return result

    def _require_developer() -> DeveloperWorkspaceAdapter:
        if developer_layer is None:
            raise RuntimeErrorV0("Developer Adapter unavailable")
        return developer_layer

    @mcp.tool()
    def dev_workspace_status(
        window_ref: str,
        workspace_path: str,
    ) -> dict[str, Any]:
        """Read bounded Git status for an approved VS Code/Cursor workspace."""
        return _require_developer().status(window_ref, workspace_path)

    @mcp.tool()
    def dev_git_diff(
        window_ref: str,
        workspace_path: str,
        staged: bool = False,
        max_chars: int = 120000,
    ) -> dict[str, Any]:
        """Read a bounded Git diff with local privacy release checks."""
        return _require_developer().diff(
            window_ref,
            workspace_path,
            staged=staged,
            max_chars=max_chars,
        )

    @mcp.tool()
    def dev_detect_tests(
        window_ref: str,
        workspace_path: str,
    ) -> dict[str, Any]:
        """Detect the fixed bounded pytest profile from local workspace markers."""
        return _require_developer().detect_test_profile(
            window_ref,
            workspace_path,
        )

    @mcp.tool()
    def request_dev_test(
        window_ref: str,
        workspace_path: str,
        profile_id: str = "pytest.quiet.v0",
        timeout_seconds: float = 120.0,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Request one-time approval for the exact fixed developer test profile."""
        if timeout_seconds <= 0 or timeout_seconds > 300:
            raise ValueError("timeout_seconds must be >0 and <=300")
        layer = _require_developer()
        detected, argv = layer.exact_test_argv(
            window_ref,
            workspace_path,
            profile_id,
        )
        workspace = detected["workspace_path"]
        args = {
            "window_ref": window_ref,
            "workspace_path": workspace,
            "adapter_id": detected["adapter_id"],
            "profile_id": profile_id,
            "argv": argv,
            "timeout_seconds": timeout_seconds,
        }
        target = (
            f"dev://{detected['adapter_id']}/{profile_id} | "
            f"{workspace}"
        )
        request = broker.request(
            action="dev_test",
            target=target,
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": request["approval_id"],
            "status": "HUMAN_GATE",
            "adapter_id": detected["adapter_id"],
            "profile_id": profile_id,
            "argv": argv,
            "target": target,
            "expires_at": request["expires_at"],
            "executed": False,
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def execute_dev_test(
        window_ref: str,
        workspace_path: str,
        approval_id: str,
        profile_id: str = "pytest.quiet.v0",
        timeout_seconds: float = 120.0,
    ) -> dict[str, Any]:
        """Execute the exact fixed test profile after local approval."""
        if timeout_seconds <= 0 or timeout_seconds > 300:
            raise ValueError("timeout_seconds must be >0 and <=300")
        layer = _require_developer()
        detected, argv = layer.exact_test_argv(
            window_ref,
            workspace_path,
            profile_id,
        )
        workspace = detected["workspace_path"]
        args = {
            "window_ref": window_ref,
            "workspace_path": workspace,
            "adapter_id": detected["adapter_id"],
            "profile_id": profile_id,
            "argv": argv,
            "timeout_seconds": timeout_seconds,
        }
        target = (
            f"dev://{detected['adapter_id']}/{profile_id} | "
            f"{workspace}"
        )
        broker.consume(
            approval_id,
            action="dev_test",
            target=target,
            args_sha256=_digest(args),
        )
        cp, receipt = runtime.run_command(
            argv,
            cwd=workspace,
            human_approved=True,
            timeout=timeout_seconds,
        )
        sanitized = layer.sanitize_test_output(cp.stdout, cp.stderr)
        return {
            "executed": True,
            "adapter_id": detected["adapter_id"],
            "profile_id": profile_id,
            "returncode": cp.returncode,
            "output": sanitized,
            "receipt_id": receipt.receipt_id,
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        }

    def _require_session_manager() -> DeveloperSessionManager:
        if session_manager is None:
            raise RuntimeErrorV0("Developer Worker Session unavailable")
        return session_manager

    def _verified_session(session_id: str) -> dict[str, Any]:
        status = _require_session_manager().verify(session_id)
        if status.get("binding_state") != "BOUND_ESTABLISHED":
            raise RuntimeErrorV0(
                f"developer session not bound: {status.get('binding_state')}"
            )
        if not status.get("window_ref"):
            raise RuntimeErrorV0("developer session has no verified window_ref")
        return status

    @mcp.tool()
    def request_dev_session_start(
        workspace_path: str,
        wait_seconds: float = 20.0,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Prepare a dedicated Cursor worker session and request local approval to launch it."""
        if wait_seconds < 5 or wait_seconds > 60:
            raise ValueError("wait_seconds must be 5..60")
        prepared = _require_session_manager().prepare(workspace_path)
        args = {
            "session_id": prepared["session_id"],
            "workspace_path": prepared["workspace_path"],
            "workspace_file_sha256": prepared["workspace_file_sha256"],
            "window_marker_sha256": prepared["window_marker_sha256"],
            "launch_argv_sha256": prepared["launch_argv_sha256"],
            "wait_seconds": wait_seconds,
        }
        target = (
            f"devsession://start/{prepared['session_id']} | "
            f"{prepared['workspace_path']}"
        )
        req = broker.request(
            action="dev_session_start",
            target=target,
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            **prepared,
            "approval_id": req["approval_id"],
            "approval_status": "HUMAN_GATE",
            "wait_seconds": wait_seconds,
            "executed": False,
        }

    @mcp.tool()
    def execute_dev_session_start(
        session_id: str,
        approval_id: str,
        wait_seconds: float = 20.0,
    ) -> dict[str, Any]:
        """Launch and bind the exact prepared dedicated Cursor session after approval."""
        if wait_seconds < 5 or wait_seconds > 60:
            raise ValueError("wait_seconds must be 5..60")
        manager = _require_session_manager()
        prepared = manager._public(manager._load(session_id))
        args = {
            "session_id": prepared["session_id"],
            "workspace_path": prepared["workspace_path"],
            "workspace_file_sha256": prepared["workspace_file_sha256"],
            "window_marker_sha256": prepared["window_marker_sha256"],
            "launch_argv_sha256": prepared["launch_argv_sha256"],
            "wait_seconds": wait_seconds,
        }
        target = (
            f"devsession://start/{prepared['session_id']} | "
            f"{prepared['workspace_path']}"
        )
        broker.consume(
            approval_id,
            action="dev_session_start",
            target=target,
            args_sha256=_digest(args),
        )
        result = manager.start(session_id, wait_seconds=wait_seconds)
        result["executed"] = True
        result["semantic_state"] = "NOT_ADJUDICATED"
        return result

    @mcp.tool()
    def dev_session_status(session_id: str) -> dict[str, Any]:
        """Verify the dedicated Cursor process/window/workspace binding."""
        return _require_session_manager().verify(session_id)

    @mcp.tool()
    def dev_session_workspace_status(session_id: str) -> dict[str, Any]:
        """Read Git status only after a dedicated Cursor session is freshly verified."""
        bound = _verified_session(session_id)
        result = _require_developer().status(
            bound["window_ref"],
            bound["workspace_path"],
        )
        result["session_id"] = session_id
        result["binding_state"] = "BOUND_ESTABLISHED"
        result["bound_window_pid"] = bound["bound_window_pid"]
        return result

    @mcp.tool()
    def dev_session_git_diff(
        session_id: str,
        staged: bool = False,
        max_chars: int = 120000,
    ) -> dict[str, Any]:
        """Read bounded Git diff through a freshly verified dedicated Cursor session."""
        bound = _verified_session(session_id)
        result = _require_developer().diff(
            bound["window_ref"],
            bound["workspace_path"],
            staged=staged,
            max_chars=max_chars,
        )
        result["session_id"] = session_id
        result["binding_state"] = "BOUND_ESTABLISHED"
        result["bound_window_pid"] = bound["bound_window_pid"]
        return result

    @mcp.tool()
    def dev_session_detect_tests(session_id: str) -> dict[str, Any]:
        """Detect the fixed pytest profile through a freshly verified dedicated session."""
        bound = _verified_session(session_id)
        result = _require_developer().detect_test_profile(
            bound["window_ref"],
            bound["workspace_path"],
        )
        result["session_id"] = session_id
        result["binding_state"] = "BOUND_ESTABLISHED"
        result["bound_window_pid"] = bound["bound_window_pid"]
        return result

    @mcp.tool()
    def request_dev_session_test(
        session_id: str,
        profile_id: str = "pytest.quiet.v0",
        timeout_seconds: float = 120.0,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Request the fixed pytest profile for a verified dedicated Cursor worker."""
        if timeout_seconds <= 0 or timeout_seconds > 300:
            raise ValueError("timeout_seconds must be >0 and <=300")
        bound = _verified_session(session_id)
        detected, argv = _require_developer().exact_test_argv(
            bound["window_ref"],
            bound["workspace_path"],
            profile_id,
        )
        args = {
            "session_id": session_id,
            "bound_window_pid": bound["bound_window_pid"],
            "workspace_path": bound["workspace_path"],
            "adapter_id": detected["adapter_id"],
            "profile_id": profile_id,
            "argv": argv,
            "timeout_seconds": timeout_seconds,
        }
        target = (
            f"devsession://test/{session_id}/{profile_id} | "
            f"{bound['workspace_path']}"
        )
        req = broker.request(
            action="dev_session_test",
            target=target,
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": req["approval_id"],
            "status": "HUMAN_GATE",
            "session_id": session_id,
            "bound_window_pid": bound["bound_window_pid"],
            "profile_id": profile_id,
            "argv": argv,
            "target": target,
            "executed": False,
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def execute_dev_session_test(
        session_id: str,
        approval_id: str,
        profile_id: str = "pytest.quiet.v0",
        timeout_seconds: float = 120.0,
    ) -> dict[str, Any]:
        """Execute the exact approved fixed pytest profile for a verified session."""
        if timeout_seconds <= 0 or timeout_seconds > 300:
            raise ValueError("timeout_seconds must be >0 and <=300")
        bound = _verified_session(session_id)
        detected, argv = _require_developer().exact_test_argv(
            bound["window_ref"],
            bound["workspace_path"],
            profile_id,
        )
        args = {
            "session_id": session_id,
            "bound_window_pid": bound["bound_window_pid"],
            "workspace_path": bound["workspace_path"],
            "adapter_id": detected["adapter_id"],
            "profile_id": profile_id,
            "argv": argv,
            "timeout_seconds": timeout_seconds,
        }
        target = (
            f"devsession://test/{session_id}/{profile_id} | "
            f"{bound['workspace_path']}"
        )
        broker.consume(
            approval_id,
            action="dev_session_test",
            target=target,
            args_sha256=_digest(args),
        )
        cp, receipt = runtime.run_command(
            argv,
            cwd=bound["workspace_path"],
            human_approved=True,
            timeout=timeout_seconds,
        )
        sanitized = _require_developer().sanitize_test_output(cp.stdout, cp.stderr)
        return {
            "executed": True,
            "session_id": session_id,
            "bound_window_pid": bound["bound_window_pid"],
            "profile_id": profile_id,
            "returncode": cp.returncode,
            "output": sanitized,
            "receipt_id": receipt.receipt_id,
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def request_dev_session_close(
        session_id: str,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Request local approval to terminate only the dedicated Cursor session processes."""
        manager = _require_session_manager()
        record = manager._public(manager._load(session_id))
        args = {
            "session_id": session_id,
            "bound_window_pid": record["bound_window_pid"],
            "workspace_path": record["workspace_path"],
            "status": record["status"],
        }
        target = f"devsession://close/{session_id} | {record['workspace_path']}"
        req = broker.request(
            action="dev_session_close",
            target=target,
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": req["approval_id"],
            "status": "HUMAN_GATE",
            "session_id": session_id,
            "bound_window_pid": record["bound_window_pid"],
            "target": target,
            "executed": False,
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def execute_dev_session_close(
        session_id: str,
        approval_id: str,
    ) -> dict[str, Any]:
        """Close only the exact dedicated Cursor session processes after local approval."""
        manager = _require_session_manager()
        record = manager._public(manager._load(session_id))
        args = {
            "session_id": session_id,
            "bound_window_pid": record["bound_window_pid"],
            "workspace_path": record["workspace_path"],
            "status": record["status"],
        }
        target = f"devsession://close/{session_id} | {record['workspace_path']}"
        broker.consume(
            approval_id,
            action="dev_session_close",
            target=target,
            args_sha256=_digest(args),
        )
        result = manager.close(session_id)
        result["executed"] = True
        result["semantic_state"] = "NOT_ADJUDICATED"
        return result

    def _require_cursor_agent_bridge() -> CursorAgentBridge:
        if cursor_agent_bridge is None:
            raise RuntimeErrorV0("Cursor Agent bridge unavailable")
        return cursor_agent_bridge

    def _agent_context(session_id: str) -> dict[str, Any]:
        return _require_session_manager().agent_context(session_id)

    def _safe_thread_title(title: str) -> dict[str, Any]:
        scan = scan_text(title)
        digest = hashlib.sha256(title.encode("utf-8", errors="replace")).hexdigest()
        if scan.release_decision != "ALLOW":
            return {
                "text": "[SENSITIVE_THREAD_TITLE]",
                "sha256": digest,
                "privacy_state": scan.state,
            }
        return {
            "text": title[:160],
            "sha256": digest,
            "truncated": len(title) > 160,
        }

    @mcp.tool()
    def cursor_agent_status(session_id: str) -> dict[str, Any]:
        """Check whether an exact dedicated session has one live Cursor desktop bridge."""
        ctx = _agent_context(session_id)
        try:
            instance = _require_cursor_agent_bridge().session_instance(
                ctx["user_data_dir"]
            )
        except CursorAgentBridgeError as exc:
            return {
                "session_id": session_id,
                "bridge_state": "NOT_ESTABLISHED",
                "reason": str(exc),
                "bound_window_pid": ctx["bound_window_pid"],
                "send_gate": "HOLD",
            }
        return {
            "session_id": session_id,
            "bridge_state": "ESTABLISHED",
            "bridge_pid": instance.pid,
            "app_name": instance.app_name,
            "app_version": instance.app_version,
            "bound_window_pid": ctx["bound_window_pid"],
            "user_data_dir_match": True,
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def cursor_agent_threads(session_id: str) -> dict[str, Any]:
        """List only live agent threads belonging to the exact dedicated session bridge."""
        ctx = _agent_context(session_id)
        rows = _require_cursor_agent_bridge().list_threads(
            ctx["user_data_dir"]
        )
        return {
            "session_id": session_id,
            "threads": [
                {
                    "id": row["id"],
                    "title": _safe_thread_title(row["title"]),
                    "source": row["source"],
                    "status": row["status"],
                    "lastUpdatedAt": row["lastUpdatedAt"],
                    "windowId": row["windowId"],
                }
                for row in rows
            ],
            "thread_count": len(rows),
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def request_cursor_agent_prompt(
        session_id: str,
        thread_id: str,
        prompt: str,
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        """Request local approval for an exact Cursor Agent prompt; does not send."""
        ctx = _agent_context(session_id)
        bridge = _require_cursor_agent_bridge()
        policy = bridge.validate_prompt(prompt)
        if policy["decision"] != "HUMAN_GATE":
            return {
                "status": "DENIED",
                "reason": policy["reason"],
                "session_id": session_id,
                "executed": False,
                "send_gate": "HOLD",
            }
        threads = bridge.list_threads(ctx["user_data_dir"])
        hits = [row for row in threads if row["id"] == thread_id]
        if len(hits) != 1:
            return {
                "status": "DENIED",
                "reason": "THREAD_NOT_EXACTLY_BOUND_TO_SESSION",
                "session_id": session_id,
                "executed": False,
                "send_gate": "HOLD",
            }
        prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        args = {
            "session_id": session_id,
            "bound_window_pid": ctx["bound_window_pid"],
            "workspace_path": ctx["workspace_path"],
            "thread_id": thread_id,
            "prompt_sha256": prompt_sha256,
            "prompt_length": len(prompt),
            "force": False,
        }
        target = (
            f"cursor-agent://{session_id}/{thread_id} | "
            f"{ctx['workspace_path']}"
        )
        req = broker.request(
            action="cursor_agent_prompt",
            target=target,
            args_sha256=_digest(args),
            ttl_seconds=ttl_seconds,
        )
        return {
            "approval_id": req["approval_id"],
            "status": "HUMAN_GATE",
            "session_id": session_id,
            "thread_id": thread_id,
            "prompt_sha256": prompt_sha256,
            "prompt_length": len(prompt),
            "target": target,
            "expires_at": req["expires_at"],
            "executed": False,
            "send_gate": "HOLD",
        }

    @mcp.tool()
    def execute_cursor_agent_prompt(
        session_id: str,
        thread_id: str,
        prompt: str,
        approval_id: str,
    ) -> dict[str, Any]:
        """Submit the exact approved prompt to the exact session-bound Cursor thread."""
        ctx = _agent_context(session_id)
        bridge = _require_cursor_agent_bridge()
        policy = bridge.validate_prompt(prompt)
        if policy["decision"] != "HUMAN_GATE":
            return {
                "status": "DENIED",
                "reason": policy["reason"],
                "session_id": session_id,
                "executed": False,
                "send_gate": "HOLD",
            }
        threads = bridge.list_threads(ctx["user_data_dir"])
        hits = [row for row in threads if row["id"] == thread_id]
        if len(hits) != 1:
            return {
                "status": "DENIED",
                "reason": "THREAD_NOT_EXACTLY_BOUND_TO_SESSION",
                "session_id": session_id,
                "executed": False,
                "send_gate": "HOLD",
            }
        prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        args = {
            "session_id": session_id,
            "bound_window_pid": ctx["bound_window_pid"],
            "workspace_path": ctx["workspace_path"],
            "thread_id": thread_id,
            "prompt_sha256": prompt_sha256,
            "prompt_length": len(prompt),
            "force": False,
        }
        target = (
            f"cursor-agent://{session_id}/{thread_id} | "
            f"{ctx['workspace_path']}"
        )
        broker.consume(
            approval_id,
            action="cursor_agent_prompt",
            target=target,
            args_sha256=_digest(args),
        )
        result = bridge.send(
            ctx["user_data_dir"],
            thread_id,
            prompt,
            force=False,
        )
        return {
            "executed": True,
            "session_id": session_id,
            "thread_id": result["threadId"],
            "windowId": result["windowId"],
            "status": result["status"],
            "thread_title": _safe_thread_title(result["threadTitle"]),
            "prompt_sha256": prompt_sha256,
            "prompt_length": len(prompt),
            "semantic_state": "NOT_ADJUDICATED",
            "send_gate": "HOLD",
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
    secret_store = None
    snapshot_store = None
    desktop_layer = None
    app_layer = None
    developer_layer = None
    session_manager = None
    cursor_agent_bridge = None
    if os.name == "nt":
        try:
            secret_store = DPAPISecretStore(broker.state_dir)
        except SecretStoreError:
            secret_store = None
        try:
            snapshot_store = SnapshotStore(
                broker.state_dir,
                protected_roots=runtime.config.normalized_roots(),
            )
        except SnapshotError:
            snapshot_store = None
        try:
            ui_refs = UIRefStore(broker.state_dir)
            desktop_layer = DesktopActionLayer(ui_refs)
            app_layer = AppAdapterLayer(
                desktop_layer,
                ui_refs,
                registry=AppAdapterRegistry(),
            )
            developer_layer = DeveloperWorkspaceAdapter(
                runtime.config,
                app_layer,
            )
            session_manager = DeveloperSessionManager(
                runtime.config,
                broker.state_dir,
                desktop_layer,
            )
            cursor_agent_bridge = CursorAgentBridge()
        except (UIRefError, DesktopUIError, AppAdapterError):
            desktop_layer = None
            app_layer = None
            developer_layer = None
            session_manager = None
            cursor_agent_bridge = None
    mcp = create_server(
        runtime,
        broker,
        secret_store=secret_store,
        snapshot_store=snapshot_store,
        desktop_layer=desktop_layer,
        app_layer=app_layer,
        developer_layer=developer_layer,
        session_manager=session_manager,
        cursor_agent_bridge=cursor_agent_bridge,
    )
    mcp.run()


if __name__ == "__main__":
    main()
