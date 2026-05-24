#!/usr/bin/env python3
"""Build null-control verse_4d corpora from canon logos_verse_4d_v1 (Track B Phase 4).

Emits vector-permutation, char-shuffle, and token-shuffle null JSONLs plus optional
apocrypha lane corpus. [HYPO] — not Track A / external send.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_logos_verse_4d_corpus_v1 import (  # noqa: E402
    _iter_jsonl,
    _recompute_bridge,
    _row_to_record,
    _sha256_text,
)

OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_CANON = OUT_DIR / "logos_verse_4d_v1_latest.jsonl"
DEFAULT_APOCRYPHA_IN = ROOT / "data" / "logos" / "manuscripts" / "apocrypha_original_only_latest.jsonl"

OUT_VECTOR_PERM = OUT_DIR / "logos_verse_4d_null_vector_permutation_v1_latest.jsonl"
OUT_CHAR_SHUFFLE = OUT_DIR / "logos_verse_4d_null_char_shuffle_v1_latest.jsonl"
OUT_TOKEN_SHUFFLE = OUT_DIR / "logos_verse_4d_null_token_shuffle_v1_latest.jsonl"
OUT_APOCRYPHA = OUT_DIR / "logos_verse_4d_apocrypha_lane_v1_latest.jsonl"

TOKEN_RE = re.compile(r"\S+")

TRACK_WALL: dict[str, bool] = {
    "a_track_auto_promotion": False,
    "live_trading_trigger": False,
    "ready_for_external_send": False,
}


def _load_canon_rows(path: Path, max_rows: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, row in enumerate(_iter_jsonl(path)):
        if max_rows and i >= max_rows:
            break
        if row.get("schema") != "logos_verse_4d_v1":
            continue
        rows.append(row)
    return rows


def _text_from_row(row: dict[str, Any]) -> str:
    span = row.get("text_span")
    if isinstance(span, dict):
        txt = span.get("original_script_text")
        if isinstance(txt, str) and txt.strip():
            return txt.strip()
    return ""


def _null_mapping(
    row: dict[str, Any],
    *,
    null_kind: str,
    source_kind: str,
    recipe_id: str,
    input_path: str,
    ts: str,
) -> dict[str, Any]:
    mapping = dict(row.get("mapping") or {})
    mapping["recipe_id"] = recipe_id
    mapping["source_kind"] = source_kind
    mapping["generated_at_utc"] = ts
    mapping["input_path"] = input_path
    return mapping


def _emit_null_vector_permutation(
    rows: list[dict[str, Any]],
    *,
    rng: random.Random,
    ts: str,
    input_path: str,
) -> list[dict[str, Any]]:
    vectors = [deepcopy(r["vector_4d"]) for r in rows if isinstance(r.get("vector_4d"), dict)]
    if len(vectors) != len(rows):
        raise ValueError("canon rows missing vector_4d")
    order = list(range(len(vectors)))
    rng.shuffle(order)
    shuffled = [vectors[i] for i in order]
    out: list[dict[str, Any]] = []
    for row, vec in zip(rows, shuffled):
        rec = deepcopy(row)
        rec["vector_4d"] = vec
        rec["mapping"] = _null_mapping(
            row,
            null_kind="vector_permutation",
            source_kind="blended",
            recipe_id=str((row.get("mapping") or {}).get("recipe_id") or "verse_decoded_v2_legacy"),
            input_path=input_path,
            ts=ts,
        )
        rec["notes"] = (
            "[HYPO] null baseline: vector_4d permuted across verses; text/gematria unchanged."
        )
        rec["track_wall"] = dict(TRACK_WALL)
        out.append(rec)
    return out


def _shuffle_chars(text: str, rng: random.Random) -> str:
    chars = list(text)
    rng.shuffle(chars)
    return "".join(chars)


def _shuffle_tokens(text: str, rng: random.Random) -> str:
    tokens = TOKEN_RE.findall(text)
    if not tokens:
        return text
    rng.shuffle(tokens)
    return " ".join(tokens)


def _recompute_row_text(
    row: dict[str, Any],
    new_text: str,
    *,
    null_kind: str,
    ts: str,
    input_path: str,
) -> dict[str, Any]:
    vec, aux = _recompute_bridge(new_text)
    meta = aux["meta"]
    bridge = aux["bridge"]
    gematria: dict[str, Any] = {
        "hebrew_value": 0,
        "greek_value": 0,
        "ascii_value": 0,
        "total_value": 0,
        "raw_combined_sum": int(meta.get("raw_combined_sum") or 0),
        "compressed_combined_sum": int(meta.get("compressed_combined_sum") or 0),
        "reconstructed_combined_sum": int(meta.get("reconstructed_combined_sum") or 0),
    }
    rec = deepcopy(row)
    rec["text_span"] = {
        "unit": "verse",
        "original_script_text": new_text,
        "text_sha256": _sha256_text(new_text),
    }
    rec["gematria_v1"] = gematria
    rec["vector_4d"] = vec
    if bridge.get("state16") is not None:
        rec["state16"] = {
            "state_id": int(bridge["state16"]),
            "distance_to_state16": float(bridge.get("distance_to_state16") or 0.0),
            "probe_path": str(bridge.get("probe_path") or ""),
        }
    elif "state16" in rec:
        del rec["state16"]
    rec["mapping"] = _null_mapping(
        row,
        null_kind=null_kind,
        source_kind="recomputed",
        recipe_id="gematria_bridge_v1_recompute_audit",
        input_path=input_path,
        ts=ts,
    )
    rec["notes"] = f"[HYPO] null baseline: {null_kind}; gematria bridge recompute."
    rec["track_wall"] = dict(TRACK_WALL)
    return rec


def _emit_null_char_shuffle(
    rows: list[dict[str, Any]],
    *,
    rng: random.Random,
    ts: str,
    input_path: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        txt = _text_from_row(row)
        if not txt:
            out.append(deepcopy(row))
            continue
        new_txt = _shuffle_chars(txt, rng)
        out.append(
            _recompute_row_text(
                row,
                new_txt,
                null_kind="char_shuffle",
                ts=ts,
                input_path=input_path,
            )
        )
    return out


def _emit_null_token_shuffle(
    rows: list[dict[str, Any]],
    *,
    rng: random.Random,
    ts: str,
    input_path: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        txt = _text_from_row(row)
        if not txt:
            out.append(deepcopy(row))
            continue
        new_txt = _shuffle_tokens(txt, rng)
        out.append(
            _recompute_row_text(
                row,
                new_txt,
                null_kind="token_shuffle",
                ts=ts,
                input_path=input_path,
            )
        )
    return out


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


def _build_apocrypha_lane(
    in_path: Path,
    *,
    max_rows: int,
    ts: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(_iter_jsonl(in_path)):
        if max_rows and i >= max_rows:
            break
        rec = _row_to_record(
            row,
            lane="apocrypha",
            recipe_id="gematria_bridge_v1_recompute_audit",
            source_kind="recomputed",
            input_path=str(in_path.as_posix()),
            ts=ts,
            recompute=True,
        )
        if rec is not None:
            rec["track_wall"] = dict(TRACK_WALL)
            out.append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build logos verse 4D null corpora (Track B Phase 4)")
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_CANON)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-rows", type=int, default=0, help="0 = all rows")
    ap.add_argument("--skip-vector-permutation", action="store_true")
    ap.add_argument("--skip-char-shuffle", action="store_true")
    ap.add_argument("--skip-token-shuffle", action="store_true")
    ap.add_argument("--skip-apocrypha", action="store_true")
    ap.add_argument("--apocrypha-input-jsonl", type=Path, default=DEFAULT_APOCRYPHA_IN)
    ap.add_argument("--out-vector-permutation", type=Path, default=OUT_VECTOR_PERM)
    ap.add_argument("--out-char-shuffle", type=Path, default=OUT_CHAR_SHUFFLE)
    ap.add_argument("--out-token-shuffle", type=Path, default=OUT_TOKEN_SHUFFLE)
    ap.add_argument("--out-apocrypha", type=Path, default=OUT_APOCRYPHA)
    args = ap.parse_args()

    in_path = Path(args.input_jsonl)
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not in_path.is_file():
        print(f"ERROR: missing canon input: {in_path}", flush=True)
        return 2

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    input_posix = str(in_path.as_posix())
    rows = _load_canon_rows(in_path, int(args.max_rows))
    if not rows:
        print("ERROR: no valid canon rows loaded", flush=True)
        return 2

    rng = random.Random(int(args.seed))
    summary: dict[str, Any] = {"ok": True, "canon_rows": len(rows), "outputs": {}}

    if not args.skip_vector_permutation:
        out_path = Path(args.out_vector_permutation)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        recs = _emit_null_vector_permutation(rows, rng=rng, ts=ts, input_path=input_posix)
        n = _write_jsonl(out_path, recs)
        summary["outputs"]["vector_permutation"] = {"path": str(out_path), "rows": n}

    if not args.skip_char_shuffle:
        out_path = Path(args.out_char_shuffle)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        recs = _emit_null_char_shuffle(rows, rng=random.Random(int(args.seed) + 1), ts=ts, input_path=input_posix)
        n = _write_jsonl(out_path, recs)
        summary["outputs"]["char_shuffle"] = {"path": str(out_path), "rows": n}

    if not args.skip_token_shuffle:
        out_path = Path(args.out_token_shuffle)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        recs = _emit_null_token_shuffle(rows, rng=random.Random(int(args.seed) + 2), ts=ts, input_path=input_posix)
        n = _write_jsonl(out_path, recs)
        summary["outputs"]["token_shuffle"] = {"path": str(out_path), "rows": n}

    if not args.skip_apocrypha:
        apo_in = Path(args.apocrypha_input_jsonl)
        if not apo_in.is_absolute():
            apo_in = ROOT / apo_in
        out_path = Path(args.out_apocrypha)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        if apo_in.is_file():
            recs = _build_apocrypha_lane(apo_in, max_rows=int(args.max_rows), ts=ts)
            n = _write_jsonl(out_path, recs)
            summary["outputs"]["apocrypha_lane"] = {"path": str(out_path), "rows": n, "input": str(apo_in)}
        else:
            summary["outputs"]["apocrypha_lane"] = {"skipped": True, "reason": f"missing {apo_in}"}

    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
