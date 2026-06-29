#!/usr/bin/env python3
"""Build commander manual RQ CLOSED checklist ([HYPO] · agent must not auto-close)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "reports/a_code_rq_close_gate_v1_latest.json"
DEFAULT_CONDITIONS = ROOT / "experiments/a_code_12ai_v2/specs/a_code_rq_close_conditions_v1.json"
DEFAULT_RESEARCH = ROOT / "docs/research/RESEARCH_OPEN_QUESTIONS_V1.md"
DEFAULT_OUT_JSON = ROOT / "reports/a_code_rq_close_human_checklist_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/a_code_rq_close_human_checklist_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_checklist(
    *,
    gate: dict[str, Any],
    conditions: dict[str, Any],
) -> dict[str, Any]:
    summary = gate.get("summary") or {}
    mechanical = summary.get("mechanical_close_candidate") is True
    rq_close_allowed = summary.get("rq_close_allowed") is True

    manual_steps = [
        {
            "id": "verify_smoke_local",
            "label_ko": "로컬 smoke green 확인",
            "command": "powershell -File scripts/Invoke-MkmPersonaHealth_v1.ps1 -Persona ACodeGovernorSmoke",
            "auto_done": False,
        },
        {
            "id": "review_archive_pack",
            "label_ko": "archive pack·lane gate·pointer row 산출물 육안 확인",
            "artifact": "reports/a_code_governor_signoff_archive_pack_v1_latest.json",
            "auto_done": mechanical,
        },
        {
            "id": "set_human_close_env",
            "label_ko": "RQ CLOSED 승인 시에만 User env MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED=1 (세션/PC 한정)",
            "auto_done": rq_close_allowed,
        },
        {
            "id": "record_commander_close",
            "label_ko": "record_a_code_rq_commander_close_v1.py 실행 (--close-reference 지정)",
            "command": "py scripts/record_a_code_rq_commander_close_v1.py --close-reference COMMANDER-ACODE-RQ-CLOSE-YYYY-MM-DD",
            "auto_done": False,
            "agent_forbidden": True,
        },
        {
            "id": "review_migration_draft",
            "label_ko": "RESEARCH close migration draft 확인 후 수동 이관",
            "artifact": "reports/a_code_research_close_migration_draft_v1_latest.md",
            "auto_done": False,
            "agent_forbidden": True,
        },
        {
            "id": "edit_research_open_questions",
            "label_ko": "docs/research/RESEARCH_OPEN_QUESTIONS_V1.md 에 RQ-028/029/031 수동 CLOSED 행 갱신",
            "path": "docs/research/RESEARCH_OPEN_QUESTIONS_V1.md",
            "auto_done": False,
            "agent_forbidden": True,
        },
        {
            "id": "no_track_a_live_claim",
            "label_ko": "Track A·live·MS paste 승격 문구·체인 합선 없음 재확인",
            "auto_done": True,
        },
    ]

    return {
        "schema": "a_code_rq_close_human_checklist_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_ids": gate.get("rq_ids") or conditions.get("rq_ids") or ["RQ-028", "RQ-029", "RQ-031"],
        "hypothesis_tier": "B",
        "research_only": True,
        "summary": {
            "gate_decision": summary.get("decision"),
            "mechanical_close_candidate": mechanical,
            "rq_close_allowed": rq_close_allowed,
            "ready_for_human_close_review": mechanical,
            "agent_auto_close_forbidden": True,
        },
        "manual_steps": manual_steps,
        "conditions_spec": str(DEFAULT_CONDITIONS.relative_to(ROOT)).replace("\\", "/"),
        "gate_report": str(DEFAULT_GATE.relative_to(ROOT)).replace("\\", "/"),
        "research_ssot": str(DEFAULT_RESEARCH.relative_to(ROOT)).replace("\\", "/"),
        "track_wall_note_ko": "본 체크리스트는 지휘관 수동 이관용. 에이전트가 RESEARCH CLOSED를 자동 갱신하지 않음.",
        "reproduction_commands": [
            "py scripts/build_a_code_rq_close_human_checklist_v1.py",
            "py scripts/check_a_code_rq_close_gate_v1.py",
        ],
    }


def render_md(doc: dict[str, Any]) -> str:
    s = doc.get("summary") or {}
    lines = [
        "# A-code RQ close — commander manual checklist",
        "",
        f"- generated_at_utc: `{doc.get('generated_at_utc')}`",
        f"- gate_decision: `{s.get('gate_decision')}`",
        f"- mechanical_close_candidate: `{s.get('mechanical_close_candidate')}`",
        f"- rq_close_allowed: `{s.get('rq_close_allowed')}`",
        "",
        "## Track wall",
        "",
        "- 에이전트 **자동 RQ CLOSED 금지**",
        "- Track A · live · MS paste 승격 **없음**",
        "",
        "## Manual steps (지휘관)",
        "",
    ]
    for i, step in enumerate(doc.get("manual_steps") or [], start=1):
        flag = "AUTO-OK" if step.get("auto_done") else "TODO"
        if step.get("agent_forbidden"):
            flag = "HUMAN-ONLY"
        lines.append(f"{i}. **[{flag}]** {step.get('label_ko')}")
        if step.get("command"):
            lines.append(f"   - `{step.get('command')}`")
        if step.get("artifact"):
            lines.append(f"   - artifact: `{step.get('artifact')}`")
        if step.get("path"):
            lines.append(f"   - path: `{step.get('path')}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    gate = _read(args.gate)
    conditions = _read(args.conditions)
    if not gate:
        raise SystemExit(f"missing gate report: {args.gate} (run check_a_code_rq_close_gate_v1.py first)")

    doc = build_checklist(gate=gate, conditions=conditions)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(doc), encoding="utf-8")
    print(
        f"OK: {args.out_json} ready_for_review={doc['summary']['ready_for_human_close_review']} "
        f"rq_close_allowed={doc['summary']['rq_close_allowed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
