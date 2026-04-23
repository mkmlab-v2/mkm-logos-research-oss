#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_WS = Path(__file__).resolve().parents[2]
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.core.build_original_corpus_regime_singularity_report_v1 import (
    _dot,
    _extract_text,
    _load_regimes,
    _normalize_original_script_text,
)
from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

REGIMES = ("bull_pump", "sideways_accumulation", "bear_trend", "capitulation")
AXES = ("S", "L", "K", "M")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Balanced regime singularity report with per-regime quota.")
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
        help="Optional canonical verse JSONL (e.g. verse_decoded_v2.jsonl). Lane label: canon.",
    )
    ap.add_argument("--regime-map-json", required=True)
    ap.add_argument("--quota-per-regime", type=int, default=12)
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()

    dss_rows: list[dict[str, Any]] = []
    apo_rows: list[dict[str, Any]] = []
    if not args.canon_only:
        dss_rows = _read_jsonl(Path(args.dss_jsonl))
        apo_rows = _read_jsonl(Path(args.apocrypha_jsonl))
    canon_opt = (args.canon_jsonl or "").strip()
    canon_rows: list[dict[str, Any]] = []
    if args.canon_only and not canon_opt:
        print("error: --canon-only requires --canon-jsonl", file=sys.stderr)
        return 2
    if canon_opt:
        cp = Path(canon_opt)
        if not cp.is_file():
            print(f"error: --canon-jsonl not found: {cp}", file=sys.stderr)
            return 2
        canon_rows = _read_jsonl(cp)
    regime_vectors = _load_regimes(Path(args.regime_map_json))
    quota = int(args.quota_per_regime)

    per_regime_rankings: dict[str, list[dict[str, Any]]] = {r: [] for r in REGIMES}
    scanned = 0

    lane_rows: list[tuple[str, list[dict[str, Any]]]] = [
        ("dss", dss_rows),
        ("apocrypha", apo_rows),
    ]
    if canon_rows:
        lane_rows.append(("canon", canon_rows))

    for lane, rows in lane_rows:
        for row in rows:
            txt = _normalize_original_script_text(_extract_text(row))
            if not txt:
                continue
            scanned += 1
            row_id = str(
                row.get("id") or row.get("verse_id") or row.get("row_id") or f"{lane}_unknown"
            )
            meta = build_gematria_metadata(raw_text=txt, compressed_text=txt, reconstructed_text=txt)
            bridge = build_gematria_4d_bridge(gematria_metadata=meta)
            vv = bridge.get("vector_4d") or {}
            vec = {k: float(vv.get(k, 0.25)) for k in AXES}
            state16 = bridge.get("state16")
            text_preview = txt[:120]
            regime_scores = {r: _dot(vec, regime_vectors[r]) for r in REGIMES}
            for regime in REGIMES:
                per_regime_rankings[regime].append(
                    {
                        "row_id": row_id,
                        "lane": lane,
                        "target_regime": regime,
                        "score": float(regime_scores[regime]),
                        "state16": state16,
                        "text_preview": text_preview,
                    }
                )

    per_regime_top: dict[str, list[dict[str, Any]]] = {}
    selected_ids: set[str] = set()
    balanced_rows: list[dict[str, Any]] = []

    for regime in REGIMES:
        ranked = sorted(per_regime_rankings[regime], key=lambda x: x["score"], reverse=True)
        top = ranked[:quota]
        per_regime_top[regime] = top
        for item in top:
            if item["row_id"] in selected_ids:
                continue
            selected_ids.add(item["row_id"])
            balanced_rows.append(item)

    counts = {r: len(per_regime_top[r]) for r in REGIMES}
    out = {
        "schema": "original_corpus_regime_singularity_balanced_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "inputs": {
            "dss_jsonl": args.dss_jsonl,
            "apocrypha_jsonl": args.apocrypha_jsonl,
            "canon_jsonl": canon_opt or None,
            "canon_only": bool(args.canon_only),
            "regime_map_json": args.regime_map_json,
            "quota_per_regime": quota,
        },
        "counts": {
            "dss_rows": len(dss_rows),
            "apocrypha_rows": len(apo_rows),
            "canon_rows": len(canon_rows),
            "rows_scanned": scanned,
            "balanced_unique_rows": len(balanced_rows),
        },
        "quota_counts": counts,
        "per_regime_top": per_regime_top,
        "balanced_union_top": sorted(balanced_rows, key=lambda x: x["score"], reverse=True),
        "note": "B-track balanced extraction using independent regime quotas; non-trading.",
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
