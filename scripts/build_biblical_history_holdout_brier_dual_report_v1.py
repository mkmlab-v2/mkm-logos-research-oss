#!/usr/bin/env python3
"""Refresh hist.* holdout Brier evals (sandbox vs production) after registry merge."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SANDBOX = ROOT / "tests/fixtures/general_prophecy_registry_historical_holdout_v1.json"
DEFAULT_PRODUCTION = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
DEFAULT_OUT = ROOT / "reports/biblical_history_holdout_brier_dual_report_latest.json"
EVAL_SCRIPT = ROOT / "scripts/eval_general_prophecy_brier_score.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_brier(registry: Path, out_json: Path, *, include_rows: bool = False) -> int:
    cmd = [
        sys.executable,
        str(EVAL_SCRIPT),
        "-i",
        str(registry),
        "-o",
        str(out_json),
        "--no-print-output-path",
    ]
    if not include_rows:
        cmd.append("--no-rows")
    return int(subprocess.run(cmd, cwd=str(ROOT), check=False).returncode)


def _row_for_question(eval_path: Path, question_id: str) -> dict[str, Any] | None:
    if not eval_path.is_file():
        return None
    for row in (_load(eval_path).get("rows") or []):
        if isinstance(row, dict) and str(row.get("question_id")) == question_id:
            return row
    return None


def _mean_brier(eval_path: Path) -> tuple[float | None, int | None]:
    if not eval_path.is_file():
        return None, None
    metrics = (_load(eval_path).get("metrics") or {})
    return metrics.get("mean_brier_score"), metrics.get("n_evaluated")


def _hist_question_ids(registry: Path) -> list[str]:
    doc = _load(registry)
    ids = [
        str(q.get("question_id"))
        for q in (doc.get("questions") or [])
        if isinstance(q, dict) and str(q.get("question_id", "")).startswith("hist.")
    ]
    return sorted(ids)


def _brier_delta_row(
    sb_row: dict[str, Any] | None, ph_row: dict[str, Any] | None
) -> float | None:
    if not sb_row or not ph_row:
        return None
    sb_b = sb_row.get("brier_contribution")
    ph_b = ph_row.get("brier_contribution")
    if isinstance(sb_b, (int, float)) and isinstance(ph_b, (int, float)):
        return round(float(ph_b) - float(sb_b), 6)
    return None


def _filter_hist_registry(src: Path, dst: Path) -> int:
    doc = _load(src)
    questions = doc.get("questions") if isinstance(doc.get("questions"), list) else []
    hist = [q for q in questions if isinstance(q, dict) and str(q.get("question_id", "")).startswith("hist.")]
    out = {
        "schema": "general_prophecy_registry_v1",
        "version": doc.get("version", "1.0.0"),
        "research_rail": "B",
        "boundary_ack": True,
        "generated_at_utc": _utc_now(),
        "questions": hist,
        "note": "hist.* filter snapshot for post-merge Brier dual report",
    }
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(hist)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sandbox-registry", type=Path, default=DEFAULT_SANDBOX)
    ap.add_argument("--production-registry", type=Path, default=DEFAULT_PRODUCTION)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sb_eval = ROOT / "reports/historical_holdout_brier_eval_sandbox_latest.json"
    ph_eval = ROOT / "reports/historical_holdout_brier_eval_production_hist_only_latest.json"
    pr_eval = ROOT / "reports/historical_holdout_brier_eval_production_latest.json"
    hist_snapshot = ROOT / "reports/tmp_general_prophecy_production_hist_only_v1.json"

    hist_count = _filter_hist_registry(args.production_registry, hist_snapshot)
    steps: list[tuple[str, Path, Path, bool]] = [
        ("sandbox", args.sandbox_registry, sb_eval, True),
        ("production_hist_only", hist_snapshot, ph_eval, True),
        ("production_all", args.production_registry, pr_eval, False),
    ]
    for name, reg, out, include_rows in steps:
        if not reg.is_file():
            print(json.dumps({"ok": False, "error": f"missing registry: {reg}", "step": name}), file=sys.stderr)
            return 2
        rc = _run_brier(reg, out, include_rows=include_rows)
        if rc != 0:
            print(json.dumps({"ok": False, "error": f"brier failed step={name}", "registry": str(reg)}), file=sys.stderr)
            return rc

    sb, ns = _mean_brier(sb_eval)
    ph, np = _mean_brier(ph_eval)
    pr, nr = _mean_brier(pr_eval)
    delta = round((ph or 0) - (sb or 0), 6) if ph is not None and sb is not None else None

    hist_ids = _hist_question_ids(hist_snapshot)
    hist_per_question: list[dict[str, Any]] = []
    for qid in hist_ids:
        sb_row = _row_for_question(sb_eval, qid)
        ph_row = _row_for_question(ph_eval, qid)
        hist_per_question.append(
            {
                "question_id": qid,
                "sandbox_row": sb_row,
                "production_hist_row": ph_row,
                "brier_delta_production_minus_sandbox": _brier_delta_row(sb_row, ph_row),
            }
        )

    dss1_id = "hist.arch.dead_sea_scrolls_cave1_1947"
    sb_dss1_row = _row_for_question(sb_eval, dss1_id)
    ph_dss1_row = _row_for_question(ph_eval, dss1_id)
    dss1_brier_delta = _brier_delta_row(sb_dss1_row, ph_dss1_row)
    prod_ids = {
        str(q.get("question_id"))
        for q in (_load(args.production_registry).get("questions") or [])
        if isinstance(q, dict) and q.get("question_id")
    }

    payload = {
        "schema": "biblical_history_holdout_brier_dual_report_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "sandbox": {
            "registry": str(args.sandbox_registry),
            "eval": str(sb_eval),
            "n_evaluated": ns,
            "mean_brier_score": sb,
        },
        "production_hist_only": {
            "registry_filter": "hist.* question_id prefix",
            "registry_snapshot": str(hist_snapshot),
            "hist_question_count": hist_count,
            "eval": str(ph_eval),
            "n_evaluated": np,
            "mean_brier_score": ph,
        },
        "production_all_resolved": {
            "registry": str(args.production_registry),
            "eval": str(pr_eval),
            "n_evaluated": nr,
            "mean_brier_score": pr,
            "note": "Includes non-hist resolved rows in production registry",
        },
        "hist_per_question": hist_per_question,
        "hist_per_question_all_aligned": all(
            row.get("brier_delta_production_minus_sandbox") == 0.0 for row in hist_per_question
        ),
        "h_dss1_holdout_anchor": {
            "question_id": dss1_id,
            "in_production_registry": dss1_id in prod_ids,
            "sandbox_row": sb_dss1_row,
            "production_hist_row": ph_dss1_row,
            "brier_delta_production_minus_sandbox": dss1_brier_delta,
        },
        "delta": {
            "production_hist_minus_sandbox_mean_brier": delta,
            "interpretation": (
                "hist.* holdout rows align between sandbox fixture and production after merge"
                if ph == sb
                else "sandbox vs production hist.* mean Brier diverged — review merge/registry drift"
            ),
        },
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
        "fact_lock_notice": "Brier on resolved historical questions is calibration observation only; not Logos gating or price-direction proof.",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output_json),
                "sandbox_brier": sb,
                "production_hist_brier": ph,
                "delta": delta,
                "h_dss1_in_registry": dss1_id in prod_ids,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
