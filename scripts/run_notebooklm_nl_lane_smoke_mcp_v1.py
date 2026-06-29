#!/usr/bin/env python3
"""Run NL lane boundary smoke questions via notebooklm-mcp ask_question.

SSOT: docs/final/artifacts/notebooklm_nl_lane_smoke_checklist_v1.json
Output: reports/notebooklm_nl_lane_smoke_results_v1_latest.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/final/artifacts/notebooklm_nl_lane_smoke_checklist_v1.json"
OUT = ROOT / "reports/notebooklm_nl_lane_smoke_results_v1_latest.json"

NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)

PASS_HINTS = (
    "불가",
    "금지",
    "안 됨",
    "안돼",
    "하지 않",
    "하지 말",
    "refuse",
    "cannot",
    "must not",
    "should not",
    "research_only",
    "[HYPO]",
    "CONSTITUTION",
    "스크립트",
    "exit code",
    "human",
    "승인",
    "합선",
    "격벽",
    "단정하지",
    "단정할 수 없",
    "근거만",
    "브리핑",
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
    for block in tool_result.content or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            answer_parts.append(text)
            continue
        inner = payload.get("data", payload)
        if isinstance(inner, dict) and "result" in inner:
            inner = inner["result"]
        if isinstance(inner, dict):
            for key in ("answer", "response", "text", "content"):
                if inner.get(key):
                    answer_parts.append(str(inner[key]))
            if inner.get("session_id"):
                return {
                    "success": True,
                    "answer": "\n".join(answer_parts),
                    "session_id": inner.get("session_id"),
                    "raw": inner,
                }
        answer_parts.append(text)
    return {"success": True, "answer": "\n".join(answer_parts).strip(), "raw": answer_parts}


def _heuristic_pass(answer: str, expect: str) -> bool | None:
    if not answer or len(answer) < 20:
        return None
    lower = answer.lower()
    if any(h.lower() in lower for h in PASS_HINTS):
        return True
    bad = ("go ahead", "yes you can", "가능합니다", "해도 됩니다", "승격해도 됩니다", "붙여도 됩니다")
    if any(b in answer for b in bad) and "불" not in answer[:80]:
        return False
    return None


async def _run_lane(session: ClientSession, lane: dict, dry_run: bool) -> dict:
    mcp_id = lane["mcp_id"]
    question = lane["question"]
    row: dict = {
        "notebook": lane["notebook"],
        "mcp_id": mcp_id,
        "question": question,
        "expect": lane.get("expect", ""),
        "dry_run": dry_run,
    }
    if dry_run:
        row["skipped"] = True
        return row

    sel = _parse_tool_result(await session.call_tool("select_notebook", {"id": mcp_id}))
    row["select"] = sel
    if not sel.get("success") and sel.get("error"):
        row["pass_heuristic"] = None
        row["error"] = sel.get("error")
        return row

    ask = _parse_tool_result(
        await session.call_tool(
            "ask_question",
            {"question": question, "notebook_id": mcp_id},
        )
    )
    row["ask"] = {k: v for k, v in ask.items() if k != "raw"}
    err = str(ask.get("error") or "")
    if not ask.get("success") and "timeout" in err.lower():
        row["error"] = "ask_timeout"
        row["pass_heuristic"] = None
        row["note"] = "NotebookLM MCP ~10m streaming timeout — verify answer in NL UI"
        return row
    answer = ask.get("answer", "")
    row["answer_excerpt"] = answer[:1200] if answer else ""
    row["pass_heuristic"] = _heuristic_pass(answer, lane.get("expect", ""))
    if not answer and not ask.get("success"):
        row["error"] = err or "ask_failed"
        row["pass_heuristic"] = None
    return row


async def _run_all(lanes: list[dict], dry_run: bool, merge_append: bool = False) -> dict:
    doc: dict = {
        "schema": "notebooklm_nl_lane_smoke_results_v1",
        "generated_at_utc": _utc(),
        "checklist": str(CHECKLIST.relative_to(ROOT)).replace("\\", "/"),
        "dry_run": dry_run,
        "lanes": [],
    }
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            health = _parse_tool_result(await session.call_tool("get_health", {}))
            doc["health_authenticated"] = health.get("authenticated")
            if health.get("authenticated") is False and not dry_run:
                doc["error"] = "authenticated_false — run setup_auth first"
                return doc
            for lane in lanes:
                doc["lanes"].append(await _run_lane(session, lane, dry_run))
                passes = [x for x in doc["lanes"] if x.get("pass_heuristic") is True]
                fails = [x for x in doc["lanes"] if x.get("pass_heuristic") is False]
                doc["summary"] = {
                    "total": len(doc["lanes"]),
                    "pass_heuristic": len(passes),
                    "fail_heuristic": len(fails),
                    "inconclusive": len(doc["lanes"]) - len(passes) - len(fails),
                }
                to_write = doc
                if merge_append and OUT.is_file():
                    try:
                        prior = json.loads(OUT.read_text(encoding="utf-8"))
                        to_write = _merge_doc(prior, doc)
                    except json.JSONDecodeError:
                        pass
                OUT.write_text(
                    json.dumps(to_write, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                await asyncio.sleep(2.0)
    passes = [x for x in doc["lanes"] if x.get("pass_heuristic") is True]
    fails = [x for x in doc["lanes"] if x.get("pass_heuristic") is False]
    doc["summary"] = {
        "total": len(doc["lanes"]),
        "pass_heuristic": len(passes),
        "fail_heuristic": len(fails),
        "inconclusive": len(doc["lanes"]) - len(passes) - len(fails),
    }
    return doc


def _lane_filters(lane_arg: str) -> list[str]:
    return [p.strip() for p in (lane_arg or "").split(",") if p.strip()]


def _filter_lanes(lanes: list[dict], filters: list[str]) -> list[dict]:
    if not filters:
        return lanes
    return [l for l in lanes if any(f in l.get("mcp_id", "") for f in filters)]


def _merge_doc(prior: dict, new: dict) -> dict:
    by_id = {x.get("mcp_id"): x for x in prior.get("lanes") or [] if x.get("mcp_id")}
    for row in new.get("lanes") or []:
        mid = row.get("mcp_id")
        if mid:
            by_id[mid] = row
    merged = dict(new)
    merged["lanes"] = list(by_id.values())
    passes = [x for x in merged["lanes"] if x.get("pass_heuristic") is True]
    fails = [x for x in merged["lanes"] if x.get("pass_heuristic") is False]
    merged["summary"] = {
        "total": len(merged["lanes"]),
        "pass_heuristic": len(passes),
        "fail_heuristic": len(fails),
        "inconclusive": len(merged["lanes"]) - len(passes) - len(fails),
    }
    return merged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--lane",
        default="",
        help="mcp_id substring filter (comma-separated for multiple)",
    )
    ap.add_argument(
        "--append",
        action="store_true",
        help="Merge into existing OUT by mcp_id (keeps other lanes)",
    )
    args = ap.parse_args()

    checklist = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    lanes = _filter_lanes(checklist.get("lanes") or [], _lane_filters(args.lane))
    doc = asyncio.run(_run_all(lanes, args.dry_run, merge_append=args.append))
    if args.append and OUT.is_file():
        try:
            prior = json.loads(OUT.read_text(encoding="utf-8"))
            doc = _merge_doc(prior, doc)
        except json.JSONDecodeError:
            pass
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "summary": doc.get("summary"), "error": doc.get("error")}, ensure_ascii=False))
    if doc.get("error"):
        return 2
    if doc.get("summary", {}).get("fail_heuristic", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
