#!/usr/bin/env python3
"""[HYPO] B-track model swap PoC — frozen harness (per-date score/eval), no ensemble promote.

Engines (v1):
  baseline_ensemble — build_btrack_ensemble_per_date_directions_v1.py (prod config copy)
  gemini_single_shot — optional smoke (--include-gemini); NOT comparable to 30d panel
  gemini_per_date_30d — build_btrack_gemini_per_date_directions_v1.py (30 causal API calls max)

Does NOT write btrack_lens_ensemble_v1.json or touch Track A / live trading.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_wrong_dir_holdout_core_v1 import holdout_dates_from_cf

DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/btrack_model_swap_harness_v1_latest.json"
WORK = ROOT / "reports/btrack_model_swap_work"

FROZEN_BASELINE_HEADLINE = 0.366667
ALERT_1_FLOOR = 0.5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *cmd],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _btc_metrics_from_eval(ev: dict[str, Any]) -> dict[str, Any]:
    legs = ev.get("metrics", {}).get("legs") if isinstance(ev.get("metrics"), dict) else {}
    if not isinstance(legs, dict):
        legs = {}
    btc = legs.get("btc") if isinstance(legs.get("btc"), dict) else {}
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    rate = m.get("price_directional_hit_rate")
    if rate is None and btc:
        rate = btc.get("price_directional_hit_rate")
    n = m.get("n_evaluated")
    if n is None and btc:
        n = btc.get("n_evaluated")
    dir_rate = m.get("price_hit_rate_on_directional_calls")
    if dir_rate is None and btc:
        dir_rate = btc.get("price_hit_rate_on_directional_calls")
    n_dir = m.get("n_directional_calls")
    if n_dir is None and btc:
        n_dir = btc.get("n_directional_calls")
    headline = float(rate) if rate is not None else None
    return {
        "price_directional_hit_rate": headline,
        "n_evaluated": n,
        "price_hit_rate_on_directional_calls": dir_rate,
        "n_directional_calls": n_dir,
        "alert_1_pass": headline is not None and headline >= ALERT_1_FLOOR,
        "alert_1b_pass": (
            dir_rate is not None
            and int(n_dir or 0) >= 10
            and float(dir_rate) >= ALERT_1_FLOOR
        ),
        "beats_frozen_baseline": headline is not None and headline > FROZEN_BASELINE_HEADLINE,
    }


def _holdout_wrong_dir_count(score_doc: dict[str, Any], holdout: set[str]) -> dict[str, Any]:
    wrong = 0
    n_holdout = 0
    for r in score_doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if ed not in holdout:
            continue
        n_holdout += 1
        pred = str(r.get("predicted_direction") or "").lower()
        act = str(r.get("actual_direction") or "").lower()
        if pred in ("bull", "bear") and act in ("bull", "bear") and pred != act:
            wrong += 1
    return {"n_holdout_days": n_holdout, "n_wrong_direction": wrong}


def run_baseline_ensemble_window(*, days: int, cfg: Path) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    tag = f"baseline_{days}d"
    cfg_copy = WORK / f"ens_cfg_{tag}.json"
    per_date = WORK / f"per_date_{tag}.json"
    score = WORK / f"score_{tag}.json"
    ev_out = WORK / f"eval_{tag}.json"

    cfg_copy.write_text(cfg.read_text(encoding="utf-8"), encoding="utf-8")

    steps: list[dict[str, Any]] = []

    p1 = _run(
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            str(days),
            "--target-instrument",
            "btc",
            "--ensemble-config",
            _rel(cfg_copy),
            "--output",
            _rel(per_date),
        ]
    )
    steps.append({"step": "per_date", "exit_code": p1.returncode})
    if p1.returncode != 0:
        return {
            "engine": "baseline_ensemble",
            "days": days,
            "status": "failed",
            "steps": steps,
            "stderr_tail": (p1.stderr or "")[-2000:],
        }

    p2 = _run(
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(days),
            "--force-dual-leg-panel",
            "--btc-csv",
            _rel(DEFAULT_BTC),
            "--kospi-csv",
            _rel(DEFAULT_KOSPI),
            "--per-date-direction-json",
            _rel(per_date),
            "--output",
            _rel(score),
        ]
    )
    steps.append({"step": "score", "exit_code": p2.returncode})
    if p2.returncode != 0:
        return {
            "engine": "baseline_ensemble",
            "days": days,
            "status": "failed",
            "steps": steps,
            "stderr_tail": (p2.stderr or "")[-2000:],
        }

    p3 = _run(
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            _rel(score),
            "--output",
            _rel(ev_out),
        ]
    )
    steps.append({"step": "eval", "exit_code": p3.returncode})
    if p3.returncode != 0:
        return {
            "engine": "baseline_ensemble",
            "days": days,
            "status": "failed",
            "steps": steps,
            "stderr_tail": (p3.stderr or "")[-2000:],
        }

    ev = _load(ev_out)
    score_doc = _load(score)
    holdout = set(holdout_dates_from_cf(DEFAULT_CF))
    return {
        "engine": "baseline_ensemble",
        "days": days,
        "status": "ok",
        "steps": steps,
        "paths": {
            "per_date": str(per_date),
            "score": str(score),
            "eval": str(ev_out),
        },
        "metrics": _btc_metrics_from_eval(ev),
        "holdout7": _holdout_wrong_dir_count(score_doc, holdout),
    }


def run_gemini_per_date_window(
    *,
    days: int,
    model: str,
    timeout: int,
    sleep_sec: float,
    max_retries: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    if days > 30:
        return {
            "engine": "gemini_per_date_30d",
            "days": days,
            "status": "failed",
            "reason": "cap_30d_only",
        }
    WORK.mkdir(parents=True, exist_ok=True)
    tag = f"gemini_per_date_{days}d"
    per_date = WORK / f"per_date_{tag}.json"
    score = WORK / f"score_{tag}.json"
    ev_out = WORK / f"eval_{tag}.json"
    cache_dir = WORK / "gemini_per_date_cache"

    steps: list[dict[str, Any]] = []
    cmd = [
        "scripts/build_btrack_gemini_per_date_directions_v1.py",
        "--recent-trading-days",
        str(days),
        "--model",
        model,
        "--timeout",
        str(timeout),
        "--sleep-sec",
        str(sleep_sec),
        "--max-retries",
        str(max_retries),
        "--cache-dir",
        _rel(cache_dir),
        "--output",
        _rel(per_date),
    ]
    if dry_run:
        cmd.append("--dry-run")
    p1 = _run(cmd)
    steps.append({"step": "gemini_per_date", "exit_code": p1.returncode})
    if p1.returncode != 0:
        return {
            "engine": "gemini_per_date_30d",
            "days": days,
            "status": "failed",
            "steps": steps,
            "stderr_tail": (p1.stderr or "")[-2000:],
            "comparable_to_30d_panel": True,
        }
    if dry_run:
        return {
            "engine": "gemini_per_date_30d",
            "days": days,
            "status": "ok",
            "dry_run": True,
            "steps": steps,
            "comparable_to_30d_panel": True,
        }

    p2 = _run(
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(days),
            "--force-dual-leg-panel",
            "--btc-csv",
            _rel(DEFAULT_BTC),
            "--kospi-csv",
            _rel(DEFAULT_KOSPI),
            "--per-date-direction-json",
            _rel(per_date),
            "--output",
            _rel(score),
        ]
    )
    steps.append({"step": "score", "exit_code": p2.returncode})
    if p2.returncode != 0:
        return {
            "engine": "gemini_per_date_30d",
            "days": days,
            "status": "failed",
            "steps": steps,
            "stderr_tail": (p2.stderr or "")[-2000:],
            "comparable_to_30d_panel": True,
        }

    p3 = _run(
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            _rel(score),
            "--output",
            _rel(ev_out),
        ]
    )
    steps.append({"step": "eval", "exit_code": p3.returncode})
    if p3.returncode != 0:
        return {
            "engine": "gemini_per_date_30d",
            "days": days,
            "status": "failed",
            "steps": steps,
            "stderr_tail": (p3.stderr or "")[-2000:],
            "comparable_to_30d_panel": True,
        }

    ev = _load(ev_out)
    score_doc = _load(score)
    holdout = set(holdout_dates_from_cf(DEFAULT_CF))
    metrics = _btc_metrics_from_eval(ev)
    return {
        "engine": "gemini_per_date_30d",
        "days": days,
        "status": "ok",
        "steps": steps,
        "comparable_to_30d_panel": True,
        "paths": {
            "per_date": str(per_date),
            "score": str(score),
            "eval": str(ev_out),
        },
        "metrics": metrics,
        "holdout7": _holdout_wrong_dir_count(score_doc, holdout),
    }


def run_gemini_single_shot(*, model: str, timeout: int) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    out_hyp = WORK / "hypothesis_gemini_single_shot.json"
    if not DEFAULT_BUNDLE.is_file():
        return {
            "engine": "gemini_single_shot",
            "status": "skipped",
            "reason": "missing_bundle",
            "comparable_to_30d_panel": False,
        }
    p = _run(
        [
            "scripts/generate_btrack_hypothesis_prophecy_v1.py",
            "--bundle",
            _rel(DEFAULT_BUNDLE),
            "--score-json",
            _rel(DEFAULT_SCORE),
            "--use-cloud-gemini",
            "--model",
            model,
            "--timeout",
            str(timeout),
            "--output",
            _rel(out_hyp),
        ]
    )
    if p.returncode != 0:
        return {
            "engine": "gemini_single_shot",
            "status": "failed",
            "comparable_to_30d_panel": False,
            "stderr_tail": (p.stderr or "")[-2000:],
            "note": "API/key/quota or generate failure; not a panel benchmark.",
        }
    doc = _load(out_hyp)
    pred = doc.get("prediction") if isinstance(doc.get("prediction"), dict) else {}
    meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
    return {
        "engine": "gemini_single_shot",
        "status": "ok",
        "comparable_to_30d_panel": False,
        "prediction": {
            "instrument": pred.get("instrument"),
            "direction": pred.get("direction"),
            "confidence": pred.get("confidence"),
        },
        "llm_model": meta.get("llm_model"),
        "hypothesis_path": str(out_hyp),
        "note": "Single-shot only; full swap needs per-date gemini adapter (future).",
    }


def _verdict(candidates: list[dict[str, Any]]) -> str:
    ok_30 = next(
        (c for c in candidates if c.get("engine") == "baseline_ensemble" and c.get("days") == 30),
        {},
    )
    m = ok_30.get("metrics") if isinstance(ok_30.get("metrics"), dict) else {}
    if ok_30.get("status") != "ok":
        return "harness_incomplete"
    gem = next((c for c in candidates if c.get("engine") == "gemini_per_date_30d"), {})
    gm = gem.get("metrics") if isinstance(gem.get("metrics"), dict) else {}
    if gem.get("status") == "ok" and not gem.get("dry_run"):
        if gm.get("beats_frozen_baseline") and gm.get("alert_1_pass"):
            return "gemini_per_date_holdout_review_required"
        if gm.get("beats_frozen_baseline"):
            return "gemini_per_date_beats_baseline_alert1_fail"
    if m.get("beats_frozen_baseline") and m.get("alert_1_pass"):
        return "holdout_review_required"
    if m.get("beats_frozen_baseline"):
        return "beats_baseline_alert1_fail"
    return "no_baseline_beat"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--include-180d", action="store_true")
    ap.add_argument("--include-gemini", action="store_true", help="Gemini single-shot smoke (paid API)")
    ap.add_argument(
        "--include-gemini-per-date",
        action="store_true",
        help="Gemini per-date 30d panel (paid API; max 30 calls, retry/backoff)",
    )
    ap.add_argument("--gemini-model", default="gemini-2.5-flash")
    ap.add_argument("--gemini-timeout", type=int, default=120)
    ap.add_argument("--gemini-sleep-sec", type=float, default=2.5)
    ap.add_argument("--gemini-max-retries", type=int, default=3)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Write plan only; no subprocess (CI / path check).",
    )
    args = ap.parse_args()

    if not args.ensemble_config.is_file():
        print(f"Missing ensemble config: {args.ensemble_config}", file=sys.stderr)
        return 2
    if not DEFAULT_BTC.is_file() or not DEFAULT_KOSPI.is_file():
        print("Missing BTC/KOSPI CSV under research/market_data/", file=sys.stderr)
        return 2

    plan = {
        "engines": ["baseline_ensemble"]
        + (["gemini_per_date_30d"] if args.include_gemini_per_date else []),
        "windows": [30] + ([180] if args.include_180d else []),
        "include_gemini": bool(args.include_gemini),
        "include_gemini_per_date": bool(args.include_gemini_per_date),
        "frozen_baseline_headline": FROZEN_BASELINE_HEADLINE,
    }
    if args.dry_run:
        report = {
            "schema": "btrack_model_swap_harness_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "dry_run": True,
            "plan": plan,
            "auto_promote": False,
            "operator_lines": [
                "- [MKM-MODEL-SWAP] dry-run plan only; frozen harness; no promote.",
            ],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")
        return 0

    results: list[dict[str, Any]] = []
    results.append(run_baseline_ensemble_window(days=30, cfg=args.ensemble_config))
    if args.include_180d:
        results.append(run_baseline_ensemble_window(days=180, cfg=args.ensemble_config))

    gemini_row: dict[str, Any] | None = None
    gemini_pd_row: dict[str, Any] | None = None
    if args.include_gemini_per_date:
        gemini_pd_row = run_gemini_per_date_window(
            days=30,
            model=args.gemini_model,
            timeout=args.gemini_timeout,
            sleep_sec=args.gemini_sleep_sec,
            max_retries=args.gemini_max_retries,
        )
        results.append(gemini_pd_row)
    if args.include_gemini:
        gemini_row = run_gemini_single_shot(model=args.gemini_model, timeout=args.gemini_timeout)
        results.append(gemini_row)

    verdict = _verdict(results)
    report = {
        "schema": "btrack_model_swap_harness_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "lg_hs_gate": "pending_external (lg_hs_meeting_followup_v1.json unchanged)",
        "frozen_harness": {
            "baseline_headline_30d": FROZEN_BASELINE_HEADLINE,
            "alert_1_floor": ALERT_1_FLOOR,
            "ensemble_config_readonly": str(args.ensemble_config),
            "holdout_7_dates": holdout_dates_from_cf(DEFAULT_CF),
        },
        "plan": plan,
        "candidates": results,
        "verdict": verdict,
        "auto_promote": False,
        "operator_lines": [],
    }

    b30 = next((r for r in results if r.get("engine") == "baseline_ensemble" and r.get("days") == 30), {})
    m30 = b30.get("metrics") if isinstance(b30.get("metrics"), dict) else {}
    report["operator_lines"] = [
        "- [MKM-MODEL-SWAP] frozen harness; ensemble/Track A untouched; auto_promote=false.",
        (
            f"- [MKM-MODEL-SWAP] baseline_ensemble 30d: headline "
            f"{m30.get('price_directional_hit_rate')} "
            f"A1={'pass' if m30.get('alert_1_pass') else 'fail'} "
            f"vs frozen {FROZEN_BASELINE_HEADLINE:.1%}"
        ),
    ]
    if args.include_180d:
        b180 = next(
            (r for r in results if r.get("engine") == "baseline_ensemble" and r.get("days") == 180),
            {},
        )
        m180 = b180.get("metrics") if isinstance(b180.get("metrics"), dict) else {}
        report["operator_lines"].append(
            f"- [MKM-MODEL-SWAP] baseline_ensemble 180d: headline {m180.get('price_directional_hit_rate')}"
        )
    if gemini_pd_row:
        gpm = gemini_pd_row.get("metrics") if isinstance(gemini_pd_row.get("metrics"), dict) else {}
        report["operator_lines"].append(
            f"- [MKM-MODEL-SWAP] gemini_per_date_30d: {gemini_pd_row.get('status')} "
            f"headline={gpm.get('price_directional_hit_rate')} "
            f"A1={'pass' if gpm.get('alert_1_pass') else 'fail'} "
            f"vs frozen {FROZEN_BASELINE_HEADLINE:.1%}"
        )
    if gemini_row:
        report["operator_lines"].append(
            f"- [MKM-MODEL-SWAP] gemini_single_shot: {gemini_row.get('status')} "
            "(not 30d panel comparable)"
        )
    report["operator_lines"].append(f"- [MKM-MODEL-SWAP] verdict={verdict}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0 if b30.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
