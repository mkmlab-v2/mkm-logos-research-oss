#!/usr/bin/env python3
"""TR Greek → gematria_bridge_v1 vector_4d for MT-only gap verses (variant layer only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_IN = ROOT / "data/logos/manuscripts/tr_greek_by_verse_v1.jsonl"
DEFAULT_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_tr_variant_vectors_v1_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "docs/final/artifacts/logos_tr_variant_vectors_summary_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _policy_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(str(json.loads(line)["verse_id"]))
    return ids


def _vector_from_greek(text: str) -> dict[str, float]:
    from scripts.core.gematria_engine import build_gematria_metadata
    from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

    meta = build_gematria_metadata(raw_text=text, compressed_text=text, reconstructed_text=text)
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    vec = bridge.get("vector_4d") or {}
    return {k: float(vec.get(k, 0.25)) for k in ("S", "L", "K", "M")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--policy-jsonl", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--all-input-rows", action="store_true", help="Ignore policy filter.")
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        print(f"missing {args.input_jsonl}", file=sys.stderr)
        return 2

    want = None if args.all_input_rows else _policy_ids(args.policy_jsonl)
    out_rows: list[dict[str, Any]] = []
    for line in args.input_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        vid = str(row["verse_id"])
        if want is not None and vid not in want:
            continue
        greek = str(row.get("greek_text") or "").strip()
        if not greek:
            continue
        vec = _vector_from_greek(greek)
        digest = hashlib.sha256(greek.encode("utf-8")).hexdigest()[:16]
        out_rows.append(
            {
                "verse_id": vid,
                "vector_4d": vec,
                "greek_text_sha256_prefix": digest,
                "source_id": row.get("source_id") or "TR_SCRIVENER_1894_HONZA",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "source_track": "B_ext",
            }
        )

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for rec in sorted(out_rows, key=lambda r: r["verse_id"]):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    summary = {
        "schema": "logos_tr_variant_vectors_summary_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "vector_count": len(out_rows),
        "input_jsonl": _rel(args.input_jsonl),
        "output_jsonl": _rel(args.output_jsonl),
        "track_wall": {"merge_into_complete_jsonl": False},
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output_jsonl} vectors={len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
