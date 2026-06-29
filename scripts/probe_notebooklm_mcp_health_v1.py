#!/usr/bin/env python3
"""Probe notebooklm-mcp get_health (+ optional setup_auth) via stdio MCP."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_mcp_health_probe_v1_latest.json"

NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _server_params() -> StdioServerParameters:
    env = {
        "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
        "HEADLESS": os.environ.get("HEADLESS", "false"),
        "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
    }
    return StdioServerParameters(command="node", args=[str(NOTEBOOKLM_JS)], env=env)


def _parse_tool_result(tool_result) -> dict:
    if tool_result.isError:
        return {"success": False, "error": str(tool_result.content)}
    for block in tool_result.content or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {"success": True, "raw": text}
        inner = payload.get("data", payload)
        if isinstance(inner, dict) and "result" in inner:
            inner = inner["result"]
        if isinstance(inner, dict):
            return inner
        return {"success": True, "payload": payload}
    return {"success": False, "error": "unparsed"}


async def _run(setup_if_needed: bool, sync_nlm_first: bool) -> dict:
    doc: dict = {
        "schema": "notebooklm_mcp_health_probe_v1",
        "generated_at_utc": _utc(),
        "index_js": str(NOTEBOOKLM_JS),
        "steps": [],
    }
    if not NOTEBOOKLM_JS.is_file():
        doc["ok"] = False
        doc["error"] = f"missing index.js: {NOTEBOOKLM_JS}"
        return doc

    if sync_nlm_first:
        import subprocess

        sync_script = ROOT / "scripts" / "sync_notebooklm_nlm_credentials_to_mcp_v1.py"
        if sync_script.is_file():
            proc = subprocess.run(
                [os.environ.get("PYTHON", "py"), str(sync_script)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            doc["steps"].append(
                {
                    "tool": "sync_notebooklm_nlm_credentials_to_mcp_v1",
                    "exit_code": proc.returncode,
                    "stdout_tail": (proc.stdout or "").strip()[-200:],
                }
            )

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            health = _parse_tool_result(await session.call_tool("get_health", {}))
            doc["health"] = health
            doc["steps"].append({"tool": "get_health", "authenticated": health.get("authenticated")})

            if not health.get("authenticated") and setup_if_needed:
                setup = _parse_tool_result(
                    await session.call_tool(
                        "setup_auth",
                        {"show_browser": True, "browser_options": {"timeout_ms": 120000}},
                    )
                )
                doc["steps"].append({"tool": "setup_auth", "result": setup})
                health2 = _parse_tool_result(await session.call_tool("get_health", {}))
                doc["health_after_setup"] = health2
                doc["steps"].append(
                    {"tool": "get_health", "authenticated": health2.get("authenticated"), "pass": 2}
                )
                doc["authenticated"] = bool(health2.get("authenticated"))
            else:
                doc["authenticated"] = bool(health.get("authenticated"))

    doc["ok"] = doc.get("authenticated") is True
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--setup-if-needed",
        action="store_true",
        help="Last resort: setup_auth when still unauthenticated (clears profile; prefer nlm sync)",
    )
    ap.add_argument(
        "--sync-nlm-first",
        action="store_true",
        default=True,
        help="Sync nlm CLI cookies into MCP state.json before get_health (default on)",
    )
    ap.add_argument(
        "--no-sync-nlm-first",
        action="store_true",
        help="Skip nlm→MCP cookie sync",
    )
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    sync_first = args.sync_nlm_first and not args.no_sync_nlm_first
    doc = asyncio.run(_run(setup_if_needed=args.setup_if_needed, sync_nlm_first=sync_first))
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "authenticated": doc.get("authenticated"), "out": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
