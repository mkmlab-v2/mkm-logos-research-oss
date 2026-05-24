#!/usr/bin/env python3
"""Call notebooklm-mcp add_source for nl_mcp_payload indices via stdio MCP client."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PILOT = Path(__file__).resolve().parents[1] / "reports" / "constitution" / "btrack_pilot"
NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)


def _server_params() -> StdioServerParameters:
    env = {
        "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
        "HEADLESS": os.environ.get("HEADLESS", "true"),
        "MKM_NOTEBOOKLM_MCP_PINNED_VERSION": os.environ.get(
            "MKM_NOTEBOOKLM_MCP_PINNED_VERSION", "2.0.0"
        ),
        "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
    }
    return StdioServerParameters(
        command="node",
        args=[str(NOTEBOOKLM_JS)],
        env=env,
    )


def _load_args(index: int) -> dict:
    path = PILOT / f"nl_mcp_payload_{index}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "type": "text",
        "title": data["title"],
        "content": data["content"],
        "notebook_id": "mkm-core-intelligence-fact-foc",
    }


def _parse_add_source_result(tool_result) -> dict:
    """Extract success and source counts from MCP CallToolResult."""
    out: dict = {"success": False, "sourceCountBefore": None, "sourceCountAfter": None, "error": None}
    if tool_result.isError:
        out["error"] = getattr(tool_result, "content", str(tool_result))
        return out
    for block in tool_result.content or []:
        text = getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else None)
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
            out["success"] = bool(inner.get("success", payload.get("success")))
            out["sourceCountBefore"] = inner.get("sourceCountBefore")
            out["sourceCountAfter"] = inner.get("sourceCountAfter")
            if inner.get("error"):
                out["error"] = inner["error"]
            return out
    out["error"] = "unparsed tool result"
    return out


async def run_indices(indices: list[int]) -> list[dict]:
    rows: list[dict] = []
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            health = await session.call_tool("get_health", {})
            health_text = ""
            for block in health.content or []:
                health_text += getattr(block, "text", "") or ""
            health_json = json.loads(health_text) if health_text.strip().startswith("{") else {}
            authenticated = (
                health_json.get("data", health_json).get("authenticated")
                if isinstance(health_json.get("data", health_json), dict)
                else None
            )
            if authenticated is not True:
                print("WARN: get_health authenticated != true", file=sys.stderr)

            for i in indices:
                title = _load_args(i)["title"]
                row = {"index": i, "title": title, "success": False, "sourceCountAfter": None, "error": None}
                try:
                    tool_args = _load_args(i)
                    result = await session.call_tool("add_source", tool_args)
                    parsed = _parse_add_source_result(result)
                    row.update(parsed)
                except Exception as exc:  # noqa: BLE001
                    row["error"] = str(exc)
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indices", default="1,2,3,4,5,6", help="comma-separated indices")
    parser.add_argument("--out", default="", help="write JSON array to path")
    args = parser.parse_args()
    indices = [int(x.strip()) for x in args.indices.split(",") if x.strip()]
    rows = asyncio.run(run_indices(indices))
    if args.out:
        Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(r.get("success") for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
