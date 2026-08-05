#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ops queue morning elementary brief v1 (research_only · thin).

Reads AutonomousPatrol latest (paste_line + manual_queue) and ops event inbox
status (drain-safe read — no drain/mutate). Emits pending_approvals YES/NO
scaffold only. Does NOT approve→apply, SEND OPEN, Track A, Temporal, or
unattended coding.

Usage:
  py scripts/build_mkm_ops_queue_morning_brief_v1.py

Artifacts:
  docs/final/artifacts/mkm_ops_queue_morning_brief_v1_latest.json
  docs/final/artifacts/mkm_ops_queue_morning_brief_v1_latest.md
  reports/human_paste/mkm_ops_queue_morning_brief_elementary_v1.txt
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from run_mkm_ops_event_inbox_v1 import JSONL as INBOX_JSONL  # noqa: E402
from run_mkm_ops_event_inbox_v1 import _load_rows, status as inbox_status  # noqa: E402

PATROL = ROOT / "reports" / "mkm_autonomous_patrol_latest.json"
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "mkm_ops_queue_morning_brief_v1_latest.json"
OUT_MD = ROOT / "docs" / "final" / "artifacts" / "mkm_ops_queue_morning_brief_v1_latest.md"
OUT_PASTE = ROOT / "reports" / "human_paste" / "mkm_ops_queue_morning_brief_elementary_v1.txt"
SCHEMA = "mkm_ops_queue_morning_brief_v1"

