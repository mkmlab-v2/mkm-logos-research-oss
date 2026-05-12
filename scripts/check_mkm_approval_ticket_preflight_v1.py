#!/usr/bin/env python3
"""Preflight gate: human approval ticket must authorize execution tag and time window."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_TICKET = ART / "mkm_approval_ticket_v1_latest.json"
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "schemas" / "mkm_approval_ticket_v1.schema.json"
DEFAULT_OUT = ART / "mkm_approval_ticket_preflight_latest.json"
DEFAULT_RUN_COUNTS = ROOT / "reports" / "mkm_approval_ticket_run_counts_v1.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _parse_dt(raw: str) -> datetime | None:
    s = (raw or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _validate_jsonschema(doc: dict[str, Any], schema_path: Path) -> list[str]:
    if not schema_path.is_file():
        return [f"missing_schema_file:{schema_path}"]
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        return []
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid_schema_json:{exc}"]
    errs: list[str] = []
    for e in Draft7Validator(schema).iter_errors(doc):
        errs.append(f"{list(e.path)}: {e.message}")
    return errs[:20]


def _scope_allowed(allow: list[str], tag: str) -> bool:
    if "*" in allow:
        return True
    return tag in allow


def _scope_denied(deny: list[str], tag: str) -> bool:
    tl = tag.lower()
    for d in deny:
        ds = str(d).strip().lower()
        if not ds:
            continue
        if ds == tl:
            return True
        if len(ds) >= 6 and ds in tl:
            return True
    return False


def _today_run_count(state_path: Path, ticket_id: str) -> int:
    day = _utc_now().strftime("%Y-%m-%d")
    data = _read_json(state_path)
    counts = data.get("counts") if isinstance(data.get("counts"), dict) else {}
    key = f"{ticket_id}|{day}"
    return int(counts.get(key, 0))


def _increment_run_count(state_path: Path, ticket_id: str) -> int:
    day = _utc_now().strftime("%Y-%m-%d")
    data = _read_json(state_path)
    if not isinstance(data.get("counts"), dict):
        data = {"schema": "mkm_approval_ticket_run_counts_v1", "counts": {}}
    counts = data["counts"]
    key = f"{ticket_id}|{day}"
    n = int(counts.get(key, 0)) + 1
    counts[key] = n
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return n


def _append_audit(
    repo: Path,
    *,
    execution_tag: str,
    decision: str,
    reasons: list[str],
    ticket_id: str | None,
    out_path: Path,
    skip: bool,
) -> None:
    if skip:
        return
    audit_py = repo / "scripts" / "mkm_append_governance_audit_log_v1.py"
    if not audit_py.is_file():
        return
    dec = "approval_ticket_preflight_v1_go" if decision == "GO" else "approval_ticket_preflight_v1_no_go"
    note_obj = {"execution_tag": execution_tag, "ticket_id": ticket_id, "reasons": reasons[:12]}
    note = json.dumps(note_obj, ensure_ascii=False)[:3800]
    risk = "low" if decision == "GO" else "elevated"
    cmd = [
        sys.executable,
        str(audit_py),
        "--mission-id",
        "mkm_approval_ticket_v1",
        "--stage",
        "preflight",
        "--decision",
        dec,
        "--evidence-path",
        str(out_path).replace("\\", "/"),
        "--actor",
        "check_mkm_approval_ticket_preflight_v1.py",
        "--note",
        note,
        "--risk-level",
        risk,
    ]
    subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticket-json", type=Path, default=DEFAULT_TICKET)
    ap.add_argument("--schema-json", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--execution-tag",
        type=str,
        required=True,
        help="Runner-declared scope tag (must match scope_allow).",
    )
    ap.add_argument("--runs-state-json", type=Path, default=DEFAULT_RUN_COUNTS)
    ap.add_argument(
        "--skip-audit-log",
        action="store_true",
        help="Do not append to reports/agent_decisions_log.jsonl (tests / CI).",
    )
    args = ap.parse_args()

    ticket = _read_json(args.ticket_json)
    tag = str(args.execution_tag).strip()
    reasons: list[str] = []

    if not ticket:
        reasons.append("missing_or_empty_ticket_json")
    if not tag:
        reasons.append("missing_execution_tag")

    if ticket:
        reasons.extend(_validate_jsonschema(ticket, args.schema_json))

    if ticket and ticket.get("schema") != "mkm_approval_ticket_v1":
        reasons.append("schema_field_mismatch")

    if ticket and ticket.get("approved") is not True:
        reasons.append("not_approved")

    vf = _parse_dt(str(ticket.get("valid_from_utc") or ""))
    vu = _parse_dt(str(ticket.get("valid_until_utc") or ""))
    now = _utc_now()
    if ticket:
        if not vf:
            reasons.append("invalid_valid_from_utc")
        if not vu:
            reasons.append("invalid_valid_until_utc")
    if vf and now < vf:
        reasons.append("before_valid_window")
    if vu and now > vu:
        reasons.append("after_valid_window")

    allow = [str(x) for x in (ticket.get("scope_allow") or []) if str(x).strip()]
    deny = [str(x) for x in (ticket.get("scope_deny") or []) if str(x).strip()]
    if ticket and allow and not _scope_allowed(allow, tag):
        reasons.append("execution_tag_not_in_scope_allow")
    if ticket and deny and _scope_denied(deny, tag):
        reasons.append("execution_tag_blocked_by_scope_deny")

    caps = dict(ticket.get("execution_caps") or {})
    max_runs = int(caps.get("max_runs_per_day") or 0)
    tid = str(ticket.get("ticket_id") or "").strip()
    if ticket and max_runs > 0 and tid:
        today_count = _today_run_count(args.runs_state_json, tid)
        if today_count >= max_runs:
            reasons.append("max_runs_per_day_exceeded")

    seen: set[str] = set()
    uniq: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    reasons = uniq

    decision = "GO" if not reasons else "NO_GO"
    valid_ok = bool(
        vf
        and vu
        and vf <= now <= vu
        and "before_valid_window" not in reasons
        and "after_valid_window" not in reasons
    )

    out: dict[str, Any] = {
        "schema": "mkm_approval_ticket_preflight_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "ticket_json": str(args.ticket_json).replace("\\", "/"),
            "execution_tag": tag,
        },
        "decision": decision,
        "reasons": reasons,
        "ticket_id": ticket.get("ticket_id"),
        "valid_window_ok": valid_ok,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": decision == "GO", "decision": decision, "out": str(args.out.resolve())}, ensure_ascii=False))

    _append_audit(
        ROOT,
        execution_tag=tag,
        decision=decision,
        reasons=reasons,
        ticket_id=str(ticket.get("ticket_id") or "") or None,
        out_path=args.out,
        skip=bool(args.skip_audit_log),
    )

    if decision != "GO":
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
