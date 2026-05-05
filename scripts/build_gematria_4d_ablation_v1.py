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
    ap = argparse.ArgumentParser(description="Build gematria 4D ablation comparison report.")
    ap.add_argument("--coupling-json", default="docs/final/artifacts/gematria_4d_coupling_latest.json")
    ap.add_argument("--resonance-json", default="docs/final/artifacts/atom_resonance_report_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/gematria_4d_ablation_latest.json")
    args = ap.parse_args()

    cp = resolve(args.coupling_json)
    rp = resolve(args.resonance_json)
    op = resolve(args.output_json)
    if not cp.is_file():
        raise SystemExit(f"missing coupling json: {cp}")
    if not rp.is_file():
        raise SystemExit(f"missing resonance json: {rp}")

    c = load(cp)
    r = load(rp)
    mean_coupling = float(((c.get("summary") or {}).get("mean_coupling_strength", 0.0) or 0.0))
    base_resonance = float(r.get("resonance_score", 0.0) or 0.0)

    with_4d = clamp01((0.6 * base_resonance) + (0.4 * mean_coupling))
    without_4d = clamp01(0.95 * base_resonance)
    delta = with_4d - without_4d

    out = {
        "schema": "gematria_4d_ablation_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "snapshot": {
            "base_resonance_score": round(base_resonance, 6),
            "mean_4d_coupling_strength": round(mean_coupling, 6),
            "score_with_4d": round(with_4d, 6),
            "score_without_4d": round(without_4d, 6),
            "delta_with_minus_without": round(delta, 6),
        },
        "policy_gate": {
            "allow_execution_trigger": False,
            "require_fail_boundary_gate": True,
            "require_research_only_lane": True,
        },
        "sources": {"coupling_json": str(cp), "resonance_json": str(rp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

