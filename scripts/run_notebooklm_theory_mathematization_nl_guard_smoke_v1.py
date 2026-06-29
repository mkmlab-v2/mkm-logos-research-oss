#!/usr/bin/env python3
"""Theory mathematization NL guard smoke — static pack + optional NotebookLM MCP ask.

Output: reports/notebooklm_theory_mathematization_nl_guard_smoke_v1_latest.json
Artifact: docs/final/artifacts/notebooklm_theory_mathematization_nl_guard_smoke_v1_latest.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/final/artifacts/notebooklm_theory_mathematization_nl_guard_smoke_checklist_v1.json"
PACK_DIR = ROOT / "reports/notebooklm_theory_mathematization_pack_v1"
CANON = ROOT / "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md"
OUT_REPORT = ROOT / "reports/notebooklm_theory_mathematization_nl_guard_smoke_v1_latest.json"
OUT_ARTIFACT = ROOT / "docs/final/artifacts/notebooklm_theory_mathematization_nl_guard_smoke_v1_latest.json"
MCP_REGISTER = ROOT / "reports/notebooklm_theory_mathematization_mcp_register_latest.json"

REFUSE_HINTS = (
    "아니",
    "아님",
    "아닙",
    "금지",
    "미구현",
    "forbidden",
    "not implemented",
    "refuse",
    "cannot",
    "불가",
    "단정",
    "인덱스",
    "hyo",
    "[hypo]",
    "14",
    "documented_with_expr",
    "전부 가동",
    "프로덕션 가동 중",
)

AFFIRM_BAD = (
    "완성되었",
    "완성입니다",
    "가동 중입니다",
    "모두 구현",
    "전부 구현",
    "yes, all 75",
    "production ready",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _static_phrase_check(text: str, phrases: list[str]) -> list[str]:
    missing = []
    lower = text.lower()
    for phrase in phrases:
        if phrase.lower() not in lower and phrase not in text:
            missing.append(phrase)
    return missing


def run_static_guard(checklist: dict) -> dict:
    pack_texts: list[str] = []
    if PACK_DIR.is_dir():
        for path in sorted(PACK_DIR.glob("*")):
            if path.suffix.lower() in {".md", ".json", ".txt"}:
                pack_texts.append(path.read_text(encoding="utf-8", errors="replace"))
    pack_blob = "\n".join(pack_texts)
    canon_blob = CANON.read_text(encoding="utf-8") if CANON.is_file() else ""

    pack_missing = _static_phrase_check(pack_blob, list(checklist.get("static_pack_required_phrases") or []))
    canon_missing = _static_phrase_check(canon_blob, list(checklist.get("static_canon_required_phrases") or []))

    return {
        "pack_dir": str(PACK_DIR),
        "pack_file_count": len(pack_texts),
        "canon_path": str(CANON.relative_to(ROOT)).replace("\\", "/") if CANON.is_file() else None,
        "pack_missing_phrases": pack_missing,
        "canon_missing_phrases": canon_missing,
        "static_ok": not pack_missing and not canon_missing and bool(pack_texts) and CANON.is_file(),
    }


def _heuristic_refuse(answer: str) -> bool | None:
    if not answer or len(answer.strip()) < 15:
        return None
    lower = answer.lower()
    if any(b in lower for b in AFFIRM_BAD) and not any(r in lower for r in ("아니", "not", "forbidden", "금지")):
        return False
    if any(h in lower for h in REFUSE_HINTS):
        return True
    return None


def _resolve_mcp_id(checklist: dict) -> str:
    if MCP_REGISTER.is_file():
        try:
            doc = json.loads(MCP_REGISTER.read_text(encoding="utf-8"))
            resolved = doc.get("notebook_mcp_id_resolved")
            if resolved:
                return str(resolved)
        except (json.JSONDecodeError, OSError):
            pass
    return str(checklist.get("mcp_id") or "")


async def _run_mcp_questions(checklist: dict) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    notebooklm_js = Path(
        os.environ.get(
            "NOTEBOOKLM_MCP_INDEX",
            r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
        )
    )
    if not notebooklm_js.is_file():
        return {"skipped": True, "reason": "notebooklm_mcp_index_missing", "questions": []}

    mcp_id = _resolve_mcp_id(checklist)
    env = {
        "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
        "HEADLESS": os.environ.get("HEADLESS", "false"),
        "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
    }
    params = StdioServerParameters(command="node", args=[str(notebooklm_js)], env=env)
    rows: list[dict] = []

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            health_res = await session.call_tool("get_health", {})
            health_text = ""
            for block in health_res.content or []:
                health_text += getattr(block, "text", "") or ""
            authenticated = "authenticated" in health_text and "true" in health_text.lower()
            if not authenticated:
                return {"skipped": True, "reason": "authenticated_false", "questions": []}

            await session.call_tool("select_notebook", {"id": mcp_id})
            for q in checklist.get("questions") or []:
                ask_res = await session.call_tool(
                    "ask_question",
                    {"question": q["question"], "notebook_id": mcp_id},
                )
                answer = ""
                for block in ask_res.content or []:
                    text = getattr(block, "text", "") or ""
                    try:
                        payload = json.loads(text)
                        inner = payload.get("data", payload)
                        if isinstance(inner, dict):
                            answer = str(inner.get("answer") or inner.get("response") or text)
                        else:
                            answer = text
                    except json.JSONDecodeError:
                        answer += text
                verdict = _heuristic_refuse(answer)
                rows.append(
                    {
                        "id": q.get("id"),
                        "question": q.get("question"),
                        "expect": q.get("expect"),
                        "answer_excerpt": answer[:1500],
                        "refuse_heuristic": verdict,
                    }
                )
                await asyncio.sleep(2.0)

    pass_n = sum(1 for r in rows if r.get("refuse_heuristic") is True)
    fail_n = sum(1 for r in rows if r.get("refuse_heuristic") is False)
    return {
        "skipped": False,
        "mcp_id": mcp_id,
        "questions": rows,
        "summary": {
            "total": len(rows),
            "refuse_pass": pass_n,
            "refuse_fail": fail_n,
            "inconclusive": len(rows) - pass_n - fail_n,
        },
    }


def build_report(*, skip_mcp: bool, checklist: dict) -> dict:
    static = run_static_guard(checklist)
    mcp: dict
    if skip_mcp:
        mcp = {"skipped": True, "reason": "skip_mcp_flag"}
    else:
        try:
            mcp = asyncio.run(_run_mcp_questions(checklist))
        except Exception as exc:
            mcp = {"skipped": True, "reason": "mcp_error", "error": str(exc)[:400]}

    mcp_ok = mcp.get("skipped") or (mcp.get("summary", {}).get("refuse_fail", 0) == 0 and mcp.get("summary", {}).get("refuse_pass", 0) > 0)
    overall_ok = static.get("static_ok") and mcp_ok

    return {
        "schema": "notebooklm_theory_mathematization_nl_guard_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "checklist": str(CHECKLIST.relative_to(ROOT)).replace("\\", "/"),
        "static_guard": static,
        "mcp_guard": mcp,
        "aggregate": {
            "static_ok": static.get("static_ok"),
            "mcp_ok": mcp_ok,
            "all_ok": overall_ok,
        },
        "reproduce": "py scripts/run_notebooklm_theory_mathematization_nl_guard_smoke_v1.py",
    }


def write_report(doc: dict, *, skip_mcp: bool = False) -> None:
    payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(payload, encoding="utf-8")
    if skip_mcp:
        static_art = ROOT / "docs/final/artifacts/notebooklm_theory_mathematization_nl_guard_smoke_static_v1_latest.json"
        static_art.write_text(payload, encoding="utf-8")
    else:
        OUT_ARTIFACT.write_text(payload, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-mcp", action="store_true", help="Static pack/canon guard only")
    ap.add_argument(
        "--ensure-mcp-register",
        action="store_true",
        help="Run register_notebooklm_theory_mathematization_mcp_v1.py before MCP asks",
    )
    args = ap.parse_args()

    if args.ensure_mcp_register and not args.skip_mcp:
        reg = subprocess.run(
            [sys.executable, "scripts/register_notebooklm_theory_mathematization_mcp_v1.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if reg.returncode != 0:
            print(reg.stderr or reg.stdout, file=sys.stderr)

    checklist = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    doc = build_report(skip_mcp=args.skip_mcp, checklist=checklist)
    write_report(doc, skip_mcp=args.skip_mcp)
    agg = doc["aggregate"]
    print(
        json.dumps(
            {
                "ok": agg.get("all_ok"),
                "static_ok": agg.get("static_ok"),
                "mcp_ok": agg.get("mcp_ok"),
                "report_out": str(OUT_REPORT),
            },
            ensure_ascii=False,
        )
    )
    return 0 if agg.get("all_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
