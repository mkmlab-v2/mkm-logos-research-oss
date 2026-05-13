#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append-only JSONL stub for premium multilens async jobs (v0).

One line per enqueue; ``drain`` walks the queue, checks report JSON on disk,
and may append ack lines. ``export-pending`` writes a JSON snapshot of pending
rows plus **recommended lens script pointers** (paths only; no subprocess).

Still no Redis / no real async worker / no automatic lens execution.
Embedding RAG remains a separate backlog item (see CONSTITUTION Premium row).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

QUEUE_ENTRY_SCHEMA = "premium_multilens_job_queue_entry_v0"
QUEUE_ENTRY_SCHEMA_VERSION = "0.1.0"
ACK_EVENT_SCHEMA = "premium_multilens_job_queue_ack_v0"
ACK_EVENT_SCHEMA_VERSION = "0.1.0"
PREMIUM_REPORT_SCHEMA = "premium_btrack_multilens_report_v1"
EXPORT_PENDING_SCHEMA = "premium_multilens_queue_pending_export_v0"
EXPORT_PENDING_SCHEMA_VERSION = "0.1.0"

# Advisory pointers only (Fact-Lock: CONSTITUTION §1c / §3.3). This module never exec's these.
RECOMMENDED_LENS_ORCHESTRATION_POINTERS_V0: list[dict[str, Any]] = [
    {
        "lens_track": "myeongni",
        "script_workspace_posix": "scripts/run_myeongni_lens_chain_from_bot_v1.py",
        "offline_smoke_argv": ["--demo-smoke"],
        "constitution_pointer": "CONSTITUTION table row: 봇→융합→명리 렌즈 원클릭 체인 v1",
    },
    {
        "lens_track": "myeongni",
        "script_workspace_posix": "scripts/run_lens_myeongni.py",
        "offline_smoke_argv": ["--allow-fallback"],
        "constitution_pointer": "CONSTITUTION: 독립 렌즈 v0/v1 (run_lens_myeongni)",
    },
    {
        "lens_track": "sasang",
        "script_workspace_posix": "scripts/run_lens_sasang.py",
        "offline_smoke_argv": [],
        "constitution_pointer": "CONSTITUTION: 사상 독립 렌즈 v0",
    },
    {
        "lens_track": "logos",
        "script_workspace_posix": "scripts/run_lens_logos.py",
        "offline_smoke_argv": [],
        "constitution_pointer": "CONSTITUTION: 로고스 독립 렌즈 v0",
    },
]


def utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def posix_under_root(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
        return rel.as_posix()
    except ValueError:
        return path.resolve().as_posix()


def build_queue_entry_v0(
    *,
    job_id: str,
    queued_at_utc: str,
    status: str,
    report_json_path: Path,
    mode: str,
    root: Path,
) -> dict[str, Any]:
    return {
        "schema": QUEUE_ENTRY_SCHEMA,
        "schema_version": QUEUE_ENTRY_SCHEMA_VERSION,
        "job_id": str(job_id).strip(),
        "status": str(status).strip() or "queued",
        "queued_at_utc": str(queued_at_utc).strip(),
        "report_json_path": posix_under_root(report_json_path, root),
        "report_kind": "premium_btrack_multilens_report_v1",
        "package_mode": str(mode).strip(),
    }


def append_queue_line_v0(queue_path: Path, entry: Mapping[str, Any]) -> None:
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(entry)
    with queue_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def load_drain_acked_job_ids(ack_path: Path) -> set[str]:
    """Any prior ``drain_ack`` row (ok true or false) suppresses re-processing that job_id."""
    ids: set[str] = set()
    for obj in read_jsonl_objects(ack_path):
        if str(obj.get("event", "")).strip() != "drain_ack":
            continue
        jid = str(obj.get("job_id", "")).strip()
        if jid:
            ids.add(jid)
    return ids


def resolve_report_json_path(report_field: str, root: Path) -> Path:
    p = Path(str(report_field).strip())
    if p.is_absolute():
        return p.resolve()
    return (root / p).resolve()


def validate_premium_report_json(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing_file"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"json_decode:{exc}"
    if not isinstance(data, dict):
        return False, "not_object"
    if data.get("schema") != PREMIUM_REPORT_SCHEMA:
        return False, "wrong_or_missing_report_schema"
    return True, "ok"


def list_pending_queue_jobs(
    *,
    root: Path,
    queue_path: Path,
    ack_path: Path,
    max_items: int,
) -> list[tuple[dict[str, Any], str, Path, bool, str]]:
    """FIFO pending jobs: (queue_row, job_id, resolved_report_path, validation_ok, validation_detail)."""
    entries = read_jsonl_objects(queue_path)
    acked = load_drain_acked_job_ids(ack_path)
    cap = max(1, int(max_items))
    out: list[tuple[dict[str, Any], str, Path, bool, str]] = []
    for rec in entries:
        if len(out) >= cap:
            break
        if str(rec.get("schema", "")).strip() != QUEUE_ENTRY_SCHEMA:
            continue
        jid = str(rec.get("job_id", "")).strip()
        if not jid or jid in acked:
            continue
        if str(rec.get("status", "queued")).strip() != "queued":
            continue
        rel = str(rec.get("report_json_path", "")).strip()
        if not rel:
            continue
        rpath = resolve_report_json_path(rel, root)
        ok, detail = validate_premium_report_json(rpath)
        out.append((rec, jid, rpath, ok, detail))
    return out


def build_ack_entry_v0(
    *,
    job_id: str,
    processed_at_utc: str,
    report_json_path: Path,
    root: Path,
    ok: bool,
    detail: str,
) -> dict[str, Any]:
    return {
        "schema": ACK_EVENT_SCHEMA,
        "schema_version": ACK_EVENT_SCHEMA_VERSION,
        "job_id": str(job_id).strip(),
        "event": "drain_ack",
        "processed_at_utc": str(processed_at_utc).strip(),
        "report_json_path": posix_under_root(report_json_path, root),
        "ok": bool(ok),
        "detail": str(detail)[:2048],
    }


def append_ack_line_v0(ack_path: Path, entry: Mapping[str, Any]) -> None:
    ack_path.parent.mkdir(parents=True, exist_ok=True)
    with ack_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(entry), ensure_ascii=False) + "\n")


