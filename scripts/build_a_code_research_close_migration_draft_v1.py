#!/usr/bin/env python3
"""Draft RESEARCH_OPEN_QUESTIONS CLOSED rows for RQ-028/029/031 (human apply only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "reports/a_code_rq_close_gate_v1_latest.json"
DEFAULT_CLOSE = ROOT / "docs/final/artifacts/a_code_commander_close_v1_latest.json"
DEFAULT_CLOSURE = ROOT / "docs/final/artifacts/a_code_closure_readiness_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/a_code_research_close_migration_draft_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/a_code_research_close_migration_draft_v1_latest.md"
RESEARCH_PATH = "docs/research/RESEARCH_OPEN_QUESTIONS_V1.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _closed_row(
    rq_id: str,
    title_ko: str,
    close_ref: str | None,
    closed_date: str,
) -> str:
    evidence = (
        f"`a_code_commander_close_v1_latest.json` · close_reference `{close_ref}`"
        if close_ref
        else "`a_code_closure_readiness_v1_latest.json` · commander close **대기**"
    )
    return (
        f"| {rq_id} | **CLOSED** `[HYPO]` | **{title_ko}** | "
        f"**{closed_date}:** A-code B-track operator-assist sandbox archived · "
        f"mechanics bundle + commander close | {evidence} · "
        f"`experiments/a_code_12ai_v2/` | "
        f"Track A·live·MS **자동 합선 없음** · 재개=**새 RQ**"
    )


def build() -> dict[str, Any]:
    gate = _read(DEFAULT_GATE)
    close_doc = _read(DEFAULT_CLOSE)
    closure = _read(DEFAULT_CLOSURE)

    gate_summary = gate.get("summary") or {}
    close_ok = (
        close_doc.get("rq_028_closed") is True
        and close_doc.get("rq_029_closed") is True
        and close_doc.get("rq_031_closed") is True
    )
    close_ref = close_doc.get("close_reference") if close_ok else None
    closed_date = (close_doc.get("closed_at_utc") or _utc())[:10] if close_ok else _utc()[:10]

    row_specs = [
        (
            "RQ-028",
            "A-code 12AI v2/v2.5 — $4×3$ Cursor 오케스트레이션·병증약리 노브 샌드박스 (RQ-026 확장)",
        ),
        (
            "RQ-029",
            "A-code 승격 체크리스트 — mechanical readiness vs human sign-off 분리 (RQ-028 자식)",
        ),
        (
            "RQ-031",
            "A-code 운영자 보조 레인 승격 토의 — evening/TG·dev pack·Track C slice만 (RQ-028/029 자식)",
        ),
    ]

    suggested_rows = [_closed_row(rq, title, close_ref, closed_date) for rq, title in row_specs]

    ready_for_human_apply = close_ok and closure.get("closure_allowed") is True

    return {
        "schema": "a_code_research_close_migration_draft_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_ids": ["RQ-028", "RQ-029", "RQ-031"],
        "hypothesis_tier": "B",
        "research_only": True,
        "agent_auto_apply": False,
        "ready_for_human_apply": ready_for_human_apply,
        "target_file": RESEARCH_PATH,
        "gate_decision": gate_summary.get("decision"),
        "commander_close_present": close_ok,
        "closure_allowed": closure.get("closure_allowed"),
        "suggested_table_rows": suggested_rows,
        "human_steps_ko": [
            "reports/a_code_research_close_migration_draft_v1_latest.md 의 제안 행을 복사",
            f"{RESEARCH_PATH} 에서 RQ-028/029/031 OPEN 행을 찾아 수동 치환",
            "에이전트·스케줄러가 RESEARCH 파일을 자동 편집하지 않음",
            "Track A·live·MS 승격 문구 추가 금지",
        ],
        "boundary_ack": (
            "본 초안은 RESEARCH inbox 수동 이관 보조. CLOSED 표기 ≠ Track A·live 승격. "
            "experiments/a_code_12ai_v2/ 는 [HYPO]·research_only 유지."
        ),
    }


def render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# A-code RESEARCH close migration draft (human apply only)",
        "",
        f"- generated_at_utc: `{doc.get('generated_at_utc')}`",
        f"- ready_for_human_apply: `{doc.get('ready_for_human_apply')}`",
        f"- agent_auto_apply: `{doc.get('agent_auto_apply')}`",
        f"- target: `{doc.get('target_file')}`",
        "",
        "## Suggested table rows (copy-paste)",
        "",
        "```markdown",
    ]
    for row in doc.get("suggested_table_rows") or []:
        lines.append(row)
    lines.extend(
        [
            "```",
            "",
            "## Human steps",
            "",
        ]
    )
    for step in doc.get("human_steps_ko") or []:
        lines.append(f"- {step}")
    lines.extend(["", "## Track wall", "", doc.get("boundary_ack", ""), ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(doc), encoding="utf-8")
    print(
        f"OK: {args.out_json} ready_for_human_apply={doc.get('ready_for_human_apply')} "
        f"agent_auto_apply={doc.get('agent_auto_apply')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
