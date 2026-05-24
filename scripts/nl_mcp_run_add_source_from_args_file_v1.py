#!/usr/bin/env python3
"""Run add_source from a JSON args file via stdio MCP (one file)."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)


def _server_params() -> StdioServerParameters:
    env = {
        "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
        "HEADLESS": os.environ.get("HEADLESS", "false"),
        "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
    }
    return StdioServerParameters(command="node", args=[str(NOTEBOOKLM_JS)], env=env)


def _parse_result(tool_result) -> dict:
    row = {"success": False, "sourceCountAfter": None, "error": None}
    if tool_result.isError:
        row["error"] = str(tool_result.content)
        return row
    for block in tool_result.content or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        inner = payload.get("data", payload)
        if isinstance(inner, dict) and "result" in inner:
            inner = inner["result"]
        if isinstance(inner, dict):
            row["success"] = bool(inner.get("success", payload.get("success")))
            row["sourceCountAfter"] = inner.get("sourceCountAfter")
            row["error"] = inner.get("error")
            return row
    row["error"] = "unparsed"
    return row


async def run(args_path: Path) -> dict:
    tool_args = json.loads(args_path.read_text(encoding="utf-8"))
    row = {"title": tool_args.get("title"), "success": False}
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("add_source", tool_args)
            row.update(_parse_result(result))
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("args_json", help="path to add_source args JSON")
    args = ap.parse_args()
    row = asyncio.run(run(Path(args.args_json)))
    print(json.dumps(row, ensure_ascii=False))
    return 0 if row.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
