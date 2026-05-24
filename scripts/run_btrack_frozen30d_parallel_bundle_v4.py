#!/usr/bin/env python3
"""[HYPO] Parallel bundle v4: legacy v1 MS hybrid + advisory sweeps + holdout OOS 180d."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v4_latest.json"
LEGACY_V1_PER = ROOT / "reports/btrack_ensemble_per_date_v1_prod_perdate_30d_v1.json"
M016_PER = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/per_date_margin_016.json"
M016_CFG = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/ens_margin_016.json"
WRONG_DIR = ROOT / "scripts/run_btrack_wrong_dir_holdout_v1.py"
HOLDOUT_OOS = ROOT / "scripts/build_btrack_holdout_gate_oos_180d_eval_v1.py"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "label": label,
        "exit_code": proc.returncode,
        "cmd": " ".join(cmd),
        "stderr_tail": (proc.stderr or "")[-800:] if proc.returncode else None,
        "stdout_tail": (proc.stdout or "")[-400:] if proc.returncode else (proc.stdout or "")[-200:],
    }


def _task_legacy_ms_hybrid() -> dict[str, Any]:
    from scripts.run_btrack_frozen30d_parallel_bundle_v2 import _task_hybrid

    if not LEGACY_V1_PER.is_file():
        return {"task": "legacy_ms_hybrid", "exit_code": 2, "error": f"missing {LEGACY_V1_PER}"}
    return _task_hybrid(
        LEGACY_V1_PER,
        "legacy_v1",
        ROOT / "reports/btrack_v1_ms_hybrid_legacy_v1_parallel_v1_latest.json",
        ROOT / "reports/btrack_v1_ms_hybrid_legacy_v1_work",
    )


def _task_advisory(per_date: Path, label: str) -> dict[str, Any]:
    if not per_date.is_file():
        return {"task": f"advisory_{label}", "exit_code": 2, "error": f"missing {per_date}"}
    out = ROOT / f"reports/btrack_advisory_bear_trap_manifest_{label}_v1_latest.json"
    sweep = ROOT / f"reports/btrack_advisory_bear_trap_sweep_{label}_v1_latest.json"
    rc = _run(
        [
            sys.executable,
            str(WRONG_DIR),
            "advisory-sweep",
            "--per-date",
            str(per_date.relative_to(ROOT)),
            "--output",
            str(out.relative_to(ROOT)),
            "--sweep-output",
            str(sweep.relative_to(ROOT)),
        ],
        label=f"advisory_{label}",
    )
    summary: dict[str, Any] = {}
    if sweep.is_file():
        doc = json.loads(sweep.read_text(encoding="utf-8"))
        summary = {
            "primary_rule": doc.get("primary_rule"),
            "n_rules": len(doc.get("rules_30d") or []),
            "sweep_path": str(sweep),
        }
        best = None
        for r in doc.get("rules_30d") or []:
            if not isinstance(r, dict):
                continue
            h7 = int(r.get("n_holdout7_wrong_overlap") or 0)
            if best is None or h7 > int(best.get("n_holdout7_wrong_overlap") or 0):
                best = r
        if best:
            summary["best_holdout7_wrong_overlap"] = best
    return {"task": f"advisory_{label}", **rc, "summary": summary}


def _task_holdout_oos_180d() -> dict[str, Any]:
    out = ROOT / "reports/btrack_holdout_gate_oos_180d_margin016_anchor_v1_latest.json"
    rc = _run(
        [sys.executable, str(HOLDOUT_OOS), "--output", str(out.relative_to(ROOT)), "--no-patch-manifest"],
        label="holdout_oos_180d",
    )
    summary: dict[str, Any] = {}
    if out.is_file():
        doc = json.loads(out.read_text(encoding="utf-8"))
        v = doc.get("verdict") if isinstance(doc.get("verdict"), dict) else {}
        e180 = doc.get("eval_180d") if isinstance(doc.get("eval_180d"), dict) else {}
        m = e180.get("metrics") if isinstance(e180.get("metrics"), dict) else {}
        summary = {
            "alert_1_pass_180d": v.get("alert_1_pass_180d"),
            "headline_180d": m.get("price_directional_hit_rate"),
            "holdout7_wrong_neutralized": (v.get("holdout7_wrong_neutralized")),
            "auto_promote": v.get("auto_promote"),
            "path": str(out),
        }
    return {"task": "holdout_oos_180d", **rc, "summary": summary}


def _task_flip_day_auxiliary() -> dict[str, Any]:
    """Apply holdout_ovn_signed_bull-style layer stats on frozen flip cohort (2026-04-30, 05-14)."""
    from scripts.btrack_wrong_dir_auxiliary_layer_v1 import apply_auxiliary_per_date_doc
    from scripts.run_btrack_wrong_dir_holdout_v1 import WORK

    flip_dates = ["2026-04-30", "2026-05-14"]
    if not M016_PER.is_file() or not LEGACY_V1_PER.is_file():
        return {"task": "flip_day_auxiliary", "exit_code": 2, "error": "missing per_date inputs"}

    layer = {
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": False,
            "preliminary_bull": True,
            "overnight_negative_or_positive": True,
        },
    }
    rows: list[dict[str, Any]] = []
    for label, per_path in (("legacy_v1", LEGACY_V1_PER), ("margin_016", M016_PER)):
        per_doc = json.loads(per_path.read_text(encoding="utf-8"))
        sub = {
            "schema": per_doc.get("schema"),
            "rows": [r for r in (per_doc.get("rows") or []) if str(r.get("eval_date") or "")[:10] in flip_dates],
        }
        adj = apply_auxiliary_per_date_doc(sub, layer)
        WORK.mkdir(parents=True, exist_ok=True)
        per_out = WORK / f"flip_aux_{label}.json"
        per_out.write_text(json.dumps(adj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # score only flip dates via batch on anchor
        dates_path = WORK / "flip_dates.json"
        dates_path.write_text(json.dumps({"eval_dates": flip_dates}, indent=2) + "\n", encoding="utf-8")
        score_out = WORK / f"flip_score_{label}.json"
        ev_out = WORK / f"flip_eval_{label}.json"
        subprocess.run(
            [
                sys.executable,
                "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                "--btc-csv",
                "research/market_data/btc_daily_external_yf.csv",
                "--batch-eval-dates-json",
                str(dates_path.relative_to(ROOT)),
                "--per-date-direction-json",
                str(per_out.relative_to(ROOT)),
                "--output",
                str(score_out.relative_to(ROOT)),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                sys.executable,
                "scripts/eval_prophecy_hit_rate_v1.py",
                "--run-mode",
                "price",
                "--score-json",
                str(score_out.relative_to(ROOT)),
                "--headline-instrument",
                "btc",
                "--output",
                str(ev_out.relative_to(ROOT)),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        ev = json.loads(ev_out.read_text(encoding="utf-8"))
        m = ev.get("metrics") or {}
        rows.append(
            {
                "label": label,
                "per_date": str(per_path),
                "n_flip_days": len(flip_dates),
                "metrics": m,
                "gated_neutral_count": sum(
                    1
                    for r in (adj.get("rows") or [])
                    if isinstance(r, dict)
                    and str(r.get("predicted_direction") or "").lower() == "neutral"
                ),
            }
        )

    out = ROOT / "reports/btrack_flip_day_auxiliary_v1_latest.json"
    report = {
        "schema": "btrack_flip_day_auxiliary_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "flip_dates": flip_dates,
        "note": "Wrong-bear flip days from daily diff; auxiliary force_neutral probe only.",
        "lanes": rows,
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "flip_day_auxiliary", "exit_code": 0, "report": str(out), "summary": report}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tasks = [
        _task_legacy_ms_hybrid,
        lambda: _task_advisory(LEGACY_V1_PER, "legacy_v1"),
        lambda: _task_advisory(M016_PER, "margin_016"),
        _task_holdout_oos_180d,
        _task_flip_day_auxiliary,
    ]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fn): i for i, fn in enumerate(tasks)}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": "unknown", "exit_code": 2, "error": str(exc)})

    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v4",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_auto_promote": False,
        "parallel_tasks": results,
        "leaderboard": {
            "legacy_ms_hybrid_target": 0.6,
            "margin016_ms_hybrid_known": 0.533333,
            "margin016_solo_known": 0.533333,
            "frozen_kpi_a": 0.433333,
        },
    }
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for r in results:
        print(f"  {r.get('task')}: exit={r.get('exit_code')} {r.get('summary', r.get('error', ''))}")
    return 0 if all(int(r.get("exit_code", 1)) == 0 for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
