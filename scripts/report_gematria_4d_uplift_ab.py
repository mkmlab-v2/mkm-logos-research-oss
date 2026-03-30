#!/usr/bin/env python3
"""A/B compare compression metrics with bridge off vs on."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report


INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_GEMATRIA_4D_UPLIFT_AB_V1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _core_metrics(report: dict) -> dict[str, float]:
    c = report.get("compression_metrics", {})
    return {
        "global_token_saving_rate": float(c.get("global_token_saving_rate", 0.0)),
        "avg_reconstruction_fidelity_jaccard": float(c.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "avg_sensitive_integrity": float(c.get("avg_sensitive_integrity", 0.0)),
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="A/B compare uplift with gematria bridge policy on/off.")
    p.add_argument("--input", default=str(INPUT_V2), help="Input evaluation spec path")
    p.add_argument("--baseline", default=str(BASELINE_V2), help="Baseline report path")
    p.add_argument("--decision", default=str(DECISION), help="Decision profile path")
    p.add_argument("--output", default=str(OUT), help="Output A/B report path")
    return p


def main() -> int:
    args = _parser().parse_args()
    input_path = Path(args.input).resolve()
    baseline_path = Path(args.baseline).resolve()
    decision_path = Path(args.decision).resolve()
    out_path = Path(args.output).resolve()

    src = _load(input_path)
    base = _load(baseline_path)
    dec = _load(decision_path)
    selected = dec.get("selected_candidate") or {}

    strategy = str(selected.get("strategy", "B"))
    intensity = str(selected.get("intensity", "extreme"))
    baseline_avg_jaccard = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    kwargs = dict(
        source_input=str(input_path.relative_to(ROOT)).replace("\\", "/"),
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=(
            float(selected["general_max_saving_rate"]) if selected.get("general_max_saving_rate") is not None else None
        ),
        sensitive_max_saving_rate=(
            float(selected["sensitive_max_saving_rate"]) if selected.get("sensitive_max_saving_rate") is not None else None
        ),
        hangul_max_saving_rate=(
            float(selected["hangul_max_saving_rate"]) if selected.get("hangul_max_saving_rate") is not None else None
        ),
        use_domain_router=True,
    )
    off_report = evaluate_report(src, include_gematria_metadata=False, include_gematria_4d_bridge=False, **kwargs)
    on_report = evaluate_report(
        src,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
        apply_gematria_4d_bridge_policy=True,
        **kwargs,
    )
    off_m = _core_metrics(off_report)
    on_m = _core_metrics(on_report)
    deltas = {k: on_m[k] - off_m[k] for k in off_m}

    result = {
        "schema": "multilens_gematria_4d_uplift_ab_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "source_input": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "profile": {"strategy": strategy, "intensity": intensity},
        "ab_config": {
            "off": {"include_gematria_metadata": False, "include_gematria_4d_bridge": False},
            "on": {"include_gematria_metadata": True, "include_gematria_4d_bridge": True, "include_cee_core": True},
            "on_policy": {
                "apply_gematria_4d_bridge_policy": True,
            },
        },
        "metrics_off": off_m,
        "metrics_on": on_m,
        "deltas_on_minus_off": deltas,
        "quality_gate_off": off_report.get("quality_gate", {}),
        "quality_gate_on": on_report.get("quality_gate", {}),
        "uplift_claim_supported": any(abs(v) > 1e-12 for v in deltas.values()),
        "note": "Current bridge is metadata-layer; non-zero uplift requires separate algorithmic integration proof.",
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
