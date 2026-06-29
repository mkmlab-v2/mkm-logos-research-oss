# @MKM12-METADATA
# Type: Logic
# Purpose: Research ablation — lens WF beat_bull gt vs gte without re-running grid
# Keywords: prophecy, ablation, beat_bull, research_only
#!/usr/bin/env python3
"""Compare lens walk-forward beat_bull policies (gt vs gte) on an existing WF JSON.

B-track / [HYPO] / research_only — does not change production gate defaults.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports" / "prophecy_lens_beat_bull_policy_ablation_v1_latest.json"
MIN_BEAT_FRAC_STRICT = 0.5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SystemExit(f"invalid json: {path}")
    return doc


def _frac_from_folds(folds: list[dict[str, Any]], key: str) -> float | None:
    if not folds:
        return None
    hits = sum(1 for f in folds if bool(f.get(key)))
    return round(hits / len(folds), 6)


def _frac_from_accuracy(folds: list[dict[str, Any]], *, gte: bool) -> float | None:
    if not folds:
        return None
    n = 0
    for f in folds:
        test = f.get("test") if isinstance(f.get("test"), dict) else {}
        acc = float(test.get("accuracy") or 0.0)
        bull = float(test.get("always_bull_control") or 0.0)
        ok = acc >= bull if gte else acc > bull
        if ok:
            n += 1
    return round(n / len(folds), 6)


def main() -> int:
    ap = argparse.ArgumentParser(description="Lens WF beat_bull gt vs gte ablation (research).")
    ap.add_argument("--walkforward-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-beat-frac", type=float, default=MIN_BEAT_FRAC_STRICT)
    args = ap.parse_args()

    if not args.walkforward_json.is_file():
        print(f"Missing: {args.walkforward_json}", flush=True)
        return 2

    doc = _load(args.walkforward_json)
    folds = [f for f in (doc.get("folds") or []) if isinstance(f, dict)]
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}

    frac_gt = agg.get("fraction_test_beats_always_bull")
    if frac_gt is None:
        frac_gt = _frac_from_folds(folds, "test_beats_always_bull")
    if frac_gt is None:
        frac_gt = _frac_from_accuracy(folds, gte=False)

    frac_gte = agg.get("fraction_test_meets_or_beats_always_bull")
    if frac_gte is None:
        frac_gte = _frac_from_folds(folds, "test_meets_or_beats_always_bull")
    if frac_gte is None:
        frac_gte = _frac_from_accuracy(folds, gte=True)

    min_beat = float(args.min_beat_frac)
    out: dict[str, Any] = {
        "schema": "prophecy_lens_beat_bull_policy_ablation_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "walkforward_json": str(args.walkforward_json),
            "min_fraction_test_beats_always_bull": min_beat,
            "note": "Production gates use gt (strict). gte is research-only counterfactual.",
        },
        "policies": {
            "gt": {
                "fraction_folds_pass": frac_gt,
                "lens_beat_bull_gate_would_pass": bool(frac_gt is not None and float(frac_gt) >= min_beat),
            },
            "gte": {
                "fraction_folds_pass": frac_gte,
                "lens_beat_bull_gate_would_pass": bool(frac_gte is not None and float(frac_gte) >= min_beat),
            },
        },
        "fold_detail": [
            {
                "fold_index": f.get("fold_index"),
                "test_accuracy": (f.get("test") or {}).get("accuracy"),
                "always_bull_control": (f.get("test") or {}).get("always_bull_control"),
                "gt_pass": bool(f.get("test_beats_always_bull")),
                "gte_pass": (
                    bool(f.get("test_meets_or_beats_always_bull"))
                    if f.get("test_meets_or_beats_always_bull") is not None
                    else float((f.get("test") or {}).get("accuracy") or 0.0)
                    >= float((f.get("test") or {}).get("always_bull_control") or 0.0)
                ),
            }
            for f in folds
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"gt_frac={frac_gt} gte_frac={frac_gte} "
        f"gt_gate={out['policies']['gt']['lens_beat_bull_gate_would_pass']} "
        f"gte_gate={out['policies']['gte']['lens_beat_bull_gate_would_pass']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
