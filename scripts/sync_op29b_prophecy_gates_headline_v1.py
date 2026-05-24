#!/usr/bin/env python3
"""Isolate O-P29b headline lane: WF + gates on shadow score without touching headline SSOT.

- Never overwrites ``prophecy_hit_rate_eval_latest.json`` (commander-approved ACTIVE KPI).
- Writes ``reports/prophecy_promotion_gates_v1_op29b_lane_latest.json``.
- Mirrors shared-gate snapshot to ``prophecy_promotion_gates_v1_panel_calibrated_latest.json``.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prophecy_hit_rate_ssot_v1 import HEADLINE_KPI, OP29B_STRATEGIC_SYNC  # noqa: E402

SHADOW = ROOT / "reports" / "op29b_shadow"
SCORE = SHADOW / "btrack_prophecy_score_op29b_shadow.json"
PER_DATE = SHADOW / "btrack_ensemble_per_date_directions_180d_op29b_gated.json"
HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"

HEADLINE = HEADLINE_KPI
BACKUP_HEADLINE = SHADOW / "prophecy_hit_rate_eval_o535_backup_20260522.json"
OUT = ROOT / "reports/prophecy_promotion_gates_v1_op29b_lane_latest.json"
PANEL_OUT = ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_panel_calibrated_latest.json"
WORK = ROOT / "reports/op29b_gates_sync_work"
STREAK = ROOT / "reports/prophecy_promotion_strict_streak_op29b_lane_v1.json"
SUMMARY = OP29B_STRATEGIC_SYNC


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _ensure_headline_ssot(py: str) -> dict[str, Any]:
    doc = _load(HEADLINE)
    hp = doc.get("headline_promotion_v1") if isinstance(doc.get("headline_promotion_v1"), dict) else {}
    rate = (doc.get("metrics") or {}).get("price_directional_hit_rate")
    lane = hp.get("lane")
    ok = (
        hp.get("human_approved") is True
        and lane == "op29b_dynamic_min018_v2"
        and rate is not None
        and float(rate) >= 0.57
    )
    if ok:
        return {"restored": False, "rate": rate, "lane": lane}
    if SCORE.is_file() and PER_DATE.is_file():
        rc = _run(
            [
                py,
                "scripts/promote_op28_headline_kpi_v1.py",
                "--score-json",
                str(SCORE),
                "--per-date-json",
                str(PER_DATE),
                "--min-confidence",
                "0.18",
                "--score-abs-deadzone",
                "0.0",
                "--prior-headline-rate",
                "0.535354",
                "--promotion-lane",
                "op29b_dynamic_min018_v2",
                "--used-field",
                "op29b_dynamic_per_date_lens_v2_confidence_fusion",
                "--output",
                str(HEADLINE),
            ]
        )
        doc = _load(HEADLINE)
        hp = doc.get("headline_promotion_v1") or {}
        return {
            "restored": rc == 0,
            "via": "promote_op28_headline_kpi_v1",
            "exit_code": rc,
            "rate": (doc.get("metrics") or {}).get("price_directional_hit_rate"),
            "lane": hp.get("lane"),
        }
    return {"restored": False, "error": "headline_missing_or_not_op29b", "rate": rate, "lane": lane}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-folds", type=int, default=4)
    ap.add_argument("--output", type=Path, default=SUMMARY)
    ap.add_argument(
        "--skip-headline-promote",
        action="store_true",
        help="Do not run promote_op28_headline_kpi_v1 (keep prophecy_hit_rate_eval_latest.json unchanged).",
    )
    args = ap.parse_args()

    py = sys.executable
    missing = [p for p in (SCORE, PER_DATE, HYPO) if not p.is_file()]
    if missing:
        print(f"ABORT missing: {missing}", file=sys.stderr)
        return 1

    if args.skip_headline_promote:
        doc = _load(HEADLINE)
        hp = doc.get("headline_promotion_v1") if isinstance(doc.get("headline_promotion_v1"), dict) else {}
        headline_status = {
            "skipped_promote": True,
            "rate": (doc.get("metrics") or {}).get("price_directional_hit_rate"),
            "lane": hp.get("lane"),
            "human_approved": hp.get("human_approved"),
        }
    else:
        headline_status = _ensure_headline_ssot(py)
    WORK.mkdir(parents=True, exist_ok=True)
    lens_wf = WORK / "lens_walkforward.json"
    inst_wf = WORK / "instrument_walkforward.json"

    steps: list[dict[str, Any]] = []

    rc = _run(
        [
            py,
            "scripts/run_prophecy_per_date_combo_walkforward_v1.py",
            "--score-json",
            str(SCORE),
            "--output",
            str(lens_wf),
            "--n-folds",
            str(args.n_folds),
        ]
    )
    steps.append({"step": "lens_walkforward", "exit_code": rc})
    if rc != 0:
        return _write_summary(args.output, headline_status, steps, gates_doc=None, exit_code=rc)

    rc = _run(
        [
            py,
            "scripts/run_prophecy_instrument_combo_walkforward_v1.py",
            "--score-json",
            str(SCORE),
            "--output",
            str(inst_wf),
            "--n-folds",
            str(args.n_folds),
        ]
    )
    steps.append({"step": "instrument_walkforward", "exit_code": rc})
    if rc != 0:
        return _write_summary(args.output, headline_status, steps, gates_doc=None, exit_code=rc)

    rc = _run(
        [
            py,
            "scripts/eval_prophecy_promotion_gates_v1.py",
            "--promotion-track-mode",
            "dual",
            "--lens-walkforward-json",
            str(lens_wf),
            "--instrument-walkforward-json",
            str(inst_wf),
            "--score-json",
            str(SCORE),
            "--hypothesis-json",
            str(HYPO),
            "--streak-history-json",
            str(STREAK),
            "--output",
            str(OUT),
            "--calibration-note",
            "op29b_lane_isolated; headline SSOT prophecy_hit_rate_eval_latest.json not modified",
        ]
    )
    steps.append({"step": "eval_gates_op29b_lane", "exit_code": rc})

    gates_doc = _load(OUT)
    if gates_doc:
        panel = dict(gates_doc)
        panel["headline_lane_isolation_v1"] = {
            "headline_ssot": str(HEADLINE.relative_to(ROOT)),
            "headline_status": headline_status,
            "formal_gates_scope": "op29b_shadow_score_only",
            "track_a_live_auto_merge": False,
        }
        PANEL_OUT.parent.mkdir(parents=True, exist_ok=True)
        PANEL_OUT.write_text(json.dumps(panel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _run([py, "scripts/build_prophecy_promotion_readiness_report_v1.py", "--gates-json", str(OUT), "--hit-rate-json", str(HEADLINE), "--output", "reports/prophecy_promotion_readiness_op29b_lane_v1_latest.json"])
    _run([py, "scripts/build_prophecy_gate_evidence_pack_v1.py"])

    return _write_summary(args.output, headline_status, steps, gates_doc=gates_doc, exit_code=0 if rc == 0 else rc)


def _write_summary(
    out: Path,
    headline_status: dict[str, Any],
    steps: list[dict[str, Any]],
    *,
    gates_doc: dict[str, Any] | None,
    exit_code: int,
) -> int:
    pack = {
        "schema": "op29b_prophecy_gates_headline_sync_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "headline_status": headline_status,
        "paths": {
            "score": str(SCORE.relative_to(ROOT)),
            "per_date": str(PER_DATE.relative_to(ROOT)),
            "gates_op29b_lane": str(OUT.relative_to(ROOT)),
            "panel_calibrated": str(PANEL_OUT.relative_to(ROOT)),
            "headline_ssot": str(HEADLINE.relative_to(ROOT)),
        },
        "steps": steps,
        "gates_summary": {
            "combined_all_passed": gates_doc.get("combined_all_passed") if gates_doc else None,
            "promotion_recommendation": gates_doc.get("promotion_recommendation") if gates_doc else None,
            "strict_pass_streak": gates_doc.get("strict_pass_streak") if gates_doc else None,
        },
        "note": "Headline 57.3% ACTIVE is commander lane; this sync does not merge into Track A or live.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": exit_code == 0, "output": str(out), "combined": pack["gates_summary"].get("combined_all_passed")}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
