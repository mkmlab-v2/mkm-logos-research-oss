#!/usr/bin/env python3
"""Build logos_verse_4d_v1 corpus JSONL + manifest (Track B).

Imports verse-level 4D from data/logos/verse_decoded_v2.jsonl when present, or
recomputes via gematria_bridge_v1 for audit (--recompute-audit).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_IN = ROOT / "data" / "logos" / "verse_decoded_v2.jsonl"
DEFAULT_JSONL = OUT_DIR / "logos_verse_4d_v1_latest.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_verse_4d_corpus_v1_latest.json"

SCRIPT_RE = re.compile(r"[\u0590-\u05FF\u0370-\u03FF\u1F00-\u1FFF]+")


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _original_script_text(row: dict[str, Any]) -> str:
    for k in ("original_text", "text"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _lane_from_row(row: dict[str, Any]) -> str:
    vid = str(row.get("verse_id") or "")
    if vid.startswith("apo:"):
        return "apocrypha"
    return "canon"


def _vector_from_row(row: dict[str, Any]) -> dict[str, float] | None:
    v = row.get("vector_4d") or row.get("unified_4d_vector")
    if not isinstance(v, dict):
        return None
    try:
        return {
            "S": float(v["S"]),
            "L": float(v["L"]),
            "K": float(v["K"]),
            "M": float(v["M"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _recompute_bridge(text: str) -> tuple[dict[str, float], dict[str, Any]]:
    from scripts.core.gematria_engine import build_gematria_metadata
    from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

    meta = build_gematria_metadata(raw_text=text, compressed_text=text, reconstructed_text=text)
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    vec = bridge.get("vector_4d") or {}
    out = {k: float(vec.get(k, 0.25)) for k in ("S", "L", "K", "M")}
    return out, {"meta": meta, "bridge": bridge}


def _row_to_record(
    row: dict[str, Any],
    *,
    lane: str,
    recipe_id: str,
    source_kind: str,
    input_path: str,
    ts: str,
    recompute: bool,
) -> dict[str, Any] | None:
    vid = row.get("verse_id")
    if not isinstance(vid, str) or not vid.strip():
        return None
    vid = vid.strip()

    txt = _original_script_text(row)
    vec = _vector_from_row(row)
    if not txt:
        if vec is not None and (
            row.get("gap_staging")
            or row.get("upstream_original_text_missing")
            or str(row.get("decode_status") or "").startswith("mt_pipeline")
        ):
            txt = f"[MT_SSOT_GAP_STAGING:{vid}]"
        else:
            return None
    state16: dict[str, Any] | None = None
    gematria: dict[str, Any] = {
        "hebrew_value": int(row.get("hebrew_value") or 0),
        "greek_value": int(row.get("greek_value") or 0),
        "ascii_value": int(row.get("ascii_value") or 0),
        "total_value": int(row.get("total_value") or 0),
    }
    if row.get("normalized_value") is not None:
        gematria["normalized_value"] = float(row["normalized_value"])

    if recompute or vec is None:
        vec, aux = _recompute_bridge(txt)
        meta = aux["meta"]
        bridge = aux["bridge"]
        gematria["raw_combined_sum"] = int(meta.get("raw_combined_sum") or 0)
        gematria["compressed_combined_sum"] = int(meta.get("compressed_combined_sum") or 0)
        gematria["reconstructed_combined_sum"] = int(meta.get("reconstructed_combined_sum") or 0)
        recipe_id = "gematria_bridge_v1_recompute_audit"
        source_kind = "recomputed"
        if bridge.get("state16") is not None:
            state16 = {
                "state_id": int(bridge["state16"]),
                "distance_to_state16": float(bridge.get("distance_to_state16") or 0.0),
                "probe_path": str(bridge.get("probe_path") or ""),
            }
    elif vec is not None:
        recipe_id = recipe_id if recipe_id != "gematria_bridge_v1_recompute_audit" else "verse_decoded_v2_legacy"
        source_kind = "imported"

    rec: dict[str, Any] = {
        "schema": "logos_verse_4d_v1",
        "version": "1.0.0",
        "verse_id": vid,
        "source_ref": str(row.get("source_ref") or ""),
        "lane": lane,
        "text_span": {
            "unit": "verse",
            "original_script_text": txt,
            "text_sha256": _sha256_text(txt),
        },
        "gematria_v1": gematria,
        "vector_4d": vec,
        "mapping": {
            "recipe_id": recipe_id,
            "source_kind": source_kind,
            "generated_at_utc": ts,
            "input_path": input_path,
        },
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
            "ready_for_external_send": False,
        },
    }
    if state16:
        rec["state16"] = state16
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description="Build logos_verse_4d_v1 corpus (Track B)")
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--lane", default="canon", choices=("canon", "dss", "apocrypha", "other"))
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--out-manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--recompute-audit", action="store_true", help="Re-run gematria bridge for every row")
    ap.add_argument("--max-rows", type=int, default=0, help="0 = all rows")
    ap.add_argument(
        "--recipe-id",
        default="verse_decoded_v2_legacy",
        choices=(
            "verse_decoded_v2_legacy",
            "gematria_bridge_v1",
            "gematria_bridge_v1_recompute_audit",
        ),
    )
    args = ap.parse_args()

    in_path = Path(args.input_jsonl)
    if not in_path.is_file():
        print(f"ERROR: missing input: {in_path}", flush=True)
        return 2

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_jsonl = Path(args.out_jsonl)
    if not out_jsonl.is_absolute():
        out_jsonl = ROOT / out_jsonl
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    emitted = 0
    skipped = 0
    dup_ids: set[str] = set()
    dup_count = 0
    null_vid = 0
    missing_vec = 0
    lanes: dict[str, int] = {}

    with out_jsonl.open("w", encoding="utf-8") as out_f:
        for i, row in enumerate(_iter_jsonl(in_path)):
            if args.max_rows and i >= args.max_rows:
                break
            lane = args.lane if args.lane != "canon" else _lane_from_row(row)
            rec = _row_to_record(
                row,
                lane=lane,
                recipe_id=str(args.recipe_id),
                source_kind="imported",
                input_path=str(in_path.as_posix()),
                ts=ts,
                recompute=bool(args.recompute_audit),
            )
            if rec is None:
                skipped += 1
                if not row.get("verse_id"):
                    null_vid += 1
                continue
            vid = rec["verse_id"]
            if vid in dup_ids:
                dup_count += 1
            else:
                dup_ids.add(vid)
            if not rec.get("vector_4d"):
                missing_vec += 1
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            emitted += 1
            lanes[lane] = lanes.get(lane, 0) + 1

    manifest: dict[str, Any] = {
        "schema": "logos_verse_4d_corpus_v1",
        "version": "1.0.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mapping_recipe_id": (
            "gematria_bridge_v1_recompute_audit"
            if args.recompute_audit
            else str(args.recipe_id)
        ),
        "purpose": "Track B verse-level 4D corpus for [HYPO] OS-code research; not Track A compression.",
        "inputs": {
            "primary_jsonl": str(in_path.as_posix()),
            "primary_sha256": _sha256_file(in_path),
        },
        "outputs": {
            "verse_4d_jsonl": str(out_jsonl.as_posix()),
            "verse_4d_jsonl_sha256": _sha256_file(out_jsonl),
            "manifest_self": str(
                (ROOT / args.out_manifest if not Path(args.out_manifest).is_absolute() else args.out_manifest).as_posix()
            ),
        },
        "counts": {
            "rows_emitted": emitted,
            "rows_skipped_empty_text": skipped,
            "lanes": lanes,
        },
        "integrity": {
            "duplicate_verse_id_count": dup_count,
            "null_verse_id_count": null_vid,
            "vector_4d_missing_count": missing_vec,
        },
        "null_baselines_planned": [
            "greek_non_canon_control_jsonl",
            "hebrew_surface_shuffle_control",
            "random_token_bag_matched_length",
        ],
        "track_wall": {
            "a_track_auto_promotion": False,
            "compression_4d_bridge_policy": "off_for_track_a_frozen_47pct",
        },
        "notes": "SSOT contract: docs/final/artifacts/LOGOS_VERSE_4D_V1_CONTRACT.json",
    }

    out_manifest = Path(args.out_manifest)
    if not out_manifest.is_absolute():
        out_manifest = ROOT / out_manifest
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {"ok": True, "emitted": emitted, "skipped": skipped, "jsonl": str(out_jsonl), "manifest": str(out_manifest)},
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
