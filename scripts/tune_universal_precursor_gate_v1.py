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


def _decision(clusters: list[dict[str, Any]], min_size: int, min_coh: float, min_clusters: int) -> dict[str, Any]:
    kept = [
        c
        for c in clusters
        if int(c.get("size") or 0) >= min_size
        and float(c.get("coherence_score_0_1") or 0.0) >= min_coh
    ]
    return {
        "min_cluster_size": int(min_size),
        "min_coherence_0_1": float(min_coh),
        "min_clusters_required": int(min_clusters),
        "kept_cluster_count": len(kept),
        "kept_total_verses": int(sum(int(c.get("size") or 0) for c in kept)),
        "decision": "GO_RESEARCH" if len(kept) >= int(min_clusters) else "HOLD_RESEARCH",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Tune stricter gate for universal precursor clusters.")
    ap.add_argument(
        "--digest-json",
        default="docs/final/artifacts/universal_precursor_cluster_digest_v1_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/universal_precursor_gate_tuning_v1_latest.json",
    )
    args = ap.parse_args()

    src = _resolve(args.digest_json)
    out = _resolve(args.output_json)
    d = _read_json(src)
    clusters = d.get("clusters") if isinstance(d.get("clusters"), list) else []

    size_grid = [10, 20, 30, 40, 50]
    coh_grid = [0.990, 0.993, 0.995, 0.997]
    min_clusters_required = 6
    rows: list[dict[str, Any]] = []
    for s in size_grid:
        for c in coh_grid:
            rows.append(_decision(clusters, s, c, min_clusters_required))

    go_rows = [r for r in rows if r["decision"] == "GO_RESEARCH"]
    # "Most conservative GO": highest size, then highest coherence.
    go_rows.sort(key=lambda r: (r["min_cluster_size"], r["min_coherence_0_1"]), reverse=True)
    recommended = go_rows[0] if go_rows else None

    out_doc = {
        "schema": "universal_precursor_gate_tuning_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "a_track_binding_forbidden": True,
        "source_digest_json": str(src),
        "baseline_gate_decision": d.get("gate_decision"),
        "sweep": rows,
        "recommended_strict_gate": recommended,
        "note": "Recommendation chooses most conservative GO_RESEARCH point on the sweep grid.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(json.dumps({"recommended": recommended}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
