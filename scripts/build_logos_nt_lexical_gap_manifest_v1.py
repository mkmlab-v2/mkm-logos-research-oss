#!/usr/bin/env python3
"""Emit SSOT manifest for NT verses that remain without SBLGNT lexical fill (B-track).

Reads gap ingest queue vs lexical fill JSONL. Does not call external APIs.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_logos_gap_original_text_v1 import NT_BOOKS  # noqa: E402

DEFAULT_QUEUE = ROOT / "reports/constitution/btrack_pilot/logos_verse_gap_ingest_queue_v1_latest.jsonl"
DEFAULT_FILL = ROOT / "data/logos/verse_decoded_v2_lexical_fill_v1.jsonl"
DEFAULT_META = ROOT / "docs/final/artifacts/logos_verse_lexical_fill_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_nt_lexical_gap_manifest_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _filled_ids(fill_jsonl: Path) -> set[str]:
    out: set[str] = set()
    for line in fill_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        vid = row.get("verse_id") or row.get("mt_verse_id")
        if vid:
            out.add(str(vid))
    return out


def _queue_ids(queue_jsonl: Path) -> list[str]:
    ids: list[str] = []
    for line in queue_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        vid = row.get("verse_id") or row.get("id")
        if vid:
            ids.append(str(vid))
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gap-queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--fill-jsonl", type=Path, default=DEFAULT_FILL)
    ap.add_argument("--fill-meta", type=Path, default=DEFAULT_META)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.gap_queue.is_file():
        print(f"missing gap queue: {args.gap_queue}", file=sys.stderr)
        return 2
    if not args.fill_jsonl.is_file():
        print(f"missing fill jsonl: {args.fill_jsonl}", file=sys.stderr)
        return 2

    filled = _filled_ids(args.fill_jsonl)
    missing_nt: list[str] = []
    for vid in _queue_ids(args.gap_queue):
        book = vid.split(".")[0]
        if book in NT_BOOKS and vid not in filled:
            missing_nt.append(vid)

    ingest_meta: dict = {}
    if args.fill_meta.is_file():
        ingest_meta = json.loads(args.fill_meta.read_text(encoding="utf-8"))

    doc = {
        "schema": "logos_nt_lexical_gap_manifest_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "missing_nt_count": len(missing_nt),
        "missing_nt_verse_ids": missing_nt,
        "policy_note_ko": (
            "SBLGNT/morphgnt에 없는 장·절 변형(전통적으로 괄호 처리된 구절). "
            "MT-only 정책 라벨 또는 별도 원문 소스 없이 lexical decode를 채우지 않음."
        ),
        "ingest_meta_pointer": str(args.fill_meta.relative_to(ROOT)).replace("\\", "/"),
        "ingest_meta_missing_nt": ingest_meta.get("missing_nt"),
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out_json} missing_nt={len(missing_nt)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
