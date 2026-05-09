#!/usr/bin/env python3
"""Run Dark Flow gate across conservative/exploratory policies and compare results."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_darkflow_btrack_gate_v1.py"
DEFAULT_EVAL = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_eval_template_v1.json"
DEFAULT_POLICY_CONSERVATIVE = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_policy_conservative_v1.json"
DEFAULT_POLICY_EXPLORATORY = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_policy_exploratory_v1.json"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_dual_policy_report_latest.json"
DEFAULT_OUT_MD = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_dual_policy_report_latest.md"


def _run_gate(eval_json: Path, policy_json: Path, output_json: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(CHECKER),
        "--eval-json",
        str(eval_json),
        "--policy-json",
        str(policy_json),
        "--output-json",
        str(output_json),
    ]
    subprocess.run(cmd, check=True, cwd=str(ROOT))
    return json.loads(output_json.read_text(encoding="utf-8"))


def _top_label(gate: dict[str, Any]) -> str:
    ranked = gate.get("ranked_hypotheses", [])
    if isinstance(ranked, list) and ranked and isinstance(ranked[0], dict):
        return str(ranked[0].get("label", "n/a"))
    return "n/a"


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _build_md(report: dict[str, Any]) -> str:
    c = report["conservative"]
    e = report["exploratory"]
    lines: list[str] = []
    lines.append("# Dark Flow B-track Dual Policy Report")
    lines.append("")
    lines.append(f"- generated_at_utc: `{report['generated_at_utc']}`")
    lines.append(f"- eval_json: `{report['eval_json']}`")
    lines.append("")
    lines.append("## Decisions")
    lines.append("")
    lines.append(f"- conservative: `{c['decision']}`")
    lines.append(f"- exploratory: `{e['decision']}`")
    lines.append("")
    lines.append("## Score Comparison")
    lines.append("")
    lines.append(f"- conservative best_composite: `{c['best_composite_score']:.3f}`")
    lines.append(f"- exploratory best_composite: `{e['best_composite_score']:.3f}`")
    lines.append(f"- delta(exploratory - conservative): `{report['delta_best_composite']:.3f}`")
    lines.append("")
    lines.append("## Top Hypothesis")
    lines.append("")
    lines.append(f"- conservative top: `{c['top_hypothesis_label']}`")
    lines.append(f"- exploratory top: `{e['top_hypothesis_label']}`")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(f"- alignment: `{report['top_hypothesis_aligned']}`")
    lines.append("- Conservative policy prioritizes replication and low systematic risk.")
    lines.append("- Exploratory policy allows earlier research progression under uncertainty.")
    lines.append("- Both outputs remain B-track research-only and cannot auto-bind to A-track.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build darkflow dual-policy comparison report.")
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--policy-conservative", type=Path, default=DEFAULT_POLICY_CONSERVATIVE)
    ap.add_argument("--policy-exploratory", type=Path, default=DEFAULT_POLICY_EXPLORATORY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    if not CHECKER.exists():
        raise FileNotFoundError(f"Missing checker script: {CHECKER}")
    if not args.eval_json.exists():
        raise FileNotFoundError(f"Missing eval json: {args.eval_json}")
    if not args.policy_conservative.exists():
        raise FileNotFoundError(f"Missing conservative policy: {args.policy_conservative}")
    if not args.policy_exploratory.exists():
        raise FileNotFoundError(f"Missing exploratory policy: {args.policy_exploratory}")

    tmp_cons = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_gate_conservative_latest.json"
    tmp_expl = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_gate_exploratory_latest.json"
    cons = _run_gate(args.eval_json, args.policy_conservative, tmp_cons)
    expl = _run_gate(args.eval_json, args.policy_exploratory, tmp_expl)

    cons_best = _to_float(cons.get("best_composite_score"))
    expl_best = _to_float(expl.get("best_composite_score"))
    report = {
        "schema": "darkflow_btrack_dual_policy_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "eval_json": str(args.eval_json),
        "conservative": {
            "policy_json": str(args.policy_conservative),
            "decision": str(cons.get("decision", "n/a")),
            "best_composite_score": cons_best,
            "top_hypothesis_label": _top_label(cons),
        },
        "exploratory": {
            "policy_json": str(args.policy_exploratory),
            "decision": str(expl.get("decision", "n/a")),
            "best_composite_score": expl_best,
            "top_hypothesis_label": _top_label(expl),
        },
        "delta_best_composite": round(expl_best - cons_best, 6),
        "top_hypothesis_aligned": _top_label(cons) == _top_label(expl),
        "source_track": "B",
        "observation_mode": "RESEARCH_ONLY",
        "auto_bind_to_atrack_forbidden": True,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_build_md(report), encoding="utf-8")
    print(str(args.output_json))
    print(str(args.output_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
