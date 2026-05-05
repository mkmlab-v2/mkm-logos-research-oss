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


def gate_status(doc: dict[str, Any]) -> dict[str, Any]:
    g = doc.get("gate_eval") if isinstance(doc.get("gate_eval"), dict) else {}
    return {
        "pass": bool(g.get("pass", not bool(g.get("should_alert", False)))),
        "should_alert": bool(g.get("should_alert", False)),
        "promotion_hold": bool(g.get("promotion_hold", False)),
        "reasons": g.get("reasons") if isinstance(g.get("reasons"), list) else [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build integrated multi-symbol gate summary.")
    ap.add_argument("--drift-gate-json", default="docs/final/artifacts/multi_symbol_top_drift_alert_latest.json")
    ap.add_argument("--negative-control-gate-json", default="docs/final/artifacts/multi_symbol_negative_control_gate_latest.json")
    ap.add_argument(
        "--counterfactual-comparison-json",
        default="docs/final/artifacts/multi_symbol_counterfactual_comparison_latest.json",
    )
    ap.add_argument("--output-json", default="docs/final/artifacts/multi_symbol_gate_summary_latest.json")
    args = ap.parse_args()

    dp = resolve(args.drift_gate_json)
    np = resolve(args.negative_control_gate_json)
    cp = resolve(args.counterfactual_comparison_json)
    op = resolve(args.output_json)
    for p in (dp, np, cp):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    drift = load(dp)
    neg = load(np)
    cf = load(cp)
    drift_status = gate_status(drift)
    neg_status = gate_status(neg)
    cf_status = gate_status(cf)

    all_pass = drift_status["pass"] and neg_status["pass"] and cf_status["pass"]
    any_hold = drift_status["promotion_hold"] or neg_status["promotion_hold"] or cf_status["promotion_hold"]

    out = {
        "schema": "multi_symbol_gate_summary_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "gates": {
            "drift": drift_status,
            "negative_control": neg_status,
            "counterfactual": cf_status,
        },
        "summary": {
            "all_pass": all_pass,
            "any_promotion_hold": any_hold,
            "status": "GO" if all_pass and not any_hold else "HOLD",
        },
        "sources": {
            "drift_gate_json": str(dp),
            "negative_control_gate_json": str(np),
            "counterfactual_comparison_json": str(cp),
        },
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

