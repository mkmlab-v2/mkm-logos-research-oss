#!/usr/bin/env python3
"""Register MKMLIFE Consumer NL notebook in notebooklm-mcp library + select as active."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
URL_FILE = ROOT / "reports" / "notebooklm_consumer_notebook_url_v1.txt"
OUT = ROOT / "reports" / "notebooklm_consumer_mcp_register_latest.json"

NOTEBOOK_MCP_ID = "21-mkmlife-consumer-survey-202"
NOTEBOOK_NAME = "21_MKMLIFE_CONSUMER_SURVEY_2026Q2"
DESCRIPTION = (
    "MKMLIFE B2C consumer_survey_only — 14문항·MAI·One-Question. "
    "physician_gold·SOAP·Track A KPI cross-cite forbidden."
)

NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)

UUID_RE = re.compile(
    r"notebook/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.I,
)


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


def _notebook_url() -> str:
    if URL_FILE.is_file():
        url = URL_FILE.read_text(encoding="utf-8").strip()
        if url and not url.startswith("("):
            return url
    raise SystemExit(f"missing URL: {URL_FILE}")


def _uuid_from_url(url: str) -> str | None:
    m = UUID_RE.search(url)
    return m.group(1).lower() if m else None


def _list_notebooks(raw: dict) -> list[dict]:
    for key in ("notebooks", "items"):
        items = raw.get(key)
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    if isinstance(raw.get("notebook"), dict):
        return [raw["notebook"]]
    return []


def _pick_canonical_id(candidates: list[dict]) -> str:
    ids = [c.get("id") for c in candidates if c.get("id")]
    if NOTEBOOK_MCP_ID in ids:
        return NOTEBOOK_MCP_ID
    return sorted(ids, key=lambda x: (len(x), x))[0]


async def _run(select: bool, prune_duplicates: bool) -> dict:
    url = _notebook_url()
    target_uuid = _uuid_from_url(url)
    doc: dict = {
        "notebook_url": url,
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "steps": [],
    }

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            health = _parse_tool_result(await session.call_tool("get_health", {}))
            doc["health_authenticated"] = health.get("authenticated")

            listed = _parse_tool_result(await session.call_tool("list_notebooks", {}))
            doc["steps"].append({"tool": "list_notebooks", "count": len(_list_notebooks(listed))})

            existing: list[dict] = []
            for nb in _list_notebooks(listed):
                nb_url = (nb.get("url") or "").lower()
                nb_uuid = _uuid_from_url(nb_url) if nb_url else None
                if nb_uuid and target_uuid and nb_uuid == target_uuid:
                    existing.append(nb)
                elif nb.get("id") == NOTEBOOK_MCP_ID or str(nb.get("id", "")).startswith(
                    NOTEBOOK_MCP_ID
                ):
                    existing.append(nb)

            resolved_id = NOTEBOOK_MCP_ID
            if existing:
                resolved_id = _pick_canonical_id(existing)
                doc["steps"].append(
                    {
                        "tool": "add_notebook",
                        "skipped": True,
                        "reason": "already_in_library",
                        "resolved_id": resolved_id,
                        "matched_ids": [x.get("id") for x in existing],
                    }
                )
                if prune_duplicates and len(existing) > 1:
                    for dup_id in [
                        x["id"] for x in existing if x.get("id") and x["id"] != resolved_id
                    ]:
                        rm = _parse_tool_result(
                            await session.call_tool("remove_notebook", {"id": dup_id})
                        )
                        doc["steps"].append(
                            {"tool": "remove_notebook", "id": dup_id, "result": rm}
                        )
            else:
                add_args = {
                    "url": url,
                    "id": NOTEBOOK_MCP_ID,
                    "name": NOTEBOOK_NAME,
                    "description": DESCRIPTION,
                    "topics": [
                        "consumer_survey_only",
                        "mkmlife",
                        "MAI",
                        "One-Question",
                        "dual-lane",
                    ],
                    "use_cases": [
                        "mkmlife B2C 카피·면책 브리핑",
                        "14문항·MAI 경계 확인",
                        "physician_gold cross-talk 방지",
                    ],
                }
                add_res = _parse_tool_result(
                    await session.call_tool("add_notebook", add_args)
                )
                doc["steps"].append({"tool": "add_notebook", "result": add_res})
                nb = add_res.get("notebook") if isinstance(add_res.get("notebook"), dict) else None
                if nb and nb.get("id"):
                    resolved_id = nb["id"]

            doc["notebook_mcp_id_resolved"] = resolved_id

            if select:
                sel_res = _parse_tool_result(
                    await session.call_tool("select_notebook", {"id": resolved_id})
                )
                doc["steps"].append({"tool": "select_notebook", "result": sel_res})

            stats = _parse_tool_result(await session.call_tool("get_library_stats", {}))
            doc["library_stats"] = stats

    doc["success"] = doc.get("health_authenticated") is not False
    if select:
        sel = next((s for s in doc["steps"] if s.get("tool") == "select_notebook"), None)
        if sel and sel.get("result", {}).get("success") is False:
            doc["success"] = False
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-select", action="store_true")
    ap.add_argument("--no-prune-duplicates", action="store_true")
    args = ap.parse_args()

    doc = asyncio.run(
        _run(select=not args.no_select, prune_duplicates=not args.no_prune_duplicates)
    )
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "success": doc.get("success"),
                "resolved_id": doc.get("notebook_mcp_id_resolved"),
                "active": doc.get("notebook_mcp_id_resolved")
                if not args.no_select
                else "(unchanged)",
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
