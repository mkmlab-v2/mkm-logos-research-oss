#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build 4D gematria coupling report from symbolic bridge.")
    ap.add_argument("--symbolic-json", default="docs/final/artifacts/symbolic_topology_insight_latest.json")
    ap.add_argument("--bridge-json", default="docs/final/artifacts/scholarly_symbol_bridge_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/gematria_4d_coupling_latest.json")
    args = ap.parse_args()

    sp = resolve(args.symbolic_json)
    bp = resolve(args.bridge_json)
    op = resolve(args.output_json)
    if not sp.is_file():
        raise SystemExit(f"missing symbolic json: {sp}")
    if not bp.is_file():
        raise SystemExit(f"missing bridge json: {bp}")

    s = load(sp)
    b = load(bp)
    axes = s.get("symbolic_topology_axes") if isinstance(s.get("symbolic_topology_axes"), dict) else {}
    bridge_rows = b.get("bridge_rows") if isinstance(b.get("bridge_rows"), list) else []

    axis_s = float(axes.get("self_grounding_vs_transcendence", 0.0) or 0.0)
    axis_l = float(axes.get("boundary_obedience_vs_autonomy", 0.0) or 0.0)
    axis_k = float(axes.get("epistemic_acceleration", 0.0) or 0.0)
    axis_m = float(axes.get("desire_intensity", 0.0) or 0.0)

    points: list[dict[str, Any]] = []
    for row in bridge_rows:
        if not isinstance(row, dict):
            continue
        pos = int(row.get("position", 0) or 0)
        conf = float(row.get("source_confidence", 0.0) or 0.0)
        atom_id = str(row.get("atom_id", ""))
        motif = str(row.get("motif_label", ""))
        # 4D projection: deterministic coordinate encoding with confidence scaling.
        p_s = clamp01((axis_s * 0.65) + (conf * 0.35))
        p_l = clamp01((axis_l * 0.60) + (pos / 10.0))
        p_k = clamp01((axis_k * 0.70) + (conf * 0.30))
        p_m = clamp01((axis_m * 0.70) + (0.05 if "desire" in motif else 0.0))
        points.append(
            {
                "position": pos,
                "atom_id": atom_id,
                "motif_label": motif,
                "vector_4d": {"S": round(p_s, 6), "L": round(p_l, 6), "K": round(p_k, 6), "M": round(p_m, 6)},
                "coupling_strength": round(clamp01((p_s + p_l + p_k + p_m) / 4.0), 6),
            }
        )

    mean_coupling = sum(float(p.get("coupling_strength", 0.0)) for p in points) / max(len(points), 1)
    out = {
        "schema": "gematria_4d_coupling_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "seed_symbol": s.get("seed_symbol"),
        "projection_points": points,
        "summary": {
            "point_count": len(points),
            "mean_coupling_strength": round(clamp01(mean_coupling), 6),
            "execution_policy": "analysis_only_non_trigger",
        },
        "sources": {"symbolic_json": str(sp), "bridge_json": str(bp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

