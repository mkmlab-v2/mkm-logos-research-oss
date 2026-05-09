#!/usr/bin/env python3
"""Extract best archetype candidate from refit output into standalone matrix file."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_REFIT = ART / "logos_fractal_archetype_refit_latest.json"
DEFAULT_BASE_MATRIX = ART / "logos_fractal_archetype_4d_matrix_v1.json"
DEFAULT_OUT = ART / "logos_fractal_archetype_4d_matrix_refit_candidate_v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build refit archetype candidate matrix.")
    ap.add_argument("--refit-json", type=Path, default=DEFAULT_REFIT)
    ap.add_argument("--base-matrix-json", type=Path, default=DEFAULT_BASE_MATRIX)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    refit = _load_json(args.refit_json)
    base = _load_json(args.base_matrix_json)
    best = (refit.get("best") or {})
    best_arch = best.get("archetypes") or []

    out = dict(base)
    out["schema"] = "logos_fractal_archetype_4d_matrix_refit_candidate_v1"
    out["generated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out["source_track"] = "B"
    out["hypothesis_tag"] = "[HYPO]"
    out["research_only"] = True
    out["auto_bind_to_atrack_forbidden"] = True
    out["candidate_meta"] = {
        "from_refit_json": str(args.refit_json).replace("\\", "/"),
        "baseline_corr_resonance_vs_non_synthetic_hit_rate": (refit.get("baseline") or {}).get(
            "corr_resonance_vs_non_synthetic_hit_rate"
        ),
        "candidate_corr_resonance_vs_non_synthetic_hit_rate": best.get(
            "corr_resonance_vs_non_synthetic_hit_rate"
        ),
    }
    if best_arch:
        out["archetypes"] = best_arch

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "archetype_count": len(out.get("archetypes", []))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

