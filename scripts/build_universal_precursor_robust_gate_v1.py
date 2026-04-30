#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def _apply(clusters: list[dict[str, Any]], min_size: int, min_coh: float) -> int:
    return sum(
        1
        for c in clusters
        if int(c.get("size") or 0) >= int(min_size)
        and float(c.get("coherence_score_0_1") or 0.0) >= float(min_coh)
    )


def _split_even_odd(clusters: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    even: list[dict[str, Any]] = []
    odd: list[dict[str, Any]] = []
    for c in clusters:
        rep = str(c.get("representative_verse_id") or "")
        if sum(ord(ch) for ch in rep) % 2 == 0:
            even.append(c)
        else:
            odd.append(c)
    return even, odd


def main() -> int:
    ap = argparse.ArgumentParser(description="Find robust strict gate that survives split checks.")
    ap.add_argument(
        "--digest-json",
        default="docs/final/artifacts/universal_precursor_cluster_digest_v1_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/universal_precursor_robust_gate_v1_latest.json",
    )
    args = ap.parse_args()

    digest = _read_json(_resolve(args.digest_json))
    clusters = digest.get("clusters") if isinstance(digest.get("clusters"), list) else []
    even, odd = _split_even_odd(clusters)

    size_grid = [50, 45, 40, 35, 30, 25, 20]
    coh_grid = [0.995, 0.994, 0.993, 0.992, 0.99]
    min_clusters_required_grid = [6, 5, 4]

    viable: list[dict[str, Any]] = []
    for ms in size_grid:
        for mc in coh_grid:
            full_k = _apply(clusters, ms, mc)
            even_k = _apply(even, ms, mc)
            odd_k = _apply(odd, ms, mc)
            for req in min_clusters_required_grid:
                ok = full_k >= req and even_k >= req and odd_k >= req
                row = {
                    "min_cluster_size": ms,
                    "min_coherence_0_1": mc,
                    "min_clusters_required": req,
                    "full_kept_clusters": full_k,
                    "even_kept_clusters": even_k,
                    "odd_kept_clusters": odd_k,
                    "robust_ok": ok,
                }
                if ok:
                    viable.append(row)

    # Most conservative robust gate: highest size, highest coherence, then highest req.
    viable.sort(
        key=lambda r: (
            r["min_cluster_size"],
            r["min_coherence_0_1"],
            r["min_clusters_required"],
        ),
        reverse=True,
    )
    recommended = viable[0] if viable else None

    out_doc = {
        "schema": "universal_precursor_robust_gate_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "a_track_binding_forbidden": True,
        "source_digest_json": str(_resolve(args.digest_json)),
        "recommended_robust_gate": recommended,
        "viable_count": len(viable),
        "viable_top10": viable[:10],
        "note": "Robust gate passes full/even/odd split simultaneously.",
    }
    out_path = _resolve(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(json.dumps({"recommended": recommended}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
