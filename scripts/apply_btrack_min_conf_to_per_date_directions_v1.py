#!/usr/bin/env python3
"""Apply production min_direction_confidence gate to per-date direction rows (bull/bear -> neutral)."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_direction_confidence_gate_v1 import apply_min_direction_confidence_gate

DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply_gate_to_document(
    doc: dict[str, Any],
    *,
    rules: dict[str, Any],
) -> dict[str, Any]:
    out = copy.deepcopy(doc)
    rows = out.get("rows") if isinstance(out.get("rows"), list) else []
    n_applied = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        prior = str(r.get("predicted_direction") or "neutral").lower()
        try:
            conf = float(r.get("confidence") if r.get("confidence") is not None else 0.0)
        except (TypeError, ValueError):
            conf = 0.0
        direction, confidence, gate = apply_min_direction_confidence_gate(
            prior, conf, rules=rules
        )
        if gate.get("applied"):
            n_applied += 1
        r["predicted_direction"] = direction
        r["confidence"] = confidence
        r["low_confidence_direction_gate"] = gate
    meta = out.get("gate_meta") if isinstance(out.get("gate_meta"), dict) else {}
    meta.update(
        {
            "applied_at_utc": _utc_now(),
            "min_direction_confidence": rules.get("min_direction_confidence"),
            "rows_gated_to_neutral": n_applied,
        }
    )
    out["gate_meta"] = meta
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument(
        "--min-direction-confidence",
        type=float,
        default=None,
        help="Override rules.min_direction_confidence for this run (sweep / shadow).",
    )
    args = ap.parse_args()
    if not args.input.is_file():
        print(f"Missing: {args.input}", file=sys.stderr)
        return 2
    cfg = json.loads(args.ensemble_config.read_text(encoding="utf-8"))
    rules = dict(cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {})
    if args.min_direction_confidence is not None:
        rules["min_direction_confidence"] = float(args.min_direction_confidence)
    doc = json.loads(args.input.read_text(encoding="utf-8"))
    gated = apply_gate_to_document(doc, rules=rules)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(gated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} "
        f"gated={gated.get('gate_meta', {}).get('rows_gated_to_neutral')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
