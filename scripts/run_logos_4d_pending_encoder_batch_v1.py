#!/usr/bin/env python3
"""B-track: LogosEncoder re-encode for verses where jsonl+pipeline4 are both fallback."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.core.logos_corpus_loader import verse_logos_text
from tools.core.logos_encoder_gpu import LogosEncoder
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d

JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
PENDING = ROOT / "reports/logos_4d_pending_encoder_v1_latest.json"
OUT_JSONL = ROOT / "reports/logos_4d_encoder_reencode_v1_latest.jsonl"
OUT_META = ROOT / "reports/logos_4d_encoder_reencode_v1_latest.json"
FALLBACK_KEY = (0.25, 0.25, 0.25, 0.25)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _is_fallback(v: dict[str, float], places: int) -> bool:
    key = tuple(round(v[k], places) for k in ("S", "L", "K", "M"))
    return key == FALLBACK_KEY


def _tensor_to_4d(t) -> dict[str, float]:
    row = t.squeeze().detach().cpu().tolist()
    return coerce_4d({"S": row[0], "L": row[1], "K": row[2], "M": row[3]})


def _load_pending_ids(path: Path) -> list[str]:
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        ids = [str(v.get("verse_id") or "") for v in doc.get("verses") or [] if v.get("verse_id")]
        if ids:
            return ids
    return []


def _load_jsonl_rows(path: Path, want: set[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid in want:
                out[vid] = row
    return out


def run_batch(*, jsonl: Path, pending_json: Path, places: int) -> tuple[list[dict], dict]:
    pending_ids = _load_pending_ids(pending_json)
    if not pending_ids:
        want: set[str] = set()
        with jsonl.open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                v = coerce_4d(row.get("vector_4d") or row.get("unified_4d_vector") or {})
                if _is_fallback(v, places):
                    vid = str(row.get("verse_id") or "")
                    if vid:
                        want.add(vid)
        pending_ids = sorted(want)
    rows_by_id = _load_jsonl_rows(jsonl, set(pending_ids))
    enc = LogosEncoder().eval()
    out_rows: list[dict] = []
    still_fallback = 0
    for vid in pending_ids:
        rec = rows_by_id.get(vid)
        if not rec:
            continue
        text = verse_logos_text(rec) or str(rec.get("text") or rec.get("original_text") or "")
        vec = _tensor_to_4d(enc.encode_text_to_logos_embedding(text))
        fb = _is_fallback(vec, places)
        if fb:
            still_fallback += 1
        out_rows.append(
            {
                "verse_id": vid,
                "encoder": "LogosEncoder_sha256_projection_v1",
                "hypothesis_tier": "B",
                "research_only": True,
                "reencode_method": "logos_encoder_text_hash",
                "text_chars": len(text),
                "vector_4d_before": {k: 0.25 for k in ("S", "L", "K", "M")},
                "vector_4d_after": {k: round(vec[k], 6) for k in vec},
                "still_fallback_after_encode": fb,
            }
        )
    meta = {
        "requested": len(pending_ids),
        "encoded": len(out_rows),
        "still_fallback_after_encode": still_fallback,
    }
    return out_rows, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, default=JSONL)
    ap.add_argument("--pending-json", type=Path, default=PENDING)
    ap.add_argument("--out-jsonl", type=Path, default=OUT_JSONL)
    ap.add_argument("--out-meta", type=Path, default=OUT_META)
    ap.add_argument("--round-places", type=int, default=4)
    args = ap.parse_args()
    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": "missing jsonl"}))
        return 2
    rows, counts = run_batch(jsonl=args.jsonl, pending_json=args.pending_json, places=max(1, args.round_places))
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    meta = {
        "schema": "logos_4d_encoder_reencode_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "inputs": {"jsonl": _rel(args.jsonl), "pending_json": _rel(args.pending_json)},
        "outputs": {"jsonl": _rel(args.out_jsonl)},
        "counts": counts,
        "note": "LogosEncoder uses deterministic sha256→4D projection; not production gematria pipeline.",
    }
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **counts, "out_jsonl": str(args.out_jsonl)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
