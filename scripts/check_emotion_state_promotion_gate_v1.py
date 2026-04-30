#!/usr/bin/env python3
"""Promotion gate for emotion-state control mapping (B-track -> controlled candidate)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL = ROOT / "docs" / "final" / "artifacts" / "emotion_state_shadow_eval_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "emotion_state_promotion_gate_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _num(v: Any, d: float) -> float:
    try:
        return float(v)
    except Exception:
        return float(d)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-stability-score", type=float, default=0.95)
    ap.add_argument("--max-fpr", type=float, default=0.05)
    ap.add_argument("--max-p95-ms", type=float, default=500.0)
    ap.add_argument("--min-state-count", type=int, default=3)
    args = ap.parse_args()

    ev = _read_json(args.eval_json)
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    stability = _num(m.get("stability_score"), 0.0)
    fpr = _num(m.get("layer5_fpr"), 1.0)
    p95 = _num(m.get("layer5_p95_ms"), 999999.0)
    mapping_loaded = bool(ev.get("mapping_loaded"))
    mapping_state_count = int(_num(ev.get("mapping_state_count"), 0.0))
    mapping_state_safety_all_ok = bool(ev.get("mapping_state_safety_all_ok"))

    checks = {
        "mapping_loaded": mapping_loaded,
        "mapping_state_count_gte_threshold": mapping_state_count >= int(args.min_state_count),
        "mapping_state_safety_all_ok": mapping_state_safety_all_ok,
        "stability_score_gte_threshold": stability >= float(args.min_stability_score),
        "fpr_lte_threshold": fpr <= float(args.max_fpr),
        "p95_lte_threshold": p95 <= float(args.max_p95_ms),
    }
    decision = "PROMOTION_CANDIDATE" if all(checks.values()) else "HOLD"

    out = {
        "schema": "emotion_state_promotion_gate_v1",
        "generated_at_utc": _iso_now(),
        "track": "b_track_sandbox_only",
        "inputs": {"eval_json": str(args.eval_json).replace("\\", "/")},
        "thresholds": {
            "min_stability_score": float(args.min_stability_score),
            "max_fpr": float(args.max_fpr),
            "max_p95_ms": float(args.max_p95_ms),
            "min_state_count": int(args.min_state_count),
        },
        "metrics": {
            "stability_score": stability,
            "layer5_fpr": fpr,
            "layer5_p95_ms": p95,
            "mapping_state_count": mapping_state_count,
        },
        "checks": checks,
        "decision": decision,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
