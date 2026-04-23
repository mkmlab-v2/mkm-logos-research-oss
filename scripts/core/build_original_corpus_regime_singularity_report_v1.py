#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_WS = Path(__file__).resolve().parents[2]
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

AXES = ("S", "L", "K", "M")
REGIMES = ("bull_pump", "sideways_accumulation", "bear_trend", "capitulation")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _load_regimes(path: Path) -> dict[str, dict[str, float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, float]] = {}
    for rid in REGIMES:
        u4 = (((data.get("regimes") or {}).get(rid) or {}).get("fingerprint") or {}).get("unified_4d_vector") or {}
        vec = {k: float(u4.get(k, 0.0)) for k in AXES}
        n = math.sqrt(sum(vec[k] ** 2 for k in AXES))
        if n <= 0.0:
            out[rid] = {k: 0.0 for k in AXES}
        else:
            out[rid] = {k: vec[k] / n for k in AXES}
    return out


def _extract_text(row: dict[str, Any]) -> str:
    for k in ("original_text", "text", "content"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _normalize_original_script_text(text: str) -> str:
    # Keep only Hebrew/Greek script letters and spaces for pure original-language scoring.
    t = re.sub(r"[^\u0590-\u05FF\u0370-\u03FF\u1F00-\u1FFF\s]", " ", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _dot(a: dict[str, float], b: dict[str, float]) -> float:
    return float(sum(a[k] * b[k] for k in AXES))


def _top_push(bag: list[dict[str, Any]], row: dict[str, Any], top_n: int) -> None:
    bag.append(row)
    bag.sort(key=lambda x: float(x["score"]), reverse=True)
    if len(bag) > top_n:
        del bag[top_n:]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build regime resonance singularity report from original-only corpora.")
    ap.add_argument("--dss-jsonl", default="data/logos/manuscripts/dss_original_only_latest.jsonl")
    ap.add_argument("--apocrypha-jsonl", default="data/logos/manuscripts/apocrypha_original_only_latest.jsonl")
    ap.add_argument(
        "--canon-only",
        action="store_true",
        help="Scan canon lane only (skip DSS/apocrypha loads). Requires --canon-jsonl.",
    )
    ap.add_argument(
        "--canon-jsonl",
        default="",
        help="Optional canonical verse stream (e.g. data/logos/verse_decoded_v2.jsonl). Rows use lane label 'canon'.",
    )
    ap.add_argument("--regime-map-json", default="data/regimes/regime_map_btc_ext.json")
    ap.add_argument("--top-n", type=int, default=50)
    ap.add_argument("--output-json", default="docs/final/artifacts/original_corpus_regime_singularity_report_v1.json")
    args = ap.parse_args()

    regimes = _load_regimes(Path(args.regime_map_json))
    dss_rows: list[dict[str, Any]] = []
    apo_rows: list[dict[str, Any]] = []
    rows: list[tuple[str, dict[str, Any]]] = []
    if not args.canon_only:
        dss_rows = _read_jsonl(Path(args.dss_jsonl))
        apo_rows = _read_jsonl(Path(args.apocrypha_jsonl))
        rows.extend([("dss", r) for r in dss_rows])
        rows.extend([("apocrypha", r) for r in apo_rows])
    canon_opt = (args.canon_jsonl or "").strip()
    canon_rows: list[dict[str, Any]] = []
    if args.canon_only and not canon_opt:
        print("error: --canon-only requires --canon-jsonl", file=sys.stderr)
        return 2
    if canon_opt:
        canon_path = Path(canon_opt)
        if not canon_path.is_file():
            print(f"error: --canon-jsonl not found: {canon_path}", file=sys.stderr)
            return 2
        canon_rows = _read_jsonl(canon_path)
        rows.extend([("canon", r) for r in canon_rows])

    top_by_regime: dict[str, list[dict[str, Any]]] = {r: [] for r in REGIMES}
    top_global: list[dict[str, Any]] = []
    top_canon_only: list[dict[str, Any]] = []
    scanned = 0

    for lane, row in rows:
        txt = _normalize_original_script_text(_extract_text(row))
        if not txt:
            continue
        meta = build_gematria_metadata(raw_text=txt, compressed_text=txt, reconstructed_text=txt)
        bridge = build_gematria_4d_bridge(gematria_metadata=meta)
        v = bridge.get("vector_4d") or {}
        vec = {k: float(v.get(k, 0.25)) for k in AXES}
        scores = {rid: _dot(vec, regimes[rid]) for rid in REGIMES}
        best_regime = max(REGIMES, key=lambda r: scores[r])
        sorted_scores = sorted(scores.values(), reverse=True)
        margin = sorted_scores[0] - (sorted_scores[1] if len(sorted_scores) > 1 else 0.0)

        rid = str(row.get("id") or row.get("verse_id") or row.get("source_ref") or f"{lane}:{scanned+1}")
        base = {
            "row_id": rid,
            "lane": lane,
            "best_regime": best_regime,
            "score": float(scores[best_regime]),
            "margin_vs_second": float(margin),
            "state16": bridge.get("state16"),
            "text_preview": txt[:120],
        }
        _top_push(top_by_regime[best_regime], base, int(args.top_n))
        _top_push(top_global, base, int(args.top_n))
        if lane == "canon":
            _top_push(top_canon_only, base, int(args.top_n))
        scanned += 1

    out = {
        "schema": "original_corpus_regime_singularity_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "inputs": {
            "dss_jsonl": args.dss_jsonl,
            "apocrypha_jsonl": args.apocrypha_jsonl,
            "canon_jsonl": canon_opt or None,
            "canon_only": bool(args.canon_only),
            "regime_map_json": args.regime_map_json,
            "top_n": int(args.top_n),
        },
        "counts": {
            "dss_rows": len(dss_rows),
            "apocrypha_rows": len(apo_rows),
            "canon_rows": len(canon_rows),
            "rows_scanned": scanned,
        },
        "top_global_singularities": top_global,
        "top_canon_singularities": top_canon_only if canon_rows else [],
        "top_by_best_regime": top_by_regime,
        "note": "B-track geometric resonance scan over original-only corpora; non-trading. top_canon_singularities ranks canon lane only (verse_decoded_v2 when passed via --canon-jsonl).",
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
