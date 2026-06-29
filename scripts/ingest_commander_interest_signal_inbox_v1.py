#!/usr/bin/env python3
"""Drain pending commander interest inbox items into the signal JSONL log."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from commander_interest_benchmark_v1_lib import (  # noqa: E402
    DEFAULT_LOG,
    ensure_signal_log,
    parse_ts,
    resolve_path,
    utc_now,
)

DEFAULT_INBOX = ROOT / "data" / "marketing" / "commander_interest_signal_inbox.json"
EXAMPLE_INBOX = ROOT / "data" / "marketing" / "commander_interest_signal_inbox_v1.example.json"
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "commander_interest_signal_inbox_ingest_latest.json"


def _utc_now() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_observed_at(raw: str) -> str:
    observed = raw.strip() or _utc_now()
    ts = parse_ts(observed)
    now = utc_now()
    if ts is not None and ts > now:
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return observed


def _resolve_inbox(path: Path, *, bootstrap_example: bool) -> Path:
    resolved = resolve_path(path)
    if resolved.is_file():
        return resolved
    if bootstrap_example and EXAMPLE_INBOX.is_file():
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(EXAMPLE_INBOX.read_text(encoding="utf-8-sig"), encoding="utf-8")
        return resolved
    raise FileNotFoundError(f"Missing inbox: {resolved}")


def _item_to_signal(row: dict[str, Any]) -> dict[str, Any]:
    observed = _normalize_observed_at(str(row.get("observed_at_utc") or ""))
    out: dict[str, Any] = {
        "schema": "commander_interest_signal_v1",
        "observed_at_utc": observed,
        "topic_id": str(row.get("topic_id") or "").strip(),
        "platform": str(row.get("platform") or "").strip(),
        "title": str(row.get("title") or "").strip(),
        "url": str(row.get("url") or "").strip(),
        "views": float(row.get("views") or 0),
        "likes": float(row.get("likes") or 0),
        "comments": float(row.get("comments") or 0),
        "shares": float(row.get("shares") or 0),
    }
    if row.get("engagement_score") is not None:
        out["engagement_score"] = float(row["engagement_score"])
    note_parts = []
    if row.get("note"):
        note_parts.append(str(row["note"]))
    if row.get("source"):
        note_parts.append(f"source={row['source']}")
    if row.get("id"):
        note_parts.append(f"inbox_id={row['id']}")
    if note_parts:
        out["note"] = " · ".join(note_parts)
    return out


def ingest_inbox(
    *,
    inbox_path: Path,
    log_path: Path,
    bootstrap_example: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    inbox = _resolve_inbox(inbox_path, bootstrap_example=bootstrap_example)
    doc = json.loads(inbox.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "commander_interest_signal_inbox_v1":
        raise ValueError(f"Unexpected inbox schema: {doc.get('schema')}")

    pending = [item for item in (doc.get("items") or []) if item.get("status") == "pending"]
    ingested_ids: list[str] = []
    skipped = 0

    if pending and not dry_run:
        log_file = ensure_signal_log(log_path)
        with log_file.open("a", encoding="utf-8") as fh:
            for item in pending:
                signal = _item_to_signal(item)
                fh.write(json.dumps(signal, ensure_ascii=False) + "\n")
                item["status"] = "ingested"
                ingested_ids.append(str(item.get("id") or ""))
        doc["updated_at_utc"] = _utc_now()
        inbox.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif pending and dry_run:
        ingested_ids = [str(item.get("id") or "") for item in pending]

    for item in doc.get("items") or []:
        if item.get("status") == "skipped":
            skipped += 1

    return {
        "schema": "commander_interest_signal_inbox_ingest_v1",
        "generated_at_utc": _utc_now(),
        "dry_run": dry_run,
        "inbox_path": str(inbox.resolve()),
        "log_path": str(resolve_path(log_path).resolve()),
        "pending_found": len(pending),
        "ingested_count": len(ingested_ids),
        "ingested_ids": ingested_ids,
        "skipped_count": skipped,
        "track_wall": {
            "lane": "internal_observation_only",
            "human_publish_only": True,
            "send_gate": "HOLD",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inbox-json", type=Path, default=DEFAULT_INBOX)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--bootstrap-example", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    payload = ingest_inbox(
        inbox_path=args.inbox_json,
        log_path=args.log_jsonl,
        bootstrap_example=args.bootstrap_example,
        dry_run=args.dry_run,
    )
    out_json = resolve_path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(out_json), **payload}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
