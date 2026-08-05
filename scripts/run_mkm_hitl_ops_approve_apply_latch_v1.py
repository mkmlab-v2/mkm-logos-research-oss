#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HITL ops approve→apply latch v1 (research_only · thin · allowlist-only).

Night body = Windows Scheduler (AutonomousPatrol). Morning = YES/NO stamp →
explicit --apply. Default is dry-run. Does NOT unlock SEND, Track A, live trade,
GitHub push, Temporal, or chat-24h persona.

Usage:
  py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py list
  py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py --approve rebuild_morning_brief
  py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py --revoke rebuild_morning_brief
  py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py              # dry-run
  py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py --apply --id rebuild_morning_brief

Artifacts:
  docs/final/artifacts/mkm_hitl_ops_apply_allowlist_v1_latest.json
  docs/final/artifacts/mkm_hitl_ops_approval_stamps_v1_latest.json
  docs/final/artifacts/mkm_hitl_ops_apply_receipt_v1_latest.json
  reports/human_paste/mkm_hitl_s_then_m_latch_elementary_v1.txt
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "docs" / "final" / "artifacts" / "mkm_hitl_ops_apply_allowlist_v1_latest.json"
STAMPS = ROOT / "docs" / "final" / "artifacts" / "mkm_hitl_ops_approval_stamps_v1_latest.json"
RECEIPT = ROOT / "docs" / "final" / "artifacts" / "mkm_hitl_ops_apply_receipt_v1_latest.json"
PASTE = ROOT / "reports" / "human_paste" / "mkm_hitl_s_then_m_latch_elementary_v1.txt"
SCHEMA_ALLOW = "mkm_hitl_ops_apply_allowlist_v1"
SCHEMA_STAMPS = "mkm_hitl_ops_approval_stamps_v1"
SCHEMA_RECEIPT = "mkm_hitl_ops_apply_receipt_v1"

