#!/usr/bin/env python3
"""Chronology epoch permutation control: node-date clustering vs null (B-track, research only).

Supports H-BC1, H-AX1, and other sidecars with epoch_window_bce + date_bce_mid nodes.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIDECAR = ROOT / "docs/final/artifacts/biblical_history_h_bc1_bronze_collapse_chronology_sidecar_v1.json"


def _default_out_for_hypothesis(hypothesis_id: str, *, era: str | None = None) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", hypothesis_id.lower()).strip("_")
    mixed_era_ids = frozenset({"H-AR1", "H-DSS1"})
    era_suffix = f"_{era}" if era == "ce" and hypothesis_id in mixed_era_ids else ""
    return ROOT / f"reports/biblical_history_{slug}{era_suffix}_epoch_permutation_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_era(sidecar: dict[str, Any], *, force: str | None = None) -> str:
    if force in ("bce", "ce"):
        return force
    hypothesis_id = str(sidecar.get("hypothesis_id", ""))
    if hypothesis_id == "H-AR1" and isinstance(sidecar.get("epoch_window_bce"), dict):
        return "bce"
    if isinstance(sidecar.get("epoch_window_ce"), dict) and not isinstance(sidecar.get("epoch_window_bce"), dict):
        return "ce"
    nodes = sidecar.get("nodes")
    if isinstance(nodes, list):
        ce_count = sum(1 for n in nodes if isinstance(n, dict) and isinstance(n.get("date_ce_mid"), int))
        bce_count = sum(1 for n in nodes if isinstance(n, dict) and isinstance(n.get("date_bce_mid"), int))
        if ce_count >= bce_count and ce_count > 0:
            return "ce"
    return "bce"


def _node_mids(sidecar: dict[str, Any], era: str) -> list[int]:
    nodes = sidecar.get("nodes")
    if not isinstance(nodes, list):
        return []
    key = "date_ce_mid" if era == "ce" else "date_bce_mid"
    out: list[int] = []
    for n in nodes:
        if isinstance(n, dict) and isinstance(n.get(key), int):
            out.append(int(n[key]))
    return out


def _span_bce(mids: list[int]) -> int | None:
    if len(mids) < 2:
        return None
    return max(mids) - min(mids)


def _count_in_window(mids: list[int], start: int, end: int) -> int:
    lo, hi = min(start, end), max(start, end)
    return sum(1 for m in mids if lo <= m <= hi)


def _permute_once(n: int, pool_lo: int, pool_hi: int, rng: random.Random) -> list[int]:
    return [rng.randint(pool_lo, pool_hi) for _ in range(n)]


def _max_in_sliding_window(mids: list[int], pool_lo: int, pool_hi: int, window_width: int) -> int:
    if not mids or window_width <= 0:
        return 0
    best = 0
    for start in range(pool_lo, pool_hi - window_width + 1):
        end = start + window_width
        cnt = _count_in_window(mids, start, end)
        if cnt > best:
            best = cnt
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description="Biblical history epoch permutation clustering control.")
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--output-json", type=Path, default=None)
    ap.add_argument("--permutation-repeats", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--null-pool-lo-bce", type=int, default=None)
    ap.add_argument("--null-pool-hi-bce", type=int, default=None)
    ap.add_argument("--era", choices=("bce", "ce"), default=None, help="Force BCE or CE epoch (mixed sidecars).")
    args = ap.parse_args()

    if not args.sidecar_json.is_file():
        raise SystemExit(f"missing sidecar: {args.sidecar_json}")

    sidecar = _load(args.sidecar_json)
    hypothesis_id = str(sidecar.get("hypothesis_id", "H-UNKNOWN"))
    era = _resolve_era(sidecar, force=args.era)
    output_json = args.output_json or _default_out_for_hypothesis(hypothesis_id, era=era)
    if era == "ce":
        epoch = sidecar.get("epoch_window_ce") if isinstance(sidecar.get("epoch_window_ce"), dict) else {}
        window_start = int(epoch.get("start", 1450))
        window_end = int(epoch.get("end", 2020))
    else:
        epoch = sidecar.get("epoch_window_bce") if isinstance(sidecar.get("epoch_window_bce"), dict) else {}
        window_start = int(epoch.get("start", -1250))
        window_end = int(epoch.get("end", -1150))

    observed_mids = _node_mids(sidecar, era)
    n = len(observed_mids)
    if n < 2:
        raise SystemExit(f"sidecar needs at least 2 nodes with date_{era}_mid")

    observed_span = _span_bce(observed_mids)
    observed_in_window = _count_in_window(observed_mids, window_start, window_end)
    window_width = abs(window_end - window_start)

    rng = random.Random(args.seed)
    perm_spans: list[int] = []
    perm_in_window: list[int] = []
    perm_sliding_max: list[int] = []
    perm_random_window: list[int] = []
    if era == "ce":
        if hypothesis_id == "H-PR1":
            pool_lo = 1000
        elif hypothesis_id == "H-AR1":
            pool_lo = 1800
        else:
            pool_lo = 1400
        pool_hi = 2020
    elif args.null_pool_lo_bce is not None:
        pool_lo = args.null_pool_lo_bce
    elif hypothesis_id == "H-AR1":
        pool_lo = -3500
    elif hypothesis_id == "H-AX1":
        pool_lo = -1500
    else:
        pool_lo = -2000
    if era != "ce":
        if args.null_pool_hi_bce is not None:
            pool_hi = args.null_pool_hi_bce
        elif hypothesis_id == "H-AR1":
            pool_hi = -800
        elif hypothesis_id == "H-AX1":
            pool_hi = -100
        else:
            pool_hi = -800
    for _ in range(max(1, args.permutation_repeats)):
        draw = _permute_once(n, pool_lo, pool_hi, rng)
        span = _span_bce(draw)
        if span is not None:
            perm_spans.append(span)
        perm_in_window.append(_count_in_window(draw, window_start, window_end))
        perm_sliding_max.append(_max_in_sliding_window(draw, pool_lo, pool_hi, window_width))
        if pool_hi - pool_lo > window_width:
            ws = rng.randint(pool_lo, pool_hi - window_width)
            perm_random_window.append(_count_in_window(draw, ws, ws + window_width))

    span_le_observed = sum(1 for s in perm_spans if observed_span is not None and s <= observed_span)
    window_ge_observed = sum(1 for c in perm_in_window if c >= observed_in_window)
    sliding_ge_observed = sum(1 for c in perm_sliding_max if c >= observed_in_window)
    random_window_ge_observed = sum(1 for c in perm_random_window if c >= observed_in_window)
    repeats = len(perm_spans) or 1
    rw_repeats = len(perm_random_window) or 1

    schema_slug = re.sub(r"[^a-z0-9]+", "_", hypothesis_id.lower()).strip("_")
    payload = {
        "schema": f"biblical_history_{schema_slug}_epoch_permutation_v1",
        "hypothesis_id": hypothesis_id,
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "era": era,
        "inputs": {
            "sidecar_json": str(args.sidecar_json),
            "permutation_repeats": args.permutation_repeats,
            "seed": args.seed,
            "null_pool": [pool_lo, pool_hi],
            f"epoch_window_{era}": [window_start, window_end],
        },
        "observed": {
            "node_count": n,
            f"date_{era}_mids": observed_mids,
            f"span_{era}_years": observed_span,
            "nodes_in_epoch_window": observed_in_window,
        },
        "null_distribution": {
            f"span_{era}_mean": round(sum(perm_spans) / repeats, 3),
            f"span_{era}_median": sorted(perm_spans)[repeats // 2],
            "in_window_mean": round(sum(perm_in_window) / repeats, 3),
            "sliding_window_max_mean": round(sum(perm_sliding_max) / repeats, 3),
            "random_window_count_mean": round(sum(perm_random_window) / rw_repeats, 3) if perm_random_window else None,
        },
        "permutation_p_values": {
            "span_clustering_le_observed": round(span_le_observed / repeats, 6),
            "in_window_ge_observed": round(window_ge_observed / repeats, 6),
            "sliding_window_max_ge_observed": round(sliding_ge_observed / repeats, 6),
            "random_window_count_ge_observed": round(random_window_ge_observed / rw_repeats, 6) if perm_random_window else None,
        },
        "sliding_window_null": {
            f"window_width_{era}_years": window_width,
            "observed_nodes_in_fixed_corridor": observed_in_window,
            "null_model": "uniform_draw_then_max_count_in_any_width_W_window_across_pool",
        },
        "interpretation": {
            "span_clustering": (
                "Lower p => observed collapse nodes are unusually tight vs random BCE draws."
            ),
            "in_window_density": (
                "Fraction of uniform null draws matching fixed corridor density."
            ),
            "sliding_window": (
                "Fraction of null draws whose best width-W window still reaches observed corridor count."
            ),
            "status": "research_only_not_promotion_proof",
        },
        "fact_lock_notice": "Symbolic archaeology prior only; not Track A or live trading gate.",
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output_json), "hypothesis_id": hypothesis_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
