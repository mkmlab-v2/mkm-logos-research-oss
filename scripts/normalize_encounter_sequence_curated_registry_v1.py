#!/usr/bin/env python3
"""Normalize encounter_sequence curated registry: latest status per sequence_id [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/clinic/encounter_sequence_curated_learning_registry_v1.jsonl"
OUT = ROOT / "reports/encounter_sequence_curated_registry_normalize_v1_latest.json"

_STATUS_RANK = {
    "human_reviewed": 4,
    "ingested_to_curated": 3,
    "reviewed": 2,
    "pending_human_review": 1,
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_rows() -> list[dict[str, Any]]:
    if not REGISTRY.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _pick_best(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def _key(row: dict[str, Any]) -> tuple[int, str]:
        status = str(row.get("curated_path_status") or "")
        return (_STATUS_RANK.get(status, 0), str(row.get("recorded_at_utc") or ""))

    return max(rows, key=_key)


def normalize(*, dry_run: bool = False) -> dict[str, Any]:
    rows = _load_rows()
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        seq = str(row.get("sequence_id") or "")
        if not seq:
            continue
        by_id.setdefault(seq, []).append(row)

    deduped = [_pick_best(group) for group in by_id.values()]
    deduped.sort(key=lambda r: str(r.get("sequence_id") or ""))

    before_pending = sum(1 for r in rows if r.get("curated_path_status") == "pending_human_review")
    after_pending = sum(1 for r in deduped if r.get("curated_path_status") == "pending_human_review")
    after_reviewed = sum(
        1
        for r in deduped
        if str(r.get("curated_path_status") or "")
        in ("ingested_to_curated", "reviewed", "human_reviewed")
    )

    backup_path: str | None = None
    if not dry_run and rows:
        backup = REGISTRY.with_suffix(f".jsonl.bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
        shutil.copyfile(REGISTRY, backup)
        backup_path = str(backup).replace("\\", "/")
        REGISTRY.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in deduped),
            encoding="utf-8",
        )

    return {
        "schema": "encounter_sequence_curated_registry_normalize_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "dry_run": dry_run,
        "normalize_ok": len(deduped) <= len(rows),
        "rows_before": len(rows),
        "rows_after": len(deduped),
        "unique_sequence_ids": len(deduped),
        "pending_before": before_pending,
        "pending_after": after_pending,
        "reviewed_after": after_reviewed,
        "backup_path": backup_path,
        "registry_path": str(REGISTRY).replace("\\", "/"),
        "reproduce": "py scripts/normalize_encounter_sequence_curated_registry_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = normalize(dry_run=args.dry_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc.get("normalize_ok"),
                "rows_before": doc.get("rows_before"),
                "rows_after": doc.get("rows_after"),
                "pending_after": doc.get("pending_after"),
            }
        )
    )
    return 0 if doc.get("normalize_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
