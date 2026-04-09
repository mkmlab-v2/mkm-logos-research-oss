#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report
from scripts.core.general_mcda_regime_switch import (
    choose_regime,
    derive_vector_4d,
    estimate_signals_from_text,
    weighted_risk_score,
)

DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "general_compression_eval_input_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_compression_ab_result_summary_v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _case_text_map(doc: dict[str, Any]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for c in doc.get("compression_cases", []):
        if not isinstance(c, dict):
            continue
        out[str(c.get("id", ""))] = {
            "raw_text": str(c.get("raw_text", "")),
            "domain": str(c.get("domain", "unknown")),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Run baseline/treatment compression eval for general rail.")
    ap.add_argument("--label", choices=("baseline", "treatment"), required=True)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--strategy", choices=("A", "B", "C"), default="A")
    ap.add_argument("--intensity", choices=("high", "ultra", "extreme"), default="extreme")
    ap.add_argument("--general-max-saving-rate", type=float, default=0.9)
    ap.add_argument("--sensitive-max-saving-rate", type=float, default=0.8)
    ap.add_argument("--hangul-max-saving-rate", type=float, default=0.75)
    args = ap.parse_args()

    doc = _load_json(args.input)
    if args.label == "baseline":
        report = evaluate_report(
            doc,
            source_input=str(args.input),
            mode="baseline",
            use_domain_router=True,
            use_master_codebook_lexicon_v1=True,
        )
    else:
        report = evaluate_report(
            doc,
            source_input=str(args.input),
            mode="experimental",
            strategy=args.strategy,
            intensity=args.intensity,
            use_domain_router=True,
            use_master_codebook_lexicon_v1=True,
            general_max_saving_rate=args.general_max_saving_rate,
            sensitive_max_saving_rate=args.sensitive_max_saving_rate,
            hangul_max_saving_rate=args.hangul_max_saving_rate,
        )

    compression = report.get("compression_metrics") or {}
    cases = compression.get("cases") or []
    case_map = _case_text_map(doc)
    regime_counts = {"normal": 0, "crisis": 0}
    switch_count = 0
    prev_regime: str | None = None
    score_sum = 0.0
    for c in cases:
        cid = str(c.get("id", ""))
        raw = case_map.get(cid, {}).get("raw_text", "")
        volatility, news_shock = estimate_signals_from_text(raw)
        v4 = derive_vector_4d(
            volatility=volatility,
            news_shock_score=news_shock,
            saving_rate=float(c.get("token_saving_rate", 0.0)),
            fidelity=float(c.get("reconstruction_fidelity_jaccard", 0.0)),
        )
        regime = choose_regime(volatility, news_shock)
        regime_counts[regime] += 1
        if prev_regime is not None and regime != prev_regime:
            switch_count += 1
        prev_regime = regime
        score_sum += weighted_risk_score(v4, regime)
    avg_risk_score = (score_sum / len(cases)) if cases else 0.0

    row = {
        "label": args.label,
        "profile": {
            "strategy": args.strategy if args.label == "treatment" else "baseline",
            "intensity": args.intensity if args.label == "treatment" else "baseline",
            "general_max_saving_rate": args.general_max_saving_rate if args.label == "treatment" else None,
            "sensitive_max_saving_rate": args.sensitive_max_saving_rate if args.label == "treatment" else None,
            "hangul_max_saving_rate": args.hangul_max_saving_rate if args.label == "treatment" else None,
        },
        "case_count": int(compression.get("case_count", 0)),
        "global_token_saving_rate": float(compression.get("global_token_saving_rate", 0.0)),
        "avg_reconstruction_fidelity_jaccard": float(compression.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "avg_sensitive_integrity": float(compression.get("avg_sensitive_integrity", 0.0)),
        "sensitive_violation_count": int(compression.get("sensitive_violation_count", 0)),
        "regime_switch_metrics": {
            "normal_count": regime_counts["normal"],
            "crisis_count": regime_counts["crisis"],
            "switch_count": switch_count,
            "avg_risk_score": avg_risk_score,
        },
    }

    if args.out.is_file() and args.append:
        payload = _load_json(args.out)
    else:
        payload = {"schema": "general_compression_ab_result_summary_v1", "runs": []}
    payload.setdefault("runs", [])
    runs = [r for r in payload["runs"] if isinstance(r, dict) and r.get("label") != args.label]
    runs.append(row)
    payload["runs"] = sorted(runs, key=lambda x: x.get("label", ""))
    _write(args.out, payload)
    print(json.dumps({"ok": True, "label": args.label, "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
