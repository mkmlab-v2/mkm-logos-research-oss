#!/usr/bin/env python3
"""Export WTT session or compression JSONL rows into open-bench contributor format [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CONTRIBUTOR_LABELS = [
    "contributor_provided",
    "research_only",
    "btrack_learning_v1",
    "masked",
]
MIN_TEXT_LEN = 40  # align with validate_compression_contributor_jsonl_v1.py
SHORT_TEXT_PAD = " [assistant] 접수 확인 후 순차적으로 안내 드리겠습니다."


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _flatten_text(row: dict[str, Any]) -> str:
    if isinstance(row.get("text"), str) and row["text"].strip():
        return row["text"].strip()
    parts: list[str] = []
    for turn in row.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or "user")
        parts.append(f"[{role}] {turn.get('text', '')}")
    return " ".join(parts).strip()


def to_contributor_row(
    row: dict[str, Any],
    *,
    row_id: str,
    domain_tag: str | None = None,
    extra_labels: list[str] | None = None,
    provenance_note: str | None = None,
) -> dict[str, Any]:
    text = _flatten_text(row)
    while len(text.strip()) < MIN_TEXT_LEN:
        text = (text + SHORT_TEXT_PAD).strip()
    labels = list(CONTRIBUTOR_LABELS)
    if extra_labels:
        for tag in extra_labels:
            if tag not in labels:
                labels.append(tag)
    out: dict[str, Any] = {
        "id": row_id,
        "text": text,
        "domain_tag": domain_tag or row.get("domain_tag") or "community-contrib",
        "labels": labels,
        "contributor_provided": True,
        "customer_provided": False,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
    }
    if provenance_note:
        out["provenance_note"] = provenance_note
    return out


def export_jsonl(
    src: Path,
    *,
    id_prefix: str,
    domain_tag: str | None = None,
    extra_labels: list[str] | None = None,
    provenance_note: str | None = None,
    max_rows: int | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(src.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        if max_rows is not None and len(rows) >= max_rows:
            break
        session = json.loads(line)
        sid = str(session.get("session_id") or session.get("id") or f"{id_prefix}-{i:03d}")
        safe_id = f"{id_prefix}-{len(rows):03d}"
        if sid and not sid.startswith(id_prefix):
            safe_id = f"{id_prefix}-{sid}"[:64]
        rows.append(
            to_contributor_row(
                session,
                row_id=safe_id,
                domain_tag=domain_tag,
                extra_labels=extra_labels,
                provenance_note=provenance_note,
            )
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, required=True, help="WTT session or compression JSONL input")
    ap.add_argument("--out", type=Path, required=True, help="Contributor JSONL output path")
    ap.add_argument("--id-prefix", default="contrib-open-bench")
    ap.add_argument("--domain-tag", default=None)
    ap.add_argument("--extra-label", action="append", default=[])
    ap.add_argument(
        "--provenance-note",
        default="open_bench_community_seed_v1",
        help="Optional row metadata (not used for promotion gates)",
    )
    ap.add_argument("--max-rows", type=int, default=None)
    args = ap.parse_args()

    src = args.jsonl.resolve()
    if not src.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {src}"}))
        return 1

    rows = export_jsonl(
        src,
        id_prefix=args.id_prefix,
        domain_tag=args.domain_tag,
        extra_labels=args.extra_label or None,
        provenance_note=args.provenance_note,
        max_rows=args.max_rows,
    )
    if len(rows) < 10:
        print(json.dumps({"ok": False, "error": f"need>=10 rows, got {len(rows)}"}))
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "rows": len(rows),
                "out": str(args.out.resolve()),
                "generated_at_utc": _utc_now(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
