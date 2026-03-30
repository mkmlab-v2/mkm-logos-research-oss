#!/usr/bin/env python3
"""Run the selected ultra compression profile as operational default."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report


INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def main() -> int:
    src_doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision_doc = json.loads(DECISION.read_text(encoding="utf-8"))

    selected = decision_doc.get("selected_candidate") or {}
    strategy = str(selected.get("strategy", "B"))
    intensity = str(selected.get("intensity", "extreme"))
    general_max_saving_rate = selected.get("general_max_saving_rate")
    sensitive_max_saving_rate = selected.get("sensitive_max_saving_rate")
    if general_max_saving_rate is not None:
        general_max_saving_rate = float(general_max_saving_rate)
    if sensitive_max_saving_rate is not None:
        sensitive_max_saving_rate = float(sensitive_max_saving_rate)
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    report = evaluate_report(
        src_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=general_max_saving_rate,
        sensitive_max_saving_rate=sensitive_max_saving_rate,
    )
    report["active_profile"] = {
        "from_decision": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json",
        "strategy": strategy,
        "intensity": intensity,
        "general_max_saving_rate": general_max_saving_rate,
        "sensitive_max_saving_rate": sensitive_max_saving_rate,
    }
    ACTIVE_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ACTIVE_REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
