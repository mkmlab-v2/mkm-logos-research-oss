# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Compare Week-22 E1 baseline, conservative, and aggressive variants.
# Keywords: track_a, week22, e1, ab, compare
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_staged_guard_unlock_sweep_v1.json"
CONSERVATIVE = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_staged_guard_unlock_sweep_conservative_v1.json"
AGGRESSIVE = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_staged_guard_unlock_sweep_aggressive_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_e1_ab_compare_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _best_metrics(doc: dict[str, Any]) -> dict[str, float]:
    runs = doc.get("runs") or []
    if not runs:
        return {
            "saving": 0.0,
            "jaccard": 0.0,
            "integrity": 0.0,
        }
    best = runs[0]
    metrics = best.get("metrics") or {}
    return {
        "saving": float(metrics.get("global_token_saving_rate", 0.0)),
        "jaccard": float(metrics.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "integrity": float(metrics.get("avg_sensitive_integrity", 0.0)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", type=Path, default=BASELINE)
    ap.add_argument("--conservative", type=Path, default=CONSERVATIVE)
    ap.add_argument("--aggressive", type=Path, default=AGGRESSIVE)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    base = _load(args.baseline if args.baseline.is_absolute() else ROOT / args.baseline)
    cons = _load(args.conservative if args.conservative.is_absolute() else ROOT / args.conservative)
    aggr = _load(args.aggressive if args.aggressive.is_absolute() else ROOT / args.aggressive)

    rows: list[tuple[str, dict[str, Any]]] = [
        ("baseline", base),
        ("conservative", cons),
        ("aggressive", aggr),
    ]

    summary: list[dict[str, Any]] = []
    for label, doc in rows:
        best = _best_metrics(doc)
        summary.append(
            {
                "variant": label,
                "decision": doc.get("decision"),
                "viable_count": int(doc.get("viable_count", 0)),
                "best_saving": best["saving"],
                "best_jaccard": best["jaccard"],
                "best_integrity": best["integrity"],
            }
        )

    out_doc = {
        "schema": "track_a_week22_e1_ab_compare_v1",
        "generated_at_utc": _now_utc(),
        "variants": summary,
    }
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