def cmd_enqueue(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    qp = Path(args.queue_path)
    if not qp.is_absolute():
        qp = (root / qp).resolve()
    rj = Path(args.report_json)
    if not rj.is_absolute():
        rj = (root / rj).resolve()
    if not rj.is_file():
        print(f"ERROR: report json not found: {rj}", file=sys.stderr)
        return 2
    ent = build_queue_entry_v0(
        job_id=args.job_id,
        queued_at_utc=args.queued_at,
        status=args.status,
        report_json_path=rj,
        mode=args.mode,
        root=root,
    )
    append_queue_line_v0(qp, ent)
    print(f"OK: appended queue entry job_id={ent['job_id']} -> {qp}")
    return 0


def cmd_drain(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    qp = Path(args.queue_path)
    if not qp.is_absolute():
        qp = (root / qp).resolve()
    if not qp.is_file():
        if bool(args.allow_missing_queue):
            print(f"SKIP: queue file not found (allow-missing-queue): {qp}")
            return 0
        print(f"ERROR: queue file not found: {qp}", file=sys.stderr)
        return 2

    ap = Path(args.ack_path)
    if not ap.is_absolute():
        ap = (root / ap).resolve()

    pending = list_pending_queue_jobs(root=root, queue_path=qp, ack_path=ap, max_items=max(1, int(args.max_jobs)))
    write_ack = bool(args.write_ack)

    worst = 0
    acted = 0
    for rec, jid, rpath, ok, detail in pending:
        if not ok:
            worst = 1
        rel = str(rec.get("report_json_path", "")).strip()
        print(f"drain job_id={jid} report={rel} ok={ok} detail={detail}")

        if write_ack:
            append_ack_line_v0(
                ap,
                build_ack_entry_v0(
                    job_id=jid,
                    processed_at_utc=utc_now_z(),
                    report_json_path=rpath,
                    root=root,
                    ok=ok,
                    detail=detail,
                ),
            )
        acted += 1

    if acted == 0:
        print("drain: no pending queue rows matched (schema/status/ack filter).")
    return worst


def cmd_export_pending(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    qp = Path(args.queue_path)
    if not qp.is_absolute():
        qp = (root / qp).resolve()
    ap = Path(args.ack_path)
    if not ap.is_absolute():
        ap = (root / ap).resolve()
    out_json = Path(args.out_json)
    if not out_json.is_absolute():
        out_json = (root / out_json).resolve()

    if not qp.is_file():
        if bool(args.allow_missing_queue):
            pending_rows: list[tuple[dict[str, Any], str, Path, bool, str]] = []
        else:
            print(f"ERROR: queue file not found: {qp}", file=sys.stderr)
            return 2
    else:
        pending_rows = list_pending_queue_jobs(
            root=root,
            queue_path=qp,
            ack_path=ap,
            max_items=max(1, int(args.max_items)),
        )

    items: list[dict[str, Any]] = []
    worst = 0
    for rec, jid, rpath, ok, detail in pending_rows:
        if not ok:
            worst = 1
        items.append(
            {
                "job_id": jid,
                "queued_at_utc": str(rec.get("queued_at_utc", "")).strip(),
                "status": str(rec.get("status", "")).strip(),
                "package_mode": str(rec.get("package_mode", "")).strip(),
                "report_json_path": str(rec.get("report_json_path", "")).strip(),
                "report_json_path_resolved": rpath.resolve().as_posix(),
                "validation_ok": ok,
                "validation_detail": detail,
            }
        )

    payload: dict[str, Any] = {
        "schema": EXPORT_PENDING_SCHEMA,
        "schema_version": EXPORT_PENDING_SCHEMA_VERSION,
        "generated_at_utc": utc_now_z(),
        "queue_path": posix_under_root(qp, root),
        "ack_path": posix_under_root(ap, root),
        "out_json": posix_under_root(out_json, root),
        "pending_items": items,
        "recommended_lens_orchestration_pointers": RECOMMENDED_LENS_ORCHESTRATION_POINTERS_V0,
        "execution_policy": {
            "default_autorun": False,
            "note": "Advisory export only; B-track; no Track A or live trading merge (CONSTITUTION + CENTRAL_AGENT_MEMORY).",
        },
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote export {posix_under_root(out_json, root)} pending={len(items)}")
    return worst


def main() -> int:
    p = argparse.ArgumentParser(description="Premium multilens async job queue stub v0 (append-only JSONL).")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("enqueue", help="Append one JSONL line.")
    e.add_argument("--root", default=".", help="Workspace root for relative path normalization.")
    e.add_argument(
        "--queue-path",
        default="reports/premium_multilens_job_queue_v0.jsonl",
        help="Queue JSONL (relative to --root unless absolute).",
    )
    e.add_argument("--job-id", required=True)
    e.add_argument("--queued-at", required=True)
    e.add_argument("--report-json", required=True)
    e.add_argument("--mode", default="stub")
    e.add_argument("--status", default="queued")
    e.set_defaults(func=cmd_enqueue)

    d = sub.add_parser(
        "drain",
        help="Scan queue FIFO for queued v0 entries; validate premium report JSON; optional ack JSONL.",
    )
    d.add_argument("--root", default=".", help="Workspace root for resolving report paths.")
    d.add_argument(
        "--queue-path",
        default="reports/premium_multilens_job_queue_v0.jsonl",
        help="Queue JSONL (relative to --root unless absolute).",
    )
    d.add_argument(
        "--ack-path",
        default="reports/premium_multilens_job_queue_ack_v0.jsonl",
        help="Ack append JSONL (relative to --root unless absolute).",
    )
    d.add_argument("--max-jobs", type=int, default=10, help="Max queue rows to consider this run (>=1).")
    d.add_argument(
        "--write-ack",
        action="store_true",
        help="Append drain_ack lines to --ack-path (default is dry-run: print only).",
    )
    d.add_argument(
        "--allow-missing-queue",
        action="store_true",
        help="If queue file is absent, print SKIP and exit 0 (recommended for daily health).",
    )
    d.set_defaults(func=cmd_drain)

    x = sub.add_parser(
        "export-pending",
        help="Write JSON snapshot of pending queue rows + advisory lens script pointers (no subprocess).",
    )
    x.add_argument("--root", default=".", help="Workspace root for resolving paths.")
    x.add_argument(
        "--queue-path",
        default="reports/premium_multilens_job_queue_v0.jsonl",
        help="Queue JSONL (relative to --root unless absolute).",
    )
    x.add_argument(
        "--ack-path",
        default="reports/premium_multilens_job_queue_ack_v0.jsonl",
        help="Ack JSONL (relative to --root unless absolute).",
    )
    x.add_argument(
        "--out-json",
        required=True,
        help="Output JSON path (relative to --root unless absolute).",
    )
    x.add_argument("--max-items", type=int, default=50, help="Max pending rows to include (>=1).")
    x.add_argument(
        "--allow-missing-queue",
        action="store_true",
        help="If queue file is absent, write empty pending_items and exit 0.",
    )
    x.set_defaults(func=cmd_export_pending)

    ns = p.parse_args()
    return int(ns.func(ns))


if __name__ == "__main__":
    raise SystemExit(main())
