#!/usr/bin/env python3
"""Build Cursor-facing prompt pack for OpenData 327 grant agent tasks (LLM + script gates)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTE = ROOT / "reports/opendata_327_grant_model_route_v1_latest.json"
DEFAULT_TASKS = ROOT / "data/grant_proposal/opendata_327_draft_tasks_v1.jsonl"
DEFAULT_JSON_OUT = ROOT / "docs/final/artifacts/opendata_327_grant_agent_prompt_pack_v1_latest.json"
DEFAULT_MD_OUT = ROOT / "docs/final/artifacts/opendata_327_grant_agent_prompt_pack_v1_latest.md"

FORBIDDEN_PHRASES = [
    "47%",
    "0.47",
    "LG",
    "compression OEM",
    "Safety PLC",
    "실매매",
    "Track A",
    "hallucination-free",
]

SCRIPT_COMMANDS: dict[str, list[str]] = {
    "grep_evidence": [
        "py scripts/check_opendata_327_pre_export_gates_v1.py",
        "# then grep submission MDs for forbidden tokens (no LG / 47% / compression headline)",
    ],
    "fact_lock_claim": [
        "py scripts/verify_p0_constitution_gate_paths.ps1  # or run_fact_lock_bundle -Skip* as policy allows",
    ],
    "implementation_claim": [
        "py scripts/build_opendata_327_submission_readiness_v1.py",
        "# read reports/opendata_327_submission_readiness_latest.json — do not claim K-Startup submit complete",
    ],
    "json_field_copy": [
        "# Read ssot_ref verbatim; paste into target section only — no paraphrase of legal/control paragraphs",
    ],
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("C:") or p.startswith("/"):
        try:
            return Path(p).resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return p
    return p


def load_tasks_index(path: Path) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        idx[str(row["task_id"])] = row
    return idx


def load_route(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def llm_prompt_for_task(route: dict[str, Any], task_row: dict[str, Any]) -> str:
    ssot = _rel(str(task_row.get("ssot_ref") or ""))
    section = str(task_row.get("section") or "")
    notes = str(route.get("notes") or task_row.get("notes") or "")
    kind = str(route.get("task_kind"))
    tier = str(route.get("model_tier"))

    forbidden = ", ".join(FORBIDDEN_PHRASES[:6])

    base = (
        f"[OpenData 327 · research_only · {tier}]\n"
        f"SSOT: `{ssot}` · section: `{section}`\n"
        f"Goal: {notes}\n"
        f"FORBIDDEN in output: {forbidden}.\n"
        "Do not invent patent numbers, deployment URLs, or implementation-done claims.\n"
        "Mark uncertain lines with `[DRAFT]`; cite SSOT headings only.\n"
    )

    if kind == "outline":
        return (
            base
            + "\nProduce a **section outline only** (bullet headings matching 공고 별첨 order). "
            "No full prose. Max 40 lines."
        )
    if kind == "table_fill":
        return (
            base
            + "\nFill **table cells only** from SSOT numbers already present. "
            "If a cell lacks SSOT backing, leave `[TBD — human]`."
            + (" Commander must confirm §2-2 before submit." if "2-2" in notes or section else "")
        )
    if kind == "narrative_section":
        return (
            base
            + "\nDraft **one section** in formal Korean business-plan tone. "
            "RAG/slot/integrity-gate narrative only (과제①). No mkmlife/compression pitch."
        )
    if kind == "business_model":
        return (
            base
            + "\nDraft **market/business model** subsection from part_c SSOT. "
            "No revenue % promises; no compression API resell."
        )
    if kind == "risk_legal":
        return (
            base
            + "\nExtract **control/risk paragraphs** from Annex SSOT for paste-in. "
            "Prefer verbatim quotes with source line refs; minimal rewriting."
        )
    return base + f"\nTask kind `{kind}`: follow SSOT; output markdown fragment only."


def script_pack_for_task(route: dict[str, Any], task_row: dict[str, Any]) -> dict[str, Any]:
    kind = str(route.get("task_kind"))
    cmds = list(SCRIPT_COMMANDS.get(kind, []))
    ssot = _rel(str(task_row.get("ssot_ref") or ""))
    return {
        "task_id": route["task_id"],
        "task_kind": kind,
        "ssot_ref": ssot,
        "section": task_row.get("section"),
        "commands": cmds,
        "pass_criterion": "exit 0 + artifact/json matches SSOT; no LLM prose",
        "notes": route.get("notes"),
    }


def build_pack(route_doc: dict[str, Any], tasks_idx: dict[str, dict[str, Any]]) -> dict[str, Any]:
    routes = route_doc.get("routes") or []

    llm_tasks: list[dict[str, Any]] = []
    script_tasks: list[dict[str, Any]] = []
    human_tasks: list[dict[str, Any]] = []

    for route in routes:
        tid = str(route["task_id"])
        task_row = tasks_idx.get(tid, {})
        if route.get("requires_human"):
            human_tasks.append(
                {
                    "task_id": tid,
                    "notes": route.get("notes"),
                    "owner": "human",
                    "action": "지휘관 1회 — 에이전트 초안 금지",
                }
            )
            continue
        if route.get("requires_script_gate"):
            script_tasks.append(script_pack_for_task(route, task_row))
            continue
        if route.get("invoke_llm_planned"):
            llm_tasks.append(
                {
                    "task_id": tid,
                    "task_kind": route.get("task_kind"),
                    "model_tier": route.get("model_tier"),
                    "model_slot_hint": route.get("model_slot_hint"),
                    "ssot_ref": _rel(str(task_row.get("ssot_ref") or "")),
                    "section": task_row.get("section"),
                    "cursor_user_prompt": llm_prompt_for_task(route, task_row),
                }
            )

    return {
        "schema": "opendata_327_grant_agent_prompt_pack_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "grant_program": "opendata_327",
        "route_pointer": str(DEFAULT_ROUTE.resolve()),
        "counts": {
            "llm_draft": len(llm_tasks),
            "script_gate": len(script_tasks),
            "human_only": len(human_tasks),
        },
        "forbidden": route_doc.get("forbidden", []),
        "cursor_chat_opener": (
            "@docs/final/artifacts/opendata_327_grant_agent_prompt_pack_v1_latest.md "
            "OpenData 327 초안만. HWPX/K-Startup 자동제출 금지. "
            "LLM 8건 순서대로, script 9건은 명령만 실행, human 12건 스킵."
        ),
        "llm_draft_tasks": llm_tasks,
        "script_gate_tasks": script_tasks,
        "human_blocked_tasks": human_tasks,
    }


def render_md(pack: dict[str, Any]) -> str:
    lines = [
        "# OpenData 327 — Grant Agent Prompt Pack",
        "",
        f"- generated_at_utc: `{pack['generated_at_utc']}`",
        f"- research_only: `{pack['research_only']}`",
        f"- llm_draft: **{pack['counts']['llm_draft']}** · script_gate: **{pack['counts']['script_gate']}** · human: **{pack['counts']['human_only']}**",
        "",
        "## Cursor chat opener (copy)",
        "",
        "```",
        pack["cursor_chat_opener"],
        "```",
        "",
        "## A. LLM draft tasks (8) — tier_cheap → tier_premium",
        "",
    ]

    cheap = [t for t in pack["llm_draft_tasks"] if t.get("model_tier") == "tier_cheap"]
    premium = [t for t in pack["llm_draft_tasks"] if t.get("model_tier") == "tier_premium"]
    for label, group in (("tier_cheap", cheap), ("tier_premium", premium)):
        lines.append(f"### {label}")
        lines.append("")
        for t in group:
            lines += [
                f"#### `{t['task_id']}` · `{t['task_kind']}`",
                f"- ssot: `{t['ssot_ref']}` · section: `{t.get('section')}`",
                "",
                "**User prompt:**",
                "",
                "```",
                t["cursor_user_prompt"].strip(),
                "```",
                "",
            ]

    lines += [
        "## B. Script gate (9) — **runbook first**",
        "",
        "원클릭: `powershell -NoProfile -File scripts/Run-GrantProposalOpenData327ScriptGateB_v1.ps1`",
        "",
        "복붙 9단계: `@docs/final/artifacts/opendata_327_script_gate_runbook_v1_latest.md`",
        "",
        "### B detail (per task_id)",
        "",
    ]
    for t in pack["script_gate_tasks"]:
        lines.append(f"### `{t['task_id']}` · `{t['task_kind']}`")
        lines.append(f"- ssot: `{t['ssot_ref']}`")
        lines.append("- commands:")
        for c in t["commands"]:
            lines.append(f"  - `{c}`")
        lines.append("")

    lines += ["## C. Human only (12) — 에이전트 스킵", ""]
    for t in pack["human_blocked_tasks"]:
        lines.append(f"- `{t['task_id']}`: {t.get('notes')}")
    lines.append("")
    lines += ["## Forbidden", ""]
    for f in pack.get("forbidden", []):
        lines.append(f"- `{f}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--route-json", type=Path, default=DEFAULT_ROUTE)
    ap.add_argument("--tasks-jsonl", type=Path, default=DEFAULT_TASKS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON_OUT)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD_OUT)
    args = ap.parse_args()

    route_doc = load_route(args.route_json)
    tasks_idx = load_tasks_index(args.tasks_jsonl)
    pack = build_pack(route_doc, tasks_idx)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(pack), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_json": str(args.out_json),
                "out_md": str(args.out_md),
                "counts": pack["counts"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
