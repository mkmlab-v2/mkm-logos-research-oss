#!/usr/bin/env python3
"""RQ-031 P13: render CONSTITUTION/worklist pointer PR draft from migration JSON ([HYPO] · human PR only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MIGRATION = ROOT / "docs/final/artifacts/a_code_constitution_worklist_migration_draft_v1.json"
DEFAULT_LANE = ROOT / "docs/final/artifacts/a_code_operator_assist_lane_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/a_code_constitution_pointer_pr_draft_v1_latest.md"
DEFAULT_OUT_JSON = ROOT / "reports/a_code_constitution_pointer_pr_draft_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_pr_draft(
    *,
    migration: dict[str, Any],
    lane: dict[str, Any],
) -> dict[str, Any]:
    pointer = migration.get("proposed_constitution_pointer_row") or {}
    return {
        "schema": "a_code_constitution_pointer_pr_draft_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "status": "draft_for_human_pr",
        "human_pr_required": True,
        "rq_ids": migration.get("rq_ids") or ["RQ-028", "RQ-029", "RQ-031"],
        "research_only": True,
        "hypothesis_tier": "B",
        "lane_status": lane.get("lane_status"),
        "operator_lane_ready": lane.get("operator_lane_ready"),
        "suggested_pr_title": "docs: add A-code 12AI governor operator-assist pointer row (B-track [HYPO])",
        "suggested_branch": "docs/a-code-operator-assist-pointer-row",
        "constitution_pointer_row": pointer,
        "worklist_paragraph_ko": migration.get("proposed_worklist_paragraph_ko"),
        "pr_checklist": migration.get("pr_checklist") or [],
        "explicit_not_migrated": migration.get("explicit_not_migrated") or [],
        "track_wall": {
            "constitution_auto_edit": False,
            "track_a_auto_promotion": False,
            "live_trading_auto_trigger": False,
        },
        "sources": {
            "migration_draft": "docs/final/artifacts/a_code_constitution_worklist_migration_draft_v1.json",
            "operator_lane": "docs/final/artifacts/a_code_operator_assist_lane_v1_latest.json",
        },
    }


def render_markdown(doc: dict[str, Any]) -> str:
    pointer = doc.get("constitution_pointer_row") or {}
    scripts = pointer.get("scripts") or []
    artifacts = pointer.get("artifacts") or []
    protocols = pointer.get("protocols") or []
    not_migrated = doc.get("explicit_not_migrated") or []
    checklist = doc.get("pr_checklist") or []

    lines = [
        "# A-code operator-assist CONSTITUTION pointer PR draft",
        "",
        f"- generated_at_utc: `{doc.get('generated_at_utc')}`",
        f"- status: `{doc.get('status')}` · **human PR only** · `[HYPO]` · `research_only`",
        f"- lane_status: `{doc.get('lane_status')}` · operator_lane_ready: `{doc.get('operator_lane_ready')}`",
        "",
        "## Suggested PR",
        "",
        f"- title: {doc.get('suggested_pr_title')}",
        f"- branch: `{doc.get('suggested_branch')}`",
        "",
        "## CONSTITUTION table row (copy-paste)",
        "",
        f"| {pointer.get('label', 'A-code 12AI governor operator-assist (B-track [HYPO])')} | "
        + " · ".join(f"`{s}`" for s in scripts[:3])
        + (" …" if len(scripts) > 3 else "")
        + " | "
        + " · ".join(f"`{a}`" for a in artifacts[:2])
        + (" …" if len(artifacts) > 2 else "")
        + " |",
        "",
        f"Note: {pointer.get('note_ko', '')}",
        "",
        "### Scripts",
        "",
    ]
    lines.extend(f"- `{s}`" for s in scripts)
    lines.extend(["", "### Artifacts", ""])
    lines.extend(f"- `{a}`" for a in artifacts)
    lines.extend(["", "### Protocols", ""])
    lines.extend(f"- `{p}`" for p in protocols)
    lines.extend(
        [
            "",
            "## MULTI_LENS worklist paragraph (ko)",
            "",
            doc.get("worklist_paragraph_ko") or "(missing)",
            "",
            "## Explicit NOT migrated",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in not_migrated)
    lines.extend(["", "## PR checklist", ""])
    lines.extend(f"- [ ] {item}" for item in checklist)
    lines.extend(
        [
            "",
            "## Track wall",
            "",
            "- CONSTITUTION **본문 법칙 변경 없음** — pointer 행만",
            "- Track A · live trading · MS paste **자동 승격 없음**",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--migration", type=Path, default=DEFAULT_MIGRATION)
    parser.add_argument("--lane", type=Path, default=DEFAULT_LANE)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    args = parser.parse_args()

    migration = _read(args.migration)
    if not migration:
        raise SystemExit(f"missing migration draft: {args.migration}")

    lane = _read(args.lane)
    doc = build_pr_draft(migration=migration, lane=lane)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_markdown(doc), encoding="utf-8")
    print(f"OK: {args.out_md}")
    print(f"OK: {args.out_json} lane_status={doc.get('lane_status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
