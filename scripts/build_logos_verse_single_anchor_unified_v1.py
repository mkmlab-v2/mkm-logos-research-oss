#!/usr/bin/env python3
"""Merge verse_decoded_v2 (BHS/SBLGNT quality core) + MT pipeline stubs for gap verses into single-anchor JSONL.

Does not claim BHS/SBLGNT decode for rows where upstream text_preview is placeholder. Sets honest
decode_status and upstream_original_text_missing. Track B / [HYPO] only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_logos_verse_gap_staging_v1 import (  # noqa: E402
    DEFAULT_DIFF,
    DEFAULT_FULL,
    PLACEHOLDER_MARKERS,
    _iter_full_rows,
    _is_placeholder_preview,
    _staging_row,
    _vector_from_full_row,
)

DEFAULT_V2 = ROOT / "data/logos/verse_decoded_v2.jsonl"
DEFAULT_LEXICAL_FILL = ROOT / "data/logos/verse_decoded_v2_lexical_fill_v1.jsonl"
DEFAULT_MT_ONLY_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_OUT = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
DEFAULT_META = ROOT / "docs/final/artifacts/logos_verse_single_anchor_unified_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _to_single_anchor_stub(
    staging: dict[str, Any],
    *,
    ts: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = dict(staging)
    preview = str(out.get("text") or out.get("original_text") or "").strip()
    placeholder = _is_placeholder_preview(preview)
    out["single_anchor_lane"] = "U"
    out["gap_staging"] = False
    out["upstream_original_text_missing"] = True
    if policy:
        out["decode_status"] = str(policy.get("decode_status") or "mt_canon_only_no_critical_text")
        out["mt_only_policy_class"] = policy.get("policy_class")
        out["mt_only_residual_cause"] = policy.get("residual_cause")
        out["edition"] = "MT_CANON_ONLY_NO_CRITICAL_TEXT"
        out["interpretation"] = str(
            policy.get("interpretation")
            or "[HYPO] MT canon only — no local BHS/SBLGNT critical text."
        )
    else:
        out["upstream_original_text_missing"] = placeholder
        out["decode_status"] = (
            "mt_pipeline_vector_stub" if placeholder else "mt_pipeline_text_preview_gematria"
        )
        out["edition"] = "MT_SSOT_PIPELINE_STUB" if placeholder else "MT_SSOT_TEXT_PREVIEW"
        out["interpretation"] = (
            "[HYPO] Single-anchor union stub — pipeline vector/gematria only; not primary BHS/SBLGNT."
            if placeholder
            else "[HYPO] Single-anchor union — MT text_preview gematria; not primary BHS/SBLGNT."
        )
    out["timestamp"] = ts
    return out


def _tag_v2_quality(row: dict[str, Any], *, ts: str) -> dict[str, Any]:
    out = dict(row)
    out["single_anchor_lane"] = "U"
    out["gap_staging"] = False
    out["upstream_original_text_missing"] = False
    if not out.get("decode_status"):
        out["decode_status"] = "bhs_sblgnt_v2_core"
    out.setdefault("edition", "BHS_SBLGNT_V2")
    out["timestamp"] = ts
    return out


def _tag_lexical_fill(row: dict[str, Any], *, ts: str) -> dict[str, Any]:
    out = dict(row)
    out["single_anchor_lane"] = "U"
    out["gap_staging"] = False
    out["upstream_original_text_missing"] = False
    out["timestamp"] = ts
    return out


def _load_jsonl_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in _iter_jsonl(path):
        vid = str(row.get("verse_id") or "").strip()
        if vid:
            out[vid] = row
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2-jsonl", type=Path, default=DEFAULT_V2)
    ap.add_argument("--coverage-diff", type=Path, default=DEFAULT_DIFF)
    ap.add_argument("--full-json", type=Path, default=DEFAULT_FULL)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_META)
    ap.add_argument(
        "--lexical-fill-jsonl",
        type=Path,
        default=DEFAULT_LEXICAL_FILL,
        help="Gap verses with real BHS/SBLGNT from ingest_logos_gap_original_text_v1.py",
    )
    ap.add_argument(
        "--mt-only-policy-jsonl",
        type=Path,
        default=DEFAULT_MT_ONLY_POLICY,
        help="SA-S14 policy labels for remaining MT-only gap stubs",
    )
    ap.add_argument("--max-gap-rows", type=int, default=0, help="0 = all gap rows (pilot: e.g. 100)")
    args = ap.parse_args()

    if not args.v2_jsonl.is_file():
        print(f"missing v2: {args.v2_jsonl}", file=sys.stderr)
        return 2
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

    ts = _utc_now()
    lexical = _load_jsonl_index(args.lexical_fill_jsonl)
    mt_policy = _load_jsonl_index(args.mt_only_policy_jsonl)
    seen: set[str] = set()
    v2_n = 0
    stub_n = 0
    mt_only_policy_n = 0
    preview_gem_n = 0
    lexical_n = 0
    gap_written = 0

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as out:
        for row in _iter_jsonl(args.v2_jsonl):
            vid = str(row.get("verse_id") or "").strip()
            if not vid or vid in seen:
                continue
            seen.add(vid)
            out.write(json.dumps(_tag_v2_quality(row, ts=ts), ensure_ascii=False) + "\n")
            v2_n += 1

        for row in _iter_full_rows(args.full_json):
            vid = row.get("verse_id") or row.get("id")
            if not isinstance(vid, str) or vid.strip() not in want:
                continue
            vid = vid.strip()
            if vid in lexical:
                out.write(json.dumps(_tag_lexical_fill(lexical[vid], ts=ts), ensure_ascii=False) + "\n")
                lexical_n += 1
                seen.add(vid)
                gap_written += 1
                if args.max_gap_rows > 0 and gap_written >= args.max_gap_rows:
                    break
                continue
            staging = _staging_row(row, ts=ts)
            if staging is None:
                continue
            pol = mt_policy.get(vid)
            rec = _to_single_anchor_stub(staging, ts=ts, policy=pol)
            if pol:
                mt_only_policy_n += 1
            elif rec.get("decode_status") == "mt_pipeline_vector_stub":
                stub_n += 1
            else:
                preview_gem_n += 1
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            seen.add(vid)
            gap_written += 1
            if args.max_gap_rows > 0 and gap_written >= args.max_gap_rows:
                break

    meta = {
        "schema": "logos_verse_single_anchor_unified_v1",
        "version": "1.0.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "v2_quality_rows": v2_n,
        "gap_stub_rows": stub_n,
        "gap_mt_only_policy_rows": mt_only_policy_n,
        "gap_lexical_fill_rows": lexical_n,
        "gap_preview_gematria_rows": preview_gem_n,
        "lexical_fill_jsonl": _rel(args.lexical_fill_jsonl) if lexical else None,
        "union_rows": v2_n + gap_written,
        "gap_expected": len(want),
        "upstream_bhs_sblgnt_blocker": stub_n > 0,
        "boundary_sentence_ko": (
            "단일 앵커 31,102 — "
            f"품질 코어 {v2_n} + 원어 {lexical_n} + MT-only 정책 {mt_only_policy_n} + legacy stub {stub_n}."
        ),
        "out_jsonl": _rel(args.out_jsonl),
        "track_wall": {"a_track_auto_promotion": False, "ready_for_external_send": False},
    }
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out_jsonl} union_rows={v2_n + gap_written} v2={v2_n} "
        f"gap={gap_written} lexical={lexical_n} mt_only_policy={mt_only_policy_n} "
        f"stub={stub_n} preview_gem={preview_gem_n}",
        flush=True,
    )
    ok = gap_written == len(want) or args.max_gap_rows > 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
