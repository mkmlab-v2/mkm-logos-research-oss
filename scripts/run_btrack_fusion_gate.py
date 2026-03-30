#!/usr/bin/env python3
"""Run fused B-Track gate: gematria-4d lane gate + CEE pilots."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_fusion_gate_latest.json"
RISK_LOG = ROOT / "reports" / "constitution" / "btrack_pilot" / "fusion_gate_risk_log.jsonl"
EVIDENCE_TODO = ROOT / "reports" / "constitution" / "btrack_pilot" / "fusion_gate_evidence_todo_latest.json"
RISK_ORDER = {"stable": 0, "medium": 1, "high_thin": 2, "critical_thin": 3}


def _run(cmd: list[str]) -> None:
    print(f"[run] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def _write_evidence_todo(path: Path, *, risk_band: str, streak: int, mean_margin: float, consensus_winner: str | None) -> None:
    payload = {
        "schema": "fusion_gate_evidence_todo_v1",
        "risk_band": risk_band,
        "thin_margin_streak": streak,
        "cee_mean_lambda_margin": mean_margin,
        "cee_consensus_winner": consensus_winner,
        "tasks": [
            "Add direct witness line-level excerpts for Deut.32:8 neighborhood (Hebrew + transliteration).",
            "Add at least 2 independent source_doc entries per key token family (god/sons/israel).",
            "Re-run scripts/run_btrack_fusion_gate.py and confirm risk band moves to medium or stable.",
        ],
        "guardrail": "Use provisional wording only until risk band is medium/stable.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run fused B-Track gate pipeline")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--min-resonance-rate", type=float, default=0.80)
    ap.add_argument("--min-mean-axis-pearson", type=float, default=-0.20)
    ap.add_argument("--min-saving-delta", type=float, default=-0.20)
    ap.add_argument("--min-cee-consensus-rate", type=float, default=0.60)
    ap.add_argument("--min-cee-mean-margin", type=float, default=0.0010)
    ap.add_argument("--min-master-atoms", type=int, default=10000)
    ap.add_argument("--min-master-hebrew-atoms", type=int, default=5000)
    ap.add_argument("--min-master-greek-atoms", type=int, default=3000)
    ap.add_argument(
        "--master-atoms-lemma-mode",
        choices=("normalized_form_v1", "heuristic_lemma_v2"),
        default="normalized_form_v1",
    )
    ap.add_argument(
        "--max-cee-risk-band",
        choices=("stable", "medium", "high_thin", "critical_thin"),
        default="critical_thin",
        help="Fail when computed cee risk band exceeds this level.",
    )
    ap.add_argument("--risk-log", default=str(RISK_LOG))
    ap.add_argument("--evidence-todo", default=str(EVIDENCE_TODO))
    ap.add_argument("--thin-margin-threshold", type=float, default=0.01)
    ap.add_argument("--thin-margin-streak-limit", type=int, default=10)
    ap.add_argument(
        "--enforce-thin-margin-streak",
        action="store_true",
        help="Fail when thin-margin streak reaches limit. Default behavior is warning-only.",
    )
    args = ap.parse_args()
    py = args.python

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    evidence_todo_path = Path(args.evidence_todo)
    if not evidence_todo_path.is_absolute():
        evidence_todo_path = ROOT / evidence_todo_path
    risk_log_path = Path(args.risk_log)
    if not risk_log_path.is_absolute():
        risk_log_path = ROOT / risk_log_path

    _run(
        [
            py,
            "scripts/run_gematria_4d_gate.py",
            "--min-resonance-rate",
            str(args.min_resonance_rate),
            "--min-mean-axis-pearson",
            str(args.min_mean_axis_pearson),
            "--min-saving-delta",
            str(args.min_saving_delta),
        ]
    )
    _run([py, "scripts/run_deut32_cee_pilot.py"])
    _run([py, "scripts/run_deut32_cee_stability_sweep.py"])
    _run([py, "scripts/core/build_original_language_master_atoms.py", "--lemma-mode", args.master_atoms_lemma_mode])
    _run(
        [
            py,
            "scripts/check_master_atoms_health.py",
            "--min-unique-atoms",
            str(args.min_master_atoms),
            "--min-hebrew-atoms",
            str(args.min_master_hebrew_atoms),
            "--min-greek-atoms",
            str(args.min_master_greek_atoms),
        ]
    )

    cee_sweep = _jread(ROOT / "reports" / "constitution" / "btrack_pilot" / "deut32_cee_stability_sweep_v1.json")
    cee_pilot = _jread(ROOT / "reports" / "constitution" / "btrack_pilot" / "deut32_cee_pilot_v1.json")
    align = _jread(ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_gematria_alignment_test_nonzero.json")
    uplift = _jread(ROOT / "docs" / "final" / "artifacts" / "MULTILENS_GEMATRIA_4D_UPLIFT_AB_V1.json")
    master_atoms = _jread(ROOT / "reports" / "constitution" / "btrack_pilot" / "original_language_master_atoms_summary_latest.json")

    consensus_rate = float(cee_sweep.get("summary", {}).get("consensus_rate", 0.0))
    mean_margin = float(cee_sweep.get("summary", {}).get("mean_lambda_margin", 0.0))
    resonance_rate = float(align.get("summary", {}).get("resonance_rate", 0.0))
    mean_axis_pearson = float(align.get("summary", {}).get("mean_axis_pearson", -1.0))
    saving_delta = float(uplift.get("deltas_on_minus_off", {}).get("global_token_saving_rate", -1.0))

    failures: list[str] = []
    if consensus_rate < args.min_cee_consensus_rate:
        failures.append(
            f"CEE consensus_rate below min: current={consensus_rate:.6f} min={args.min_cee_consensus_rate:.6f}"
        )
    if mean_margin < 0.001:
        risk_band = "critical_thin"
    elif mean_margin < 0.005:
        risk_band = "high_thin"
    elif mean_margin < 0.02:
        risk_band = "medium"
    else:
        risk_band = "stable"

    if mean_margin < args.min_cee_mean_margin:
        failures.append(
            f"CEE mean_lambda_margin below min: current={mean_margin:.6f} min={args.min_cee_mean_margin:.6f}"
        )
    if RISK_ORDER[risk_band] > RISK_ORDER[args.max_cee_risk_band]:
        failures.append(
            f"CEE risk band above max: current={risk_band} max={args.max_cee_risk_band}"
        )

    # Append risk log and compute thin-margin streak.
    risk_log_path.parent.mkdir(parents=True, exist_ok=True)
    current_log = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decision": None,  # filled later
        "cee_consensus_winner": cee_sweep.get("summary", {}).get("consensus_winner"),
        "cee_consensus_rate": consensus_rate,
        "cee_mean_lambda_margin": mean_margin,
        "cee_margin_risk_band": risk_band,
        "thin_margin_threshold": args.thin_margin_threshold,
    }
    with risk_log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(current_log, ensure_ascii=False) + "\n")

    logs = _read_jsonl(risk_log_path)
    streak = 0
    threshold = float(args.thin_margin_threshold)
    for row in reversed(logs):
        m = row.get("cee_mean_lambda_margin")
        if isinstance(m, (int, float)) and float(m) <= threshold:
            streak += 1
        else:
            break
    thin_streak_alert = streak >= int(args.thin_margin_streak_limit)
    if thin_streak_alert and args.enforce_thin_margin_streak:
        failures.append(
            "CEE thin-margin streak limit reached: "
            f"streak={streak} threshold={threshold:.6f} limit={args.thin_margin_streak_limit}"
        )

    if risk_band in {"critical_thin", "high_thin"} and thin_streak_alert:
        recommended_action = "enforce_hard_gate_and_collect_direct_witness"
    elif risk_band in {"critical_thin", "high_thin"}:
        recommended_action = "collect_more_evidence"
    elif risk_band == "medium":
        recommended_action = "monitor"
    else:
        recommended_action = "stable_continue"

    evidence_todo_written = False
    if recommended_action in {"collect_more_evidence", "enforce_hard_gate_and_collect_direct_witness"}:
        _write_evidence_todo(
            evidence_todo_path,
            risk_band=risk_band,
            streak=streak,
            mean_margin=mean_margin,
            consensus_winner=cee_sweep.get("summary", {}).get("consensus_winner"),
        )
        evidence_todo_written = True

    decision = "pass" if not failures else "fail"
    current_log["decision"] = decision
    report = {
        "schema": "btrack_fusion_gate_v1",
        "decision": decision,
        "thresholds": {
            "min_resonance_rate": args.min_resonance_rate,
            "min_mean_axis_pearson": args.min_mean_axis_pearson,
            "min_saving_delta": args.min_saving_delta,
            "min_cee_consensus_rate": args.min_cee_consensus_rate,
            "min_cee_mean_margin": args.min_cee_mean_margin,
            "min_master_atoms": args.min_master_atoms,
            "min_master_hebrew_atoms": args.min_master_hebrew_atoms,
            "min_master_greek_atoms": args.min_master_greek_atoms,
            "master_atoms_lemma_mode": args.master_atoms_lemma_mode,
            "max_cee_risk_band": args.max_cee_risk_band,
            "thin_margin_threshold": args.thin_margin_threshold,
            "thin_margin_streak_limit": args.thin_margin_streak_limit,
            "enforce_thin_margin_streak": bool(args.enforce_thin_margin_streak),
        },
        "metrics": {
            "gematria_resonance_rate": resonance_rate,
            "gematria_mean_axis_pearson": mean_axis_pearson,
            "gematria_saving_delta_on_minus_off": saving_delta,
            "cee_pilot_winner": cee_pilot.get("decision", {}).get("winner_reading_id"),
            "cee_pilot_lambda_margin": cee_pilot.get("decision", {}).get("lambda_margin"),
            "cee_consensus_winner": cee_sweep.get("summary", {}).get("consensus_winner"),
            "cee_consensus_rate": consensus_rate,
            "cee_mean_lambda_margin": mean_margin,
            "cee_margin_risk_band": risk_band,
            "cee_thin_margin_streak": streak,
            "cee_thin_margin_streak_alert": thin_streak_alert,
            "recommended_action": recommended_action,
            "master_atoms_unique": master_atoms.get("stats", {}).get("unique_master_atoms"),
            "master_atoms_by_lang": master_atoms.get("stats", {}).get("unique_atoms_by_lang"),
            "master_atoms_lemma_method": master_atoms.get("stats", {}).get("lemma_method"),
        },
        "risk_log_path": str(risk_log_path),
        "evidence_todo_path": str(evidence_todo_path) if evidence_todo_written else None,
        "failures": failures,
        "guardrail": {
            "preferred_terms": ["우세 가설", "provisional", "추가 검증 필요"],
            "forbidden_terms": ["정답 확정", "final accept"],
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"fusion_decision={decision}")
    print(f"out={out_path}")
    if thin_streak_alert:
        print(
            "WARNING: CEE thin-margin streak alert "
            f"(streak={streak}, threshold={threshold:.6f}, limit={args.thin_margin_streak_limit})"
        )
    if failures:
        for f in failures:
            print(f"- {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
