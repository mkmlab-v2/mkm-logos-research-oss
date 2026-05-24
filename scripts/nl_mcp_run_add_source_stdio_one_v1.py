#!/usr/bin/env python3
"""Run one add_source via stdio MCP; writes parsed result JSON to --out."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

AGENT_TOOLS = Path(r"C:\Users\PRO\.cursor\projects\c-workspace\agent-tools")
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
        "MKM_NOTEBOOKLM_MCP_PINNED_VERSION": os.environ.get(
            "MKM_NOTEBOOKLM_MCP_PINNED_VERSION", "2.0.0"
        ),
        "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
    }
    return StdioServerParameters(command="node", args=[str(NOTEBOOKLM_JS)], env=env)


def _parse_result(tool_result) -> dict:
    row = {"success": False, "sourceCountBefore": None, "sourceCountAfter": None, "error": None}
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
            row["sourceCountBefore"] = inner.get("sourceCountBefore")
            row["sourceCountAfter"] = inner.get("sourceCountAfter")
            if inner.get("error"):
                row["error"] = inner["error"]
            return row
    row["error"] = "unparsed tool result"
    return row


async def run_one(index: int, out_path: Path) -> dict:
    args_path = AGENT_TOOLS / f"mcp_call_{index}.json"
    tool_args = json.loads(args_path.read_text(encoding="utf-8"))
    row = {
        "index": index,
        "title": tool_args.get("title"),
        "success": False,
        "sourceCountAfter": None,
        "error": None,
    }
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("add_source", tool_args)
            parsed = _parse_result(result)
            row.update(parsed)
    out_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(row, ensure_ascii=False), flush=True)
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("index", type=int)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    row = asyncio.run(run_one(args.index, Path(args.out)))
    return 0 if row.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