DONE_CARDS = [
    {
        "id": "DC1",
        "user_visible_outcome": "Morning elementary paste shows patrol + inbox queue in one place",
        "pass_evidence": "artifact+paste exit0 · paste_line present",
        "non_scope": "approve→apply latch · SEND · Track A · Temporal",
        "status": "DONE",
    },
    {
        "id": "DC2",
        "user_visible_outcome": "Script reads manual_queue + inbox status without draining",
        "pass_evidence": "inbox mode=status · drain_mutated=false",
        "non_scope": "auto drain apply · overnight coding job",
        "status": "DONE",
    },
    {
        "id": "DC3",
        "user_visible_outcome": "Walls stamped: research_only · SEND HOLD · harness≠unattended coding DONE",
        "pass_evidence": "walls block in JSON/MD/paste",
        "non_scope": "claim long-loop unattended coding complete",
        "status": "DONE",
    },
    {
        "id": "DC3b",
        "user_visible_outcome": "pending_approvals YES/NO scaffold lists actionable queue items (no auto-apply)",
        "pass_evidence": "pending_approvals[] in JSON/MD/paste · auto_apply=false",
        "non_scope": "M approve→apply latch · stamp→merge",
        "status": "DONE",
    },
    {
        "id": "DC4",
        "user_visible_outcome": "M approve→apply latch",
        "pass_evidence": "scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py · allowlist+stamps+receipt",
        "non_scope": "auto-apply from this brief · SEND · Track A",
        "status": "DONE",
    },
    {
        "id": "DC5",
        "user_visible_outcome": "L overnight / Temporal / Cursor long-running agents",
        "pass_evidence": "documented HOLD only (not this unlock)",
        "non_scope": "this unlock",
        "status": "HOLD",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _local_date() -> str:
    try:
        return datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    except Exception:
        return datetime.now().date().isoformat()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        return doc if isinstance(doc, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _needs_commander_preview(limit: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in _load_rows():
        if r.get("status") != "needs_commander":
            continue
        out.append(
            {
                "event_id": r.get("event_id"),
                "action": r.get("action"),
                "lane": r.get("lane"),
                "source": r.get("source"),
                "created_at_utc": r.get("created_at_utc"),
            }
        )
        if len(out) >= limit:
            break
    return out


def _build_pending_approvals(
    manual: list[Any],
    needs_preview: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """YES/NO scaffold only — never auto-apply / drain / merge."""
    rows: list[dict[str, Any]] = []
    for item in manual:
        if not isinstance(item, dict):
            continue
        mid = str(item.get("id") or "").strip() or "unknown"
        label = str(item.get("label_ko") or item.get("reason") or mid).strip()
        rows.append(
            {
                "source": "manual_queue",
                "id": mid,
                "label": label,
                "reason": item.get("reason"),
                "scaffold": "YES / NO",
                "prompt_ko": f"[ ] YES 승인 · [ ] NO 보류 — {mid}: {label}",
                "if_yes": "지휘관 채팅/명령으로 명시 승인 후 해당 수동 스크립트만 (본 브리프가 apply 하지 않음)",
                "if_no": "대기열 유지 · 자동 실행 없음",
                "auto_apply": False,
            }
        )
    for ev in needs_preview:
        eid = str(ev.get("event_id") or "").strip() or "unknown"
        action = str(ev.get("action") or "").strip() or "(action)"
        rows.append(
            {
                "source": "ops_inbox",
                "id": eid,
                "label": action,
                "lane": ev.get("lane"),
                "event_source": ev.get("source"),
                "scaffold": "YES / NO",
                "prompt_ko": f"[ ] YES 승인 · [ ] NO 보류 — inbox:{eid} · {action}",
                "if_yes": "지휘관 명시 ACK 후 inbox drain/apply 경로만 (본 브리프 ≠ drain)",
                "if_no": "needs_commander 유지 · 자동 drain 금지",
                "auto_apply": False,
            }
        )
    return rows


def build() -> dict[str, Any]:
    patrol = _load_json(PATROL) or {}
    inbox = inbox_status()
    # status() rewrites drain-latest to status mode — intentional read-safe stamp
    manual = patrol.get("manual_queue") if isinstance(patrol.get("manual_queue"), list) else []
    counts = inbox.get("counts") if isinstance(inbox.get("counts"), dict) else {}
    pending = int(counts.get("pending") or 0)
    needs = int(counts.get("needs_commander") or 0)
    blocked = int(counts.get("blocked") or 0)
    local_date = _local_date()
    paste_line = str(patrol.get("paste_line") or "").strip()
    overall = str(patrol.get("overall") or ("OK" if patrol.get("ok") else "MISSING"))
    patrol_present = PATROL.is_file()
    inbox_present = INBOX_JSONL.is_file()
    needs_preview = _needs_commander_preview()
    pending_approvals = _build_pending_approvals(manual, needs_preview)

    one_liner = (
        f"[OpsMorningBrief] {local_date} patrol={overall} "
        f"manual={len(manual)} inbox_pending={pending} needs_commander={needs} "
        f"pending_approvals={len(pending_approvals)} "
        f"| research_only · SEND HOLD · ≠unattended coding DONE · ≠auto-apply"
    )

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "local_date": local_date,
        "research_only": True,
        "send_gate": "HOLD",
        "track_a": "FROZEN",
        "drain_mutated": False,
        "auto_apply": False,
        "ok": bool(patrol_present),
        "one_liner": one_liner,
        "sources": {
            "patrol": {
                "path": str(PATROL.as_posix()),
                "present": patrol_present,
                "overall": overall,
                "ok": patrol.get("ok"),
                "last_run_local_date": patrol.get("last_run_local_date"),
                "paste_line": paste_line or None,
                "manual_queue_count": len(manual),
            },
            "ops_inbox": {
                "jsonl": str(INBOX_JSONL.as_posix()),
                "present": inbox_present,
                "status": inbox,
                "needs_commander_preview": needs_preview,
            },
        },
        "manual_queue": manual,
        "pending_approvals": pending_approvals,
        "pending_approvals_count": len(pending_approvals),
        "walls_ko": [
            "읽기+초등 브리프만 — drain/apply/merge 자동 금지",
            "pending_approvals = YES/NO 스캐폴드만 · auto_apply=false (승인≠적용)",
            "approve→apply 래치 = M · run_mkm_hitl_ops_approve_apply_latch_v1 (본 브리프≠apply)",
            "장시간 무인 코딩 / Temporal / SEND OPEN / Track A / 실매매 = 금지",
            "Cursor 무제한 ≠ PC/채팅 꺼져도 24h 혼자 코딩 (트리거·스케줄 필요)",
            "AutonomousPatrol ≠ 과학자 자율진화 · companion≠LTM · Ollama chat❌/pipeline✅",
        ],
        "done_cards": DONE_CARDS,
        "reproduce": [
            "py scripts/build_mkm_ops_queue_morning_brief_v1.py",
            "py scripts/run_mkm_ops_event_inbox_v1.py status",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Test-MkmSoloCoreStackTaskMembership_v1.ps1 -TaskName MKM_AutonomousPatrol_Daily",
        ],
        "non_scope": [
            "auto_apply_from_brief",
            "L_overnight_coding",
            "SEND_OPEN",
            "Track_A",
            "Temporal",
            "unattended_coding_DONE",
        ],
        "m_latch_pointer": "scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py",
    }

    md_lines = [
        f"# Ops queue morning brief v1 — {local_date}",
        "",
        f"**one_liner:** `{one_liner}`",
        "",
        "## Patrol",
        f"- path: `{PATROL.as_posix()}` present={patrol_present}",
        f"- overall: **{overall}** · last_run_local_date={patrol.get('last_run_local_date')}",
        f"- paste_line: {paste_line or '(missing)'}",
        f"- manual_queue: **{len(manual)}**",
        "",
    ]
    if manual:
        md_lines.append("| id | label_ko | reason |")
        md_lines.append("|----|----------|--------|")
        for item in manual:
            if not isinstance(item, dict):
                continue
            md_lines.append(
                f"| `{item.get('id')}` | {item.get('label_ko') or ''} | {item.get('reason') or ''} |"
            )
        md_lines.append("")
    md_lines.extend(
        [
            "## pending_approvals (YES/NO scaffold · no auto-apply)",
            f"- count: **{len(pending_approvals)}** · auto_apply=false · ≠ M latch",
            "",
        ]
    )
    if pending_approvals:
        md_lines.append("| source | id | scaffold | prompt_ko |")
        md_lines.append("|--------|----|----------|-----------|")
        for row in pending_approvals:
            md_lines.append(
                f"| `{row.get('source')}` | `{row.get('id')}` | {row.get('scaffold')} | {row.get('prompt_ko') or ''} |"
            )
        md_lines.append("")
    else:
        md_lines.append("_empty — no manual_queue / needs_commander items_")
        md_lines.append("")
    md_lines.extend(
        [
            "## Ops inbox (status · no drain)",
            f"- jsonl: `{INBOX_JSONL.as_posix()}` present={inbox_present}",
            f"- counts: `{json.dumps(counts, ensure_ascii=False)}`",
            f"- pending={pending} · needs_commander={needs} · blocked={blocked}",
            "",
            "## Walls",
        ]
    )
    for w in doc["walls_ko"]:
        md_lines.append(f"- {w}")
    md_lines.extend(
        [
            "",
            "## Done cards",
        ]
    )
    for c in DONE_CARDS:
        md_lines.append(
            f"- **{c['id']}** `{c['status']}` — {c['user_visible_outcome']}"
        )
    md_lines.extend(
        [
            "",
            "## Reproduce",
            "```",
            "py scripts/build_mkm_ops_queue_morning_brief_v1.py",
            "```",
            "",
            f"schema={SCHEMA} · research_only · send_gate=HOLD",
        ]
    )

    paste = "\n".join(
        [
            "【초등】아침 ops 대기열 브리프 (patrol manual_queue + inbox)",
            f"날짜: {local_date} · research_only · SEND HOLD · Track A 금지",
            "",
            "■ 한 줄",
            one_liner,
            "",
            "■ AutonomousPatrol",
            f"- overall: {overall}",
            f"- paste_line: {paste_line or '(없음 — 자율루프 먼저)'}",
            f"- manual_queue: {len(manual)}건 (사람만 · 자동 실행 금지)",
        ]
    )
    if manual:
        paste += "\n"
        for item in manual:
            if not isinstance(item, dict):
                continue
            paste += (
                f"  · {item.get('id')}: {item.get('label_ko') or item.get('reason')}\n"
            )
    paste += "\n".join(
        [
            "",
            "■ pending_approvals (YES/NO · auto_apply=false · 승인≠적용)",
            f"- count: {len(pending_approvals)}",
        ]
    )
    if pending_approvals:
        paste += "\n"
        for row in pending_approvals:
            paste += f"  · {row.get('prompt_ko')}\n"
            paste += f"      if_yes: {row.get('if_yes')}\n"
            paste += f"      if_no: {row.get('if_no')}\n"
    else:
        paste += "\n  · (비어 있음)\n"
    paste += "\n".join(
        [
            "",
            "■ ops event inbox (status · drain 안 함)",
            f"- pending={pending} · needs_commander={needs} · blocked={blocked}",
            f"- jsonl: reports/mkm_ops_event_inbox_v1.jsonl",
            "",
            "■ 복붙",
            "py scripts/build_mkm_ops_queue_morning_brief_v1.py",
            "",
            "■ 벽",
            "- 이 브리프 ≠ 장시간 무인 코딩 완성 · ≠ Cursor 무제한=24h 혼자 코딩",
            "- pending_approvals = 스캐폴드만 · ≠ approve→apply(M) · ≠ overnight/Temporal(L) · ≠ SEND OPEN",
            "",
            f"End · {OUT_PASTE.as_posix().replace(str(ROOT).replace(chr(92), '/') + '/', '')}",
            "",
        ]
    )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_PASTE.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    OUT_PASTE.write_text(paste, encoding="utf-8")
    return doc


def main() -> int:
    doc = build()
    print(json.dumps({"ok": doc.get("ok"), "one_liner": doc.get("one_liner"), "out": str(OUT_JSON.as_posix())}, ensure_ascii=False))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
