#!/usr/bin/env python3
"""Daily evolution / AI-tech radar — candidates only; human approval before any apply.

B-track · research_only · auto_apply none. Does not mutate Track A or live trading.
Network fetch is opt-in (MKM_EVOLUTION_RADAR_FETCH=1); default is disk SSOT scan only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "mkm_evolution_radar_daily_v1_latest.json"
RESEARCH_OPEN = ROOT / "docs" / "research" / "RESEARCH_OPEN_QUESTIONS_V1.md"
ALLOWLIST = ROOT / "docs" / "final" / "artifacts" / "evolution_auto_apply_allowlist_v1_latest.json"
CURSOR_CHANGELOG = (
    ROOT / "projects" / "bitcoin-trading" / "ops" / "v2" / "CURSOR_CHANGELOG_INTEGRATION_PLAN_2026-03-24.md"
)
EVOLUTION_DRAFT = ROOT / "docs" / "final" / "artifacts" / "autonomous_evolution_loop_draft_v1_latest.json"
PRESERVE_KINDS = frozenset(
    {
        "exa_product_fact_review",
        "human_review_queue",
        "manual_followup",
    }
)

OPEN_RE = re.compile(r"\[OPEN\]", re.I)
TECH_KW = re.compile(
    r"(cursor|agent|mcp|llm|evolution|자율|압축|compression|notebooklm|cloud|gemini|claude)",
    re.I,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _scan_research_open() -> list[dict[str, Any]]:
    text = _read_text(RESEARCH_OPEN)
    if not text:
        return []
    candidates: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if not OPEN_RE.search(line) or not TECH_KW.search(line):
            continue
        title = line.strip()[:200]
        candidates.append(
            {
                "id": f"research_open_L{i}",
                "title": title,
                "source": "docs/research/RESEARCH_OPEN_QUESTIONS_V1.md",
                "kind": "research_queue",
                "approval_status": "pending",
                "suggested_action": "commander_review_in_chat",
            }
        )
    return candidates[:15]


def _allowlist_reminder() -> dict[str, Any]:
    if not ALLOWLIST.is_file():
        return {"present": False}
    doc = json.loads(ALLOWLIST.read_text(encoding="utf-8-sig"))
    signoff = doc.get("human_signoff_required_for") or []
    return {
        "present": True,
        "research_only": doc.get("research_only"),
        "human_signoff_required_for": signoff[:12],
        "forbidden_targets": (doc.get("forbidden_targets") or [])[:8],
    }


def _cursor_changelog_hint() -> dict[str, Any]:
    if not CURSOR_CHANGELOG.is_file():
        return {"present": False}
    st = CURSOR_CHANGELOG.stat()
    return {
        "present": True,
        "path": str(CURSOR_CHANGELOG.relative_to(ROOT)).replace("\\", "/"),
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "suggested_action": "agent_reads_changelog_section_3_3_3_4_on_commander_approval",
    }


def _evolution_draft_pointer() -> dict[str, Any]:
    if not EVOLUTION_DRAFT.is_file():
        return {"present": False}
    doc = json.loads(EVOLUTION_DRAFT.read_text(encoding="utf-8-sig"))
    return {
        "present": True,
        "dry_run": doc.get("dry_run"),
        "gate_exit_code": (doc.get("gate_minimal") or {}).get("exit_code"),
        "proposal_count": len(doc.get("proposals") or []),
    }


def _preserved_manual_candidates(existing: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not existing or existing.get("schema") != "mkm_evolution_radar_daily_v1":
        return []
    out: list[dict[str, Any]] = []
    for c in existing.get("candidates") or []:
        if not isinstance(c, dict):
            continue
        if c.get("preserve_on_daily_rebuild") is True or c.get("kind") in PRESERVE_KINDS:
            out.append(c)
    return out


def build_radar(*, include_fetch: bool, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    preserved = _preserved_manual_candidates(existing)
    preserved_ids = {str(c.get("id")) for c in preserved if c.get("id")}
    candidates = list(preserved)
    for row in _scan_research_open():
        if str(row.get("id")) not in preserved_ids:
            candidates.append(row)
    if include_fetch and "fetch_not_implemented_v1" not in preserved_ids:
        candidates.append(
            {
                "id": "fetch_not_implemented_v1",
                "title": "MKM_EVOLUTION_RADAR_FETCH=1 set but RSS/Exa ingest not wired — use chat Exa/NotebookLM on approval",
                "source": "build_mkm_evolution_radar_daily_v1",
                "kind": "manual_followup",
                "approval_status": "pending",
                "suggested_action": "agent_web_research_after_commander_approval",
                "preserve_on_daily_rebuild": True,
            }
        )

    return {
        "schema": "mkm_evolution_radar_daily_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "human_approval_required": True,
        "auto_apply": "none",
        "allowlist_ssot": str(ALLOWLIST.relative_to(ROOT)).replace("\\", "/"),
        "allowlist_summary": _allowlist_reminder(),
        "cursor_changelog": _cursor_changelog_hint(),
        "evolution_draft_latest": _evolution_draft_pointer(),
        "candidates": candidates,
        "commander_approval_contract": {
            "approve_phrase_examples": [
                "승인: research_open_L42",
                "승인: cursor_changelog_review",
                "승인: exa_mcp_permissions_review",
                "승인: myeongri_interpret_v4_calibration30_review",
            ],
            "append_script": "scripts/append_mkm_evolution_radar_candidate_v1.py",
            "fixture_examples": [
                "docs/final/artifacts/fixtures/mkm_evolution_radar_candidate_exa_mcp_v1.example.json",
                "docs/final/artifacts/fixtures/mkm_evolution_radar_candidate_myeongri_cal30_v1.example.json",
            ],
            "reject_phrase": "거절: <id>",
            "note_ko": (
                "승인 전 레포 자동 변경·Track A 승격·실매매 합선 금지. "
                "Exa fetch는 live fact 수집 로그이며 구현·통과 증명 아님."
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--fetch",
        action="store_true",
        help="Set fetch flag (ingest still manual/agent; records placeholder)",
    )
    args = ap.parse_args()
    env_fetch = os.environ.get("MKM_EVOLUTION_RADAR_FETCH", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    existing: dict[str, Any] | None = None
    if args.out_json.is_file():
        try:
            existing = json.loads(args.out_json.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            existing = None
    doc = build_radar(include_fetch=bool(args.fetch or env_fetch), existing=existing)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out_json} candidates={len(doc['candidates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