DONE_CARDS = [
    {
        "id": "DC1",
        "user_visible_outcome": "S verify morning brief + inbox status + patrol membership exit 0",
        "pass_evidence": "Phase1 commands stamped in receipt/paste",
        "non_scope": "M latch · L Temporal",
        "status": "DONE",
    },
    {
        "id": "DC2",
        "user_visible_outcome": "Allowlist JSON lists only safe ops scripts",
        "pass_evidence": "mkm_hitl_ops_apply_allowlist_v1_latest.json",
        "non_scope": "git push · SEND · drain-destructive · trade",
        "status": "DONE",
    },
    {
        "id": "DC3",
        "user_visible_outcome": "Commander --approve <id> writes stamp JSON",
        "pass_evidence": "mkm_hitl_ops_approval_stamps_v1_latest.json",
        "non_scope": "stamp alone runs commands",
        "status": "DONE",
    },
    {
        "id": "DC4",
        "user_visible_outcome": "Apply runner dry-run default; --apply explicit",
        "pass_evidence": "receipt mode=dry_run|apply · exit0",
        "non_scope": "auto-apply from morning brief",
        "status": "DONE",
    },
    {
        "id": "DC5",
        "user_visible_outcome": "Walls: allowlist-only · SEND HOLD · Track A frozen · no live trade",
        "pass_evidence": "walls block + forbidden_action_ids reject",
        "non_scope": "unattended coding DONE claim",
        "status": "DONE",
    },
    {
        "id": "DC6",
        "user_visible_outcome": "L Cursor Automations / Temporal",
        "pass_evidence": "documented HOLD only",
        "non_scope": "this unlock",
        "status": "HOLD",
    },
    {
        "id": "DC7",
        "user_visible_outcome": "Chat idle auto-research / 24h persona mesh",
        "pass_evidence": "explicitly rejected in walls",
        "non_scope": "multiagent≠persona-mesh",
        "status": "HOLD",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing: {path}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"not object: {path}")
    return doc


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_allowlist(path: Path | None = None) -> dict[str, Any]:
    p = path or ALLOWLIST
    doc = _load_json(p)
    if str(doc.get("schema") or "") != SCHEMA_ALLOW:
        raise ValueError(f"invalid allowlist schema: {doc.get('schema')}")
    return doc


def _action_map(allow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in allow.get("allowed_actions") or []:
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = row
    return out


def _forbidden(allow: dict[str, Any]) -> set[str]:
    raw = allow.get("forbidden_action_ids") or []
    return {str(x) for x in raw if x}


def _empty_stamps() -> dict[str, Any]:
    return {
        "schema": SCHEMA_STAMPS,
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "stamps": [],
    }


def load_stamps() -> dict[str, Any]:
    if not STAMPS.is_file():
        return _empty_stamps()
    doc = _load_json(STAMPS)
    if str(doc.get("schema") or "") != SCHEMA_STAMPS:
        raise ValueError(f"invalid stamps schema: {doc.get('schema')}")
    if not isinstance(doc.get("stamps"), list):
        doc["stamps"] = []
    return doc


def _active_yes(stamps: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Latest YES stamp per id wins; NO/revoked removes."""
    latest: dict[str, dict[str, Any]] = {}
    for row in stamps.get("stamps") or []:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("id") or "").strip()
        if not aid:
            continue
        decision = str(row.get("decision") or "").upper()
        if decision == "YES":
            latest[aid] = row
        elif decision in ("NO", "REVOKE"):
            latest.pop(aid, None)
    return latest


def cmd_list(allow: dict[str, Any], stamps: dict[str, Any]) -> int:
    yes = _active_yes(stamps)
    rows = []
    for aid, action in _action_map(allow).items():
        rows.append(
            {
                "id": aid,
                "label": action.get("label"),
                "approved": aid in yes,
                "argv": action.get("argv"),
            }
        )
    out = {
        "ok": True,
        "schema": "mkm_hitl_ops_latch_list_v1",
        "allowed_count": len(rows),
        "approved_count": sum(1 for r in rows if r["approved"]),
        "actions": rows,
        "forbidden_action_ids": sorted(_forbidden(allow)),
        "default_mode": allow.get("default_mode", "dry_run"),
        "l_hold": allow.get("l_hold"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_approve(
    allow: dict[str, Any],
    *,
    action_id: str,
    by: str,
    note: str,
    decision: str,
) -> int:
    aid = action_id.strip()
    forbidden = _forbidden(allow)
    actions = _action_map(allow)
    if aid in forbidden:
        print(json.dumps({"ok": False, "error": f"forbidden_action_id: {aid}"}, ensure_ascii=False))
        return 2
    if decision == "YES" and aid not in actions:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"id not on allowlist: {aid}",
                    "allowed": sorted(actions.keys()),
                },
                ensure_ascii=False,
            )
        )
        return 2

    stamps = load_stamps()
    entry = {
        "id": aid,
        "decision": decision,
        "approved_by": by,
        "note": note,
        "at_utc": _utc(),
        "allowlist_schema": SCHEMA_ALLOW,
    }
    stamps["stamps"].append(entry)
    stamps["generated_at_utc"] = _utc()
    stamps["research_only"] = True
    stamps["send_gate"] = "HOLD"
    _write_json(STAMPS, stamps)
    print(
        json.dumps(
            {
                "ok": True,
                "id": aid,
                "decision": decision,
                "stamps_path": str(STAMPS.as_posix()),
                "note_ko": "승인 스탬프만 기록 · apply는 별도 --apply",
            },
            ensure_ascii=False,
        )
    )
    return 0


def _run_action(action: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    argv = [str(x) for x in (action.get("argv") or [])]
    cwd = ROOT / str(action.get("cwd") or ".")
    row: dict[str, Any] = {
        "id": action.get("id"),
        "label": action.get("label"),
        "argv": argv,
        "mode": "apply" if apply else "dry_run",
    }
    if not apply:
        row["ran"] = False
        row["exit_code"] = None
        row["stdout_tail"] = "(dry-run · not executed)"
        return row

    try:
        cp = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=600,
            shell=False,
        )
        combined = (cp.stdout or "") + (cp.stderr or "")
        row["ran"] = True
        row["exit_code"] = int(cp.returncode)
        row["stdout_tail"] = combined[-2000:] if combined else ""
        row["ok"] = cp.returncode == 0
    except Exception as exc:  # noqa: BLE001 — receipt must capture
        row["ran"] = True
        row["exit_code"] = 1
        row["ok"] = False
        row["error"] = str(exc)
    return row


def cmd_apply(
    allow: dict[str, Any],
    *,
    apply: bool,
    only_id: str | None,
    phase1_stamp: dict[str, Any] | None = None,
) -> int:
    stamps = load_stamps()
    yes = _active_yes(stamps)
    actions = _action_map(allow)
    forbidden = _forbidden(allow)

    selected_ids: list[str]
    if only_id:
        selected_ids = [only_id.strip()]
    else:
        selected_ids = sorted(yes.keys())

    results: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for aid in selected_ids:
        if aid in forbidden:
            blocked.append({"id": aid, "reason": "forbidden_action_id"})
            continue
        if aid not in actions:
            blocked.append({"id": aid, "reason": "not_on_allowlist"})
            continue
        if aid not in yes:
            blocked.append({"id": aid, "reason": "no_YES_stamp"})
            continue
        results.append(_run_action(actions[aid], apply=apply))

    mode = "apply" if apply else "dry_run"
    all_ok = all(r.get("ok", True) for r in results if r.get("ran")) and not (
        apply and any(r.get("exit_code") not in (0, None) for r in results)
    )
    # dry-run: ok if planning succeeded (no blocks required)
    if not apply:
        all_ok = True

    if apply and results:
        all_ok = all(bool(r.get("ok")) for r in results)

    receipt: dict[str, Any] = {
        "schema": SCHEMA_RECEIPT,
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a": "FROZEN",
        "mode": mode,
        "ok": all_ok and (bool(results) or not only_id),
        "selected_ids": selected_ids,
        "results": results,
        "blocked": blocked,
        "allowlist_path": str(ALLOWLIST.as_posix()),
        "stamps_path": str(STAMPS.as_posix()),
        "walls_ko": allow.get("walls_ko") or [],
        "l_hold": allow.get("l_hold"),
        "done_cards": DONE_CARDS,
        "phase1_s_verify": phase1_stamp,
        "non_scope": [
            "chat_24h_persona",
            "idle_auto_research",
            "SEND_OPEN",
            "Track_A",
            "live_trade",
            "GitHub_push",
            "Temporal",
            "Cursor_Automations",
            "unattended_coding_DONE",
        ],
        "reproduce": [
            "py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py list",
            "py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py --approve rebuild_morning_brief",
            "py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py",
            "py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py --apply --id rebuild_morning_brief",
        ],
    }
    if only_id and not results:
        receipt["ok"] = False

    _write_json(RECEIPT, receipt)
    _write_elementary(receipt, allow, stamps)
    print(
        json.dumps(
            {
                "ok": receipt["ok"],
                "mode": mode,
                "ran": len([r for r in results if r.get("ran")]),
                "planned": len(results),
                "blocked": len(blocked),
                "receipt": str(RECEIPT.as_posix()),
                "paste": str(PASTE.as_posix()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if receipt["ok"] else 1


def _write_elementary(
    receipt: dict[str, Any],
    allow: dict[str, Any],
    stamps: dict[str, Any],
) -> None:
    yes = _active_yes(stamps)
    lines = [
        "=== MKM HITL S→M latch elementary v1 ===",
        f"generated_at_utc: {receipt.get('generated_at_utc')}",
        "posture: research_only · SEND HOLD · Track A FROZEN · Fact-Lock",
        "",
        "## What was structured (S→M→L)",
        "1) S verify — morning brief + inbox status + AutonomousPatrol membership (exit 0 required)",
        "2) M latch — allowlist + --approve stamp + dry-run/--apply runner (THIS unlock)",
        "3) L HOLD — Cursor Automations / Temporal = document only · NOT built",
        "",
        "## Phase 1 S verify (stamp)",
    ]
    p1 = receipt.get("phase1_s_verify") or {}
    if p1:
        for k, v in p1.items():
            if isinstance(v, dict) and ("command" in v or "exit" in v):
                cmd = v.get("command") or ""
                ex = v.get("exit")
                note = v.get("note") or ""
                extra = f" · {note}" if note else ""
                lines.append(f"- {k}: exit={ex} · `{cmd}`{extra}")
            elif isinstance(v, dict):
                lines.append(f"- {k}: {json.dumps(v, ensure_ascii=False)}")
            else:
                lines.append(f"- {k}: {v}")
    else:
        lines.append("- (run Phase1 commands separately; optional stamp via --stamp-phase1-json)")
    lines.extend(
        [
            "",
            "## Allowlist (safe only)",
        ]
    )
    for aid, action in _action_map(allow).items():
        mark = "YES" if aid in yes else "—"
        lines.append(f"- [{mark}] `{aid}` — {action.get('label')}")
    lines.extend(
        [
            "",
            "## Forbidden (never apply via latch)",
            "- " + ", ".join(sorted(_forbidden(allow))),
            "",
            "## Commander recipe (3 lines)",
            "1) 아침: `py scripts/build_mkm_ops_queue_morning_brief_v1.py` → YES/NO 스캐폴드 확인",
            "2) 승인: `py scripts/run_mkm_hitl_ops_approve_apply_latch_v1.py --approve rebuild_morning_brief`",
            "3) 적용: 먼저 dry-run(기본) → OK면 `... --apply --id rebuild_morning_brief`",
            "",
            f"## Last receipt mode={receipt.get('mode')} ok={receipt.get('ok')}",
        ]
    )
    for r in receipt.get("results") or []:
        lines.append(
            f"- {r.get('id')}: mode={r.get('mode')} ran={r.get('ran')} exit={r.get('exit_code')}"
        )
    for b in receipt.get("blocked") or []:
        lines.append(f"- BLOCKED {b.get('id')}: {b.get('reason')}")
    lines.extend(
        [
            "",
            "## What still will NOT happen",
            "- Chat idle auto-research / 24h persona mesh",
            "- SEND OPEN · Track A auto · live trade · GitHub push",
            "- Morning brief auto-apply (scaffold ≠ latch)",
            "- L Temporal / Cursor Automations install",
            "- 「무인 자율연구 DONE」 soft claim (harness≠product)",
            "",
            "## Soft-claim gate (must FAIL soft DONE)",
            "- claim: 「무인 자율연구 DONE…」 → adversarial BLOCKED expected · mkm_claim_adversarial_reread_v1_latest.json",
            "- Honest latch unlock ≠ unattended coding commercial DONE",
            "",
            "## Done cards",
        ]
    )
    for c in DONE_CARDS:
        lines.append(f"- {c['id']} [{c['status']}] {c['user_visible_outcome']}")
    lines.extend(
        [
            "",
            "## Artifact paths",
            f"- allowlist: {ALLOWLIST.as_posix()}",
            f"- stamps: {STAMPS.as_posix()}",
            f"- receipt: {RECEIPT.as_posix()}",
            f"- paste: {PASTE.as_posix()}",
            f"- phase1 stamp: {(ROOT / 'docs/final/artifacts/mkm_hitl_phase1_s_verify_stamp_v1_latest.json').as_posix()}",
            f"- scheduler map: docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json",
            f"- morning brief: docs/final/artifacts/mkm_ops_queue_morning_brief_v1_latest.json",
            "",
            "## L HOLD (Phase 3)",
            json.dumps(allow.get("l_hold") or {}, ensure_ascii=False),
            "",
            "=== end ===",
            "",
        ]
    )
    PASTE.parent.mkdir(parents=True, exist_ok=True)
    PASTE.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", nargs="?", default="apply_plan", help="list | apply_plan (default)")
    ap.add_argument("--approve", metavar="ID", help="Write YES stamp for allowlisted id")
    ap.add_argument("--revoke", metavar="ID", help="Write REVOKE stamp for id")
    ap.add_argument("--by", default="commander", help="Approver label")
    ap.add_argument("--note", default="", help="Optional note")
    ap.add_argument("--apply", action="store_true", help="Actually run allowlisted+stamped commands")
    ap.add_argument("--id", dest="only_id", default=None, help="Limit apply/dry-run to one id")
    ap.add_argument(
        "--stamp-phase1-json",
        type=Path,
        default=None,
        help="Optional JSON object to embed as phase1_s_verify in receipt",
    )
    args = ap.parse_args(argv)

    try:
        allow = load_allowlist()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    if args.approve:
        return cmd_approve(allow, action_id=args.approve, by=args.by, note=args.note, decision="YES")
    if args.revoke:
        return cmd_approve(allow, action_id=args.revoke, by=args.by, note=args.note, decision="REVOKE")

    if args.command == "list":
        return cmd_list(allow, load_stamps())

    phase1: dict[str, Any] | None = None
    if args.stamp_phase1_json and args.stamp_phase1_json.is_file():
        phase1 = _load_json(args.stamp_phase1_json)

    return cmd_apply(allow, apply=bool(args.apply), only_id=args.only_id, phase1_stamp=phase1)


if __name__ == "__main__":
    raise SystemExit(main())
