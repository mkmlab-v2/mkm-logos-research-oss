#!/usr/bin/env python3
"""IJEOMA B-track NL smoke: 동의수세보원 표리병증 proxy — [CANON] 인용 없이."""

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
NOTEBOOK_MCP_ID = "15-b-track-ijeoma-1"
NOTEBOOK_UUID = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/ijeoma_pyobyeong_nl_smoke_v1.json"

QUESTION = (
    "동의수세보원 표리병증(表裡病證) 논지를 업로드된 IJEOMA 소스만 근거로 5줄 요약해 주세요. "
    "[CANON] 단정·한자 정본 확정 없이. 인용이 없으면 '근거 부족'이라고만 답하세요."
)

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
        return {"success": False, "error": str(tool_result.content), "answer": ""}
    answer_parts: list[str] = []
    authenticated = None
    for block in tool_result.content or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            answer_parts.append(text)
            continue
        if isinstance(payload, dict) and "authenticated" in payload:
            authenticated = payload.get("authenticated")
        if isinstance(payload, dict) and payload.get("success") is False:
            return {
                "success": False,
                "error": payload.get("error") or text,
                "answer": "",
                "authenticated": authenticated,
            }
        inner = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(inner, dict) and "result" in inner:
            inner = inner["result"]
        if isinstance(inner, dict):
            for key in ("answer", "response", "text", "content", "message"):
                if inner.get(key):
                    answer_parts.append(str(inner[key]))
            if inner.get("session_id"):
                return {
                    "success": True,
                    "answer": "\n".join(answer_parts),
                    "session_id": inner.get("session_id"),
                    "authenticated": authenticated,
                }
        answer_parts.append(text)
    answer = "\n".join(answer_parts).strip()
    return {
        "success": True,
        "answer": answer,
        "authenticated": authenticated,
        "error": "" if answer else "",
    }


async def _run(question: str, notebook_mcp_id: str) -> dict:
    if not NOTEBOOKLM_JS.is_file():
        return {
            "ok": False,
            "error": f"notebooklm-mcp missing: {NOTEBOOKLM_JS}",
            "question": question,
        }

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            health = _parse_tool_result(await session.call_tool("get_health", {}))
            sel = _parse_tool_result(
                await session.call_tool("select_notebook", {"id": notebook_mcp_id})
            )
            if not sel.get("success"):
                return {
                    "ok": False,
                    "error": sel.get("error") or "select_notebook_failed",
                    "stage": "select_notebook",
                    "notebook_mcp_id": notebook_mcp_id,
                    "question": question,
                }

            result = _parse_tool_result(
                await session.call_tool(
                    "ask_question",
                    {"question": question, "notebook_id": notebook_mcp_id},
                )
            )
            answer = result.get("answer", "")
            ok = bool(answer) and result.get("success", False)
            if not ok and not result.get("error"):
                result["error"] = "empty_answer"
            return {
                "ok": ok,
                "authenticated": health.get("authenticated"),
                "notebook_mcp_id": notebook_mcp_id,
                "notebook_uuid": NOTEBOOK_UUID,
                "session_id": result.get("session_id"),
                "question": question,
                "answer": answer,
                "error": result.get("error") or ("" if ok else "ask_failed"),
                "stage": "ask_question" if not ok else "complete",
            }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook-mcp-id", default=NOTEBOOK_MCP_ID)
    ap.add_argument("--question", default=QUESTION)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = asyncio.run(_run(args.question, args.notebook_mcp_id))
    doc.update(
        {
            "schema": "ijeoma_pyobyeong_nl_smoke_v1",
            "generated_at_utc": _utc(),
            "track": "B",
            "send_gate": "HOLD",
            "research_only": True,
            "reproduce": "py scripts/run_ijeoma_pyobyeong_nl_smoke_v1.py",
        }
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "out": str(args.out)}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
