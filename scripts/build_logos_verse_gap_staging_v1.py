#!/usr/bin/env python3
"""Build Track B gap staging rows from verse_4pipeline_full_31102 for verses missing in verse_decoded_v2.

Does not overwrite verse_decoded_v2.jsonl. Rows are labeled MT_SSOT_GAP_STAGING — not BHS/SBLGNT decode.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_DIFF = ROOT / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_v1_latest.json"
DEFAULT_FULL = ROOT / "data/logos/verse_4pipeline_full_31102.json"
DEFAULT_OUT = ROOT / "data/logos/verse_decoded_v2_gap_staging_v1.jsonl"
DEFAULT_META = ROOT / "docs/final/artifacts/logos_verse_gap_staging_v1_latest.json"

PLACEHOLDER_MARKERS = ("(원어 없음)", "(no original)", "원어 없음")
SCRIPT_RE = re.compile(r"[\u0590-\u05FF\u0370-\u03FF\u1F00-\u1FFF]+")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _iter_full_rows(path: Path) -> Iterator[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                yield row
        return
    if isinstance(data, dict):
        for key in ("verses", "rows", "data"):
            block = data.get(key)
            if isinstance(block, list):
                for row in block:
                    if isinstance(row, dict):
                        yield row
                return
    raise ValueError(f"unsupported full canon shape: {path}")


def _is_placeholder_preview(preview: str) -> bool:
    s = preview.strip()
    if not s:
        return True
    return any(m in s for m in PLACEHOLDER_MARKERS)


def _vector_from_full_row(row: dict[str, Any]) -> dict[str, float]:
    p4 = row.get("pipeline4_unified_v2")
    if isinstance(p4, dict):
        v = p4.get("vector_4d")
        if isinstance(v, dict):
            try:
                return {k: float(v[k]) for k in ("S", "L", "K", "M")}
            except (KeyError, TypeError, ValueError):
                pass
    p1 = row.get("pipeline1_simple_4d")
    if isinstance(p1, dict):
        v = p1.get("vector_4d")
        if isinstance(v, dict):
            try:
                return {k: float(v[k]) for k in ("S", "L", "K", "M")}
            except (KeyError, TypeError, ValueError):
                pass
    return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}


def _gematria_fields(text: str) -> dict[str, Any]:
    from scripts.core.gematria_engine import build_gematria_metadata
    from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

    meta = build_gematria_metadata(raw_text=text, compressed_text=text, reconstructed_text=text)
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    vec = bridge.get("vector_4d") or {}
    vector_4d = {k: float(vec.get(k, 0.25)) for k in ("S", "L", "K", "M")}
    return {
        "hebrew_value": int(meta.get("hebrew_value") or 0),
        "greek_value": int(meta.get("greek_value") or 0),
        "ascii_value": int(meta.get("ascii_value") or 0),
        "total_value": int(meta.get("total_value") or 0),
        "normalized_value": float(meta.get("normalized_value") or 0.0),
        "vector_4d": vector_4d,
        "unified_4d_vector": dict(vector_4d),
        "physical_constants_match": meta.get("physical_constants_match") or {},
    }


def _staging_row(row: dict[str, Any], *, ts: str) -> dict[str, Any] | None:
    vid = row.get("verse_id") or row.get("id")
    if not isinstance(vid, str) or not vid.strip():
        return None
    vid = vid.strip()
    preview = str(row.get("text_preview") or row.get("text") or "").strip()
    placeholder = _is_placeholder_preview(preview)
    base_vec = _vector_from_full_row(row)

    out: dict[str, Any] = {
        "verse_id": vid,
        "source_ref": vid.replace(".", " ").replace(":", " "),
        "edition": "MT_SSOT_GAP_STAGING",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "decode_status": "mt_full_json_placeholder" if placeholder else "mt_full_json_text_preview",
        "gap_staging": True,
        "text": preview if not placeholder else "",
        "original_text": preview if not placeholder else "",
        "interpretation": "[HYPO] MT SSOT gap staging — not BHS/SBLGNT primary decode.",
        "lambda_entropy": float((row.get("pipeline4_unified_v2") or {}).get("lambda_entropy") or 0.0),
        "distance_to_centroid": float((row.get("pipeline4_unified_v2") or {}).get("distance_to_centroid") or 0.0),
        "s_hash": vid,
        "c_mass_index": None,
        "timestamp": ts,
    }

    if not placeholder and SCRIPT_RE.search(preview):
        g = _gematria_fields(preview)
        out.update(g)
    else:
        out.update(
            {
                "hebrew_value": 0,
                "greek_value": 0,
                "ascii_value": 0,
                "total_value": 0,
                "normalized_value": 0.0,
                "vector_4d": base_vec,
                "unified_4d_vector": dict(base_vec),
                "physical_constants_match": {},
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coverage-diff", type=Path, default=DEFAULT_DIFF)
    ap.add_argument("--full-json", type=Path, default=DEFAULT_FULL)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_META)
    ap.add_argument("--max-rows", type=int, default=0)
    args = ap.parse_args()

    if not args.coverage_diff.is_file():
        print(f"missing coverage diff: {args.coverage_diff}", file=sys.stderr)
        return 2
    if not args.full_json.is_file():
        print(f"missing full canon: {args.full_json}", file=sys.stderr)
        return 2

    diff = json.loads(args.coverage_diff.read_text(encoding="utf-8-sig"))
    missing = diff.get("missing_verse_ids")
    if not isinstance(missing, list):
        print("coverage diff has no missing_verse_ids", file=sys.stderr)
        return 2
    want = {str(v).strip() for v in missing if str(v).strip()}
    if not want:
        print("empty gap set", file=sys.stderr)
        return 2

    ts = _utc_now()
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    placeholder_n = 0
    preview_gematria_n = 0
    written = 0
    with args.out_jsonl.open("w", encoding="utf-8") as fh:
        for row in _iter_full_rows(args.full_json):
            vid = row.get("verse_id") or row.get("id")
            if not isinstance(vid, str) or vid.strip() not in want:
                continue
            rec = _staging_row(row, ts=ts)
            if rec is None:
                continue
            if rec.get("decode_status") == "mt_full_json_placeholder":
                placeholder_n += 1
            else:
                preview_gematria_n += 1
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
            if args.max_rows > 0 and written >= args.max_rows:
                break

    meta = {
        "schema": "logos_verse_gap_staging_v1",
        "version": "1.0.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "gap_count_expected": len(want),
        "rows_written": written,
        "placeholder_rows": placeholder_n,
        "text_preview_gematria_rows": preview_gematria_n,
        "out_jsonl": _rel(args.out_jsonl),
        "note": "Staging only — does not replace verse_decoded_v2 BHS+SBLGNT rows.",
        "track_wall": {"a_track_auto_promotion": False, "ready_for_external_send": False},
    }
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out_jsonl} rows={written} placeholder={placeholder_n} preview_gematria={preview_gematria_n}",
        flush=True,
    )
    return 0 if written == len(want) or args.max_rows > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
