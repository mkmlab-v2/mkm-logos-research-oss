#!/usr/bin/env python3
"""Append-only JSONL stub for BigSet Tier-0 atypical signals → human review queue (v0).

No auto-resolution, no Track A trigger, no clinical analog execution.
``enqueue-from-signals`` reads ``bigset_tier0_atypical_signal_v1`` artifact;
``drain`` validates pending rows still exist in the signal artifact and may ack.

Reproducible:
  py scripts/bigset_tier0_atypical_human_review_queue_stub_v1.py enqueue-from-signals \\
    --signals-json docs/final/artifacts/bigset_tier0_atypical_signal_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]

QUEUE_ENTRY_SCHEMA = "bigset_tier0_atypical_human_review_queue_entry_v0"
QUEUE_ENTRY_SCHEMA_VERSION = "0.1.0"
ACK_EVENT_SCHEMA = "bigset_tier0_atypical_human_review_ack_v0"
ACK_EVENT_SCHEMA_VERSION = "0.1.0"
EXPORT_PENDING_SCHEMA = "bigset_tier0_atypical_human_review_pending_export_v0"
EXPORT_PENDING_SCHEMA_VERSION = "0.1.0"
SIGNAL_SCHEMA = "bigset_tier0_atypical_signal_v1"

DEFAULT_QUEUE = ROOT / "reports/bigset_tier0_atypical_human_review_queue_v1.jsonl"
DEFAULT_ACK = ROOT / "reports/bigset_tier0_atypical_human_review_ack_v1.jsonl"
DEFAULT_EXPORT = ROOT / "docs/final/artifacts/bigset_tier0_atypical_human_review_pending_v1_latest.json"


def utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def posix_under_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


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


def append_queue_line(queue_path: Path, entry: Mapping[str, Any]) -> None:
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(entry), ensure_ascii=False) + "\n")


def append_ack_line(ack_path: Path, entry: Mapping[str, Any]) -> None:
    ack_path.parent.mkdir(parents=True, exist_ok=True)
    with ack_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(entry), ensure_ascii=False) + "\n")


def review_id_for_signal(signal: Mapping[str, Any], index: int) -> str:
    gid = str(signal.get("conflict_group_id") or "ungrouped").strip()
    st = str(signal.get("signal_type") or "unknown").strip()
    row_idx = signal.get("row_index", index)
    return f"bigset_atyp_{gid}_{st}_{row_idx}"


def build_queue_entry_v0(
    *,
    review_id: str,
    signal: Mapping[str, Any],
    queued_at_utc: str,
    signals_json_path: Path,
    source_csv_path: Path | None,
    root: Path,
) -> dict[str, Any]:
    return {
        "schema": QUEUE_ENTRY_SCHEMA,
        "schema_version": QUEUE_ENTRY_SCHEMA_VERSION,
        "review_id": review_id,
        "status": "pending_human_review",
        "queued_at_utc": queued_at_utc,
        "signal": dict(signal),
        "signals_json_path": posix_under_root(signals_json_path, root),
        "source_csv_path": posix_under_root(source_csv_path, root) if source_csv_path else None,
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "human_action_required": True,
        "note_ko": "관측 신호 — 임상·Track A·SEND 트리거 아님",
    }


def load_acked_review_ids(ack_path: Path) -> set[str]:
    ids: set[str] = set()
    for obj in read_jsonl_objects(ack_path):
        if str(obj.get("event", "")).strip() != "drain_ack":
            continue
        rid = str(obj.get("review_id", "")).strip()
        if rid:
            ids.add(rid)
    return ids


def load_queued_review_ids(queue_path: Path) -> set[str]:
    ids: set[str] = set()
    for obj in read_jsonl_objects(queue_path):
        if str(obj.get("schema", "")).strip() != QUEUE_ENTRY_SCHEMA:
            continue
        rid = str(obj.get("review_id", "")).strip()
        if rid:
            ids.add(rid)
    return ids


def signal_fingerprint(signal: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(signal.get("signal_type") or ""),
        str(signal.get("conflict_group_id") or ""),
        signal.get("row_index"),
        str(signal.get("verse_ref") or ""),
    )


def signals_index(doc: Mapping[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    out: dict[tuple[Any, ...], dict[str, Any]] = {}
    for sig in doc.get("signals") or []:
        if isinstance(sig, dict):
            out[signal_fingerprint(sig)] = sig
    return out


def cmd_enqueue_from_signals(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    signals_path = Path(args.signals_json)
    if not signals_path.is_absolute():
        signals_path = (root / signals_path).resolve()
    if not signals_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing signals json: {signals_path}"}), file=sys.stderr)
        return 2

    doc = json.loads(signals_path.read_text(encoding="utf-8"))
    if str(doc.get("schema") or "") != SIGNAL_SCHEMA:
        print(json.dumps({"ok": False, "error": f"unexpected schema: {doc.get('schema')}"}), file=sys.stderr)
        return 2

    qp = Path(args.queue_path)
    if not qp.is_absolute():
        qp = (root / qp).resolve()

    csv_path: Path | None = None
    if args.source_csv:
        csv_path = Path(args.source_csv)
        if not csv_path.is_absolute():
            csv_path = (root / csv_path).resolve()

    already = load_queued_review_ids(qp)
    queued_at = utc_now_z()
    appended = 0
    signals = [s for s in (doc.get("signals") or []) if isinstance(s, dict)]

    if int(args.min_signals) > 0 and len(signals) < int(args.min_signals):
        print(
            json.dumps(
                {
                    "ok": True,
                    "skipped": True,
                    "reason": "below_min_signals",
                    "signal_count": len(signals),
                },
                ensure_ascii=False,
            )
        )
        return 0

    for i, sig in enumerate(signals):
        rid = review_id_for_signal(sig, i)
        if rid in already:
            continue
        ent = build_queue_entry_v0(
            review_id=rid,
            signal=sig,
            queued_at_utc=queued_at,
            signals_json_path=signals_path,
            source_csv_path=csv_path,
            root=root,
        )
        append_queue_line(qp, ent)
        already.add(rid)
        appended += 1

    print(
        json.dumps(
            {
                "ok": True,
                "appended": appended,
                "signal_count": len(signals),
                "queue_path": str(qp),
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_export_pending(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    qp = Path(args.queue_path)
    if not qp.is_absolute():
        qp = (root / qp).resolve()
    ap = Path(args.ack_path)
    if not ap.is_absolute():
        ap = (root / ap).resolve()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (root / out_path).resolve()

    acked = load_acked_review_ids(ap)
    pending: list[dict[str, Any]] = []
    for obj in read_jsonl_objects(qp):
        if str(obj.get("schema", "")).strip() != QUEUE_ENTRY_SCHEMA:
            continue
        rid = str(obj.get("review_id", "")).strip()
        if not rid or rid in acked:
            continue
        if str(obj.get("status", "")).strip() != "pending_human_review":
            continue
        pending.append(obj)

    export_doc = {
        "schema": EXPORT_PENDING_SCHEMA,
        "schema_version": EXPORT_PENDING_SCHEMA_VERSION,
        "generated_at_utc": utc_now_z(),
        "research_only": True,
        "send_gate": "HOLD",
        "pending_count": len(pending),
        "pending": pending,
        "queue_path": posix_under_root(qp, root),
        "repro_command": (
            "py scripts/bigset_tier0_atypical_human_review_queue_stub_v1.py export-pending"
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(export_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "pending_count": len(pending), "out": str(out_path)}, ensure_ascii=False))
    return 0


def cmd_drain(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    qp = Path(args.queue_path)
    if not qp.is_absolute():
        qp = (root / qp).resolve()
    if not qp.is_file():
        if args.allow_missing_queue:
            print(json.dumps({"ok": True, "skipped": True, "reason": "missing_queue"}, ensure_ascii=False))
            return 0
        print(json.dumps({"ok": False, "error": f"missing queue: {qp}"}), file=sys.stderr)
        return 2

    ap = Path(args.ack_path)
    if not ap.is_absolute():
        ap = (root / ap).resolve()

    signals_path = Path(args.signals_json)
    if not signals_path.is_absolute():
        signals_path = (root / signals_path).resolve()
    sig_index: dict[tuple[Any, ...], dict[str, Any]] = {}
    if signals_path.is_file():
        doc = json.loads(signals_path.read_text(encoding="utf-8"))
        sig_index = signals_index(doc)

    acked = load_acked_review_ids(ap)
    worst = 0
    acted = 0
    max_jobs = max(1, int(args.max_jobs))

    for obj in read_jsonl_objects(qp):
        if acted >= max_jobs:
            break
        if str(obj.get("schema", "")).strip() != QUEUE_ENTRY_SCHEMA:
            continue
        rid = str(obj.get("review_id", "")).strip()
        if not rid or rid in acked:
            continue
        if str(obj.get("status", "")).strip() != "pending_human_review":
            continue

        sig = obj.get("signal") if isinstance(obj.get("signal"), dict) else {}
        still_present = signal_fingerprint(sig) in sig_index
        ok = still_present
        detail = "signal_still_present" if still_present else "signal_missing_from_artifact"
        if not still_present:
            worst = 1

        print(f"drain review_id={rid} ok={ok} detail={detail}")
        if args.write_ack:
            append_ack_line(
                ap,
                {
                    "schema": ACK_EVENT_SCHEMA,
                    "schema_version": ACK_EVENT_SCHEMA_VERSION,
                    "event": "drain_ack",
                    "review_id": rid,
                    "processed_at_utc": utc_now_z(),
                    "ok": ok,
                    "detail": detail,
                    "commander_note": str(args.commander_note or "").strip() or None,
                },
            )
        acted += 1
        acked.add(rid)

    if acted == 0:
        print("drain: no pending rows")
    return worst


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_enq = sub.add_parser("enqueue-from-signals")
    p_enq.add_argument("--signals-json", type=Path, required=True)
    p_enq.add_argument("--source-csv", type=Path, default=None)
    p_enq.add_argument("--queue-path", type=Path, default=DEFAULT_QUEUE)
    p_enq.add_argument("--min-signals", type=int, default=0)
    p_enq.set_defaults(func=cmd_enqueue_from_signals)

    p_exp = sub.add_parser("export-pending")
    p_exp.add_argument("--queue-path", type=Path, default=DEFAULT_QUEUE)
    p_exp.add_argument("--ack-path", type=Path, default=DEFAULT_ACK)
    p_exp.add_argument("--out", type=Path, default=DEFAULT_EXPORT)
    p_exp.set_defaults(func=cmd_export_pending)

    p_drain = sub.add_parser("drain")
    p_drain.add_argument("--queue-path", type=Path, default=DEFAULT_QUEUE)
    p_drain.add_argument("--ack-path", type=Path, default=DEFAULT_ACK)
    p_drain.add_argument("--signals-json", type=Path, default=ROOT / "docs/final/artifacts/bigset_tier0_atypical_signal_v1_latest.json")
    p_drain.add_argument("--max-jobs", type=int, default=50)
    p_drain.add_argument("--allow-missing-queue", action="store_true")
    p_drain.add_argument("--write-ack", action="store_true")
    p_drain.add_argument("--commander-note", default="")
    p_drain.set_defaults(func=cmd_drain)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
