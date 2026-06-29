#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add fixed sasang proxy columns to a wide B-track CSV from swarm metrics ([HYPO]).

Reads ``btrack_swarm_sasang_hypothesis_register_v1.json`` for pinned threshold (default 0.58).
Does not tune weights or threshold against OHLCV. Not a trading trigger.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER = ROOT / "docs" / "final" / "artifacts" / "btrack_swarm_sasang_hypothesis_register_v1.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "sasang_4agent_monitor_policy_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _load_threshold(register: Path, policy: Path) -> float:
    pinned = 0.58
    if register.is_file():
        reg = json.loads(register.read_text(encoding="utf-8"))
        sas = reg.get("sasang_proxy") if isinstance(reg.get("sasang_proxy"), dict) else {}
        pinned = float(sas.get("geumhwa_transition_threshold_pinned") or pinned)
    if policy.is_file():
        pol = json.loads(policy.read_text(encoding="utf-8"))
        pinned = float(pol.get("geumhwa_transition_threshold") or pinned)
    return pinned


def _parse_float(cell: str) -> float | None:
    try:
        v = float(str(cell).strip())
    except ValueError:
        return None
    if v != v:
        return None
    return v


def _proxy_row(panic: float, fomo: float, consensus: float, threshold: float) -> dict[str, str]:
    geumhwa_score = _clamp01(0.65 * panic + 0.35 * fomo)
    geumhwa_state = geumhwa_score >= threshold
    if geumhwa_state and consensus >= 0.8:
        stage = 3
        stage_label = "late"
    elif geumhwa_state:
        stage = 2
        stage_label = "mid"
    elif panic >= 0.85:
        stage = 1
        stage_label = "early"
    else:
        stage = 0
        stage_label = "stable"
    bo_myeong = _clamp01((1.0 - panic) * 0.7 + consensus * 0.3)
    return {
        "sasang_geumhwa_score": f"{geumhwa_score:.6f}",
        "sasang_geumhwa_state": "1" if geumhwa_state else "0",
        "sasang_geumhwa_threshold_used": f"{threshold:.4f}",
        "sasang_byeongjeung_stage": str(stage),
        "sasang_byeongjeung_stage_label": stage_label,
        "sasang_bo_myeong_score": f"{bo_myeong:.6f}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-csv", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-meta-json", type=Path, default=None)
    ap.add_argument("--register-json", type=Path, default=DEFAULT_REGISTER)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--panic-col", type=str, default="swarm_panic_ratio")
    ap.add_argument("--fomo-col", type=str, default="swarm_fomo_index")
    ap.add_argument("--consensus-col", type=str, default="swarm_consensus_strength")
    ap.add_argument("--utf8-bom", action="store_true")
    args = ap.parse_args()

    if not args.input_csv.is_file():
        print(f"missing input: {args.input_csv}", file=sys.stderr)
        return 2

    threshold = _load_threshold(args.register_json, args.policy_json)
    text = args.input_csv.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines:
        print("empty csv", file=sys.stderr)
        return 2
    reader = csv.DictReader(lines)
    headers = list(reader.fieldnames or [])
    extra = [
        "sasang_geumhwa_score",
        "sasang_geumhwa_state",
        "sasang_geumhwa_threshold_used",
        "sasang_byeongjeung_stage",
        "sasang_byeongjeung_stage_label",
        "sasang_bo_myeong_score",
    ]
    out_headers = headers + [c for c in extra if c not in headers]

    n_enriched = 0
    n_skipped = 0
    out_rows: list[dict[str, str]] = []
    for row in reader:
        base = {k: str(row.get(k, "") or "") for k in headers}
        panic = _parse_float(base.get(args.panic_col, ""))
        fomo = _parse_float(base.get(args.fomo_col, ""))
        consensus = _parse_float(base.get(args.consensus_col, ""))
        if panic is None or fomo is None or consensus is None:
            n_skipped += 1
            for c in extra:
                base[c] = ""
        else:
            n_enriched += 1
            base.update(_proxy_row(panic, fomo, consensus, threshold))
        out_rows.append({k: base.get(k, "") for k in out_headers})

    encoding = "utf-8-sig" if args.utf8_bom else "utf-8"
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="", encoding=encoding) as fp:
        w = csv.DictWriter(fp, fieldnames=out_headers)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    meta = {
        "schema": "btrack_wide_sasang_proxy_enrich_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "geumhwa_transition_threshold_used": threshold,
        "formula_version": "swarm_sasang_proxy_v1",
        "counts": {
            "n_rows": len(out_rows),
            "n_enriched": n_enriched,
            "n_skipped_missing_swarm": n_skipped,
        },
        "inputs": {"input_csv": str(args.input_csv.resolve())},
        "out_csv": str(args.out_csv.resolve()),
    }
    meta_path = args.out_meta_json or args.out_csv.with_suffix(".enrich.meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE rows={len(out_rows)} enriched={n_enriched} csv={args.out_csv.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
