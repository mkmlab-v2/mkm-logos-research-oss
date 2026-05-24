#!/usr/bin/env python3
"""Ingest Scrivener 1894 TR Greek from honza/textus-receptus into tr_greek_by_verse_v1.jsonl (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_tr_osis_to_mt_verse_v1 import honza_row_to_verse_id  # noqa: E402

HONZA_FLAT_URL = (
    "https://raw.githubusercontent.com/honza/textus-receptus/master/data/gnt.flat.json"
)
DEFAULT_CACHE = ROOT / "data/logos/manuscripts/cache/honza_gnt.flat.json"
DEFAULT_OUT = ROOT / "data/logos/manuscripts/tr_greek_by_verse_v1.jsonl"
DEFAULT_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_GAP_REPORT = ROOT / "docs/final/artifacts/logos_tr_greek_gap_hit_report_v1_latest.json"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_tr_greek_ingest_manifest_v1_latest.json"

SOURCE_ID = "TR_SCRIVENER_1894_HONZA"
LICENSE_TAG = "honza_free_use_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _load_policy_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(str(json.loads(line)["verse_id"]))
    return ids


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-Logos-TR-Ingest/1.0"})
    with urllib.request.urlopen(req, timeout=600) as resp:  # noqa: S310
        data = resp.read()
    dest.write_bytes(data)


def _load_honza_flat(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("verses"), list):
        return raw["verses"]
    raise ValueError(f"unexpected honza JSON shape: {type(raw)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--url", default=HONZA_FLAT_URL)
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--policy-jsonl", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--gap-report", type=Path, default=DEFAULT_GAP_REPORT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument(
        "--gap-only",
        action="store_true",
        help="Write only verses listed in policy-jsonl (15 MT-only gaps).",
    )
    ap.add_argument("--full-nt", action="store_true", help="Write all mapped NT verses (overrides --gap-only).")
    args = ap.parse_args()

    cache = args.cache_path
    if not cache.is_file():
        if args.skip_download:
            print(f"missing cache: {cache} (remove --skip-download)", file=sys.stderr)
            return 2
        print(f"downloading {args.url} -> {cache}", flush=True)
        try:
            _download(args.url, cache)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"download failed: {exc}", file=sys.stderr)
            return 2

    policy_ids = _load_policy_ids(args.policy_jsonl)
    limit_ids: set[str] | None = policy_ids if args.gap_only and not args.full_nt else None

    rows = _load_honza_flat(cache)
    written: dict[str, dict[str, Any]] = {}
    unmapped = 0
    for row in rows:
        vid = honza_row_to_verse_id(row)
        if not vid:
            unmapped += 1
            continue
        if limit_ids is not None and vid not in limit_ids:
            continue
        greek = str(row.get("greek_text") or "").strip()
        if not greek:
            continue
        written[vid] = {
            "verse_id": vid,
            "greek_text": greek,
            "source_id": SOURCE_ID,
            "license_tag": LICENSE_TAG,
            "manuscript_edition": "TR_SCRIVENER_1894",
            "source_track": "B_ext",
            "honza_book_name_osis": row.get("book_name_osis"),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for vid in sorted(written.keys()):
            f.write(json.dumps(written[vid], ensure_ascii=False) + "\n")

    gap_hits: list[dict[str, Any]] = []
    for vid in sorted(policy_ids):
        hit = written.get(vid)
        gap_hits.append(
            {
                "verse_id": vid,
                "hit": hit is not None,
                "greek_chars": len(hit["greek_text"]) if hit else 0,
                "preview": (hit["greek_text"][:80] + "…") if hit and len(hit["greek_text"]) > 80 else (hit or {}).get("greek_text"),
            }
        )

    gap_report = {
        "schema": "logos_tr_greek_gap_hit_report_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "policy_verse_count": len(policy_ids),
        "hits": sum(1 for g in gap_hits if g["hit"]),
        "misses": [g["verse_id"] for g in gap_hits if not g["hit"]],
        "verses": gap_hits,
        "cache_path": _rel(cache),
        "output_jsonl": _rel(args.output),
    }
    args.gap_report.parent.mkdir(parents=True, exist_ok=True)
    args.gap_report.write_text(json.dumps(gap_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "logos_tr_greek_ingest_manifest_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "source_url": args.url,
        "rows_written": len(written),
        "honza_rows_scanned": len(rows),
        "unmapped_honza_rows": unmapped,
        "gap_only": bool(limit_ids),
        "output_jsonl": _rel(args.output),
        "gap_report": _rel(args.gap_report),
        "track_wall": {
            "merge_into_complete_jsonl": False,
            "ready_for_external_send": False,
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"wrote {args.output} rows={len(written)} "
        f"gap_hits={gap_report['hits']}/{gap_report['policy_verse_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
