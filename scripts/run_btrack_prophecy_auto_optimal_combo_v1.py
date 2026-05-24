#!/usr/bin/env python3
"""[HYPO] Auto-search best B-track combo from current on-disk state (research_only).

Orchestrates existing sweeps against live SSOT paths:
  - Prod ensemble baseline (eval_prophecy_hit_rate on score JSON)
  - Ensemble fusion profiles (run_btrack_ensemble_fusion_ablation_v1.py)
  - Lens combo strategies (run_prophecy_lens_combo_backtest_v1.py)
  - Auxiliary post-ensemble variants (btrack_wrong_dir_auxiliary_grid_*_latest.json)

Does NOT auto-promote to Track A or mutate production score JSON unless --apply-best-ensemble
(research temp build only). Default: recommendation artifact only.
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
DEFAULT_SCORE_30 = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_SCORE_180 = ROOT / "reports/btrack_prophecy_score_recommended_180d_v1.json"
DEFAULT_ENSEMBLE_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_GRID_180 = ROOT / "reports/btrack_wrong_dir_auxiliary_grid_180d_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_prophecy_auto_optimal_combo_v1_latest.json"
SCHEMA = "btrack_prophecy_auto_optimal_combo_v1"

FUSION_SCRIPT = ROOT / "scripts/run_btrack_ensemble_fusion_ablation_v1.py"
LENS_COMBO_SCRIPT = ROOT / "scripts/run_prophecy_lens_combo_backtest_v1.py"
EVAL_SCRIPT = ROOT / "scripts/eval_prophecy_hit_rate_v1.py"
ALERT1_THRESHOLD = 0.5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def _eval_headline(score_json: Path, *, days_label: str) -> dict[str, Any] | None:
    if not score_json.is_file():
        return None
    cp = subprocess.run(
        [
            sys.executable,
            str(EVAL_SCRIPT),
            "--run-mode",
            "price",
            "--score-json",
            str(score_json),
            "--headline-instrument",
            "btc",
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    code = int(cp.returncode)
    out = cp.stdout or ""
    if code != 0:
        return {"error": (out or "")[-500:], "window": days_label}
    try:
        doc = json.loads((out or "").strip())
    except json.JSONDecodeError:
        return {"error": "invalid eval json", "window": days_label}
    m = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
    rate = m.get("price_directional_hit_rate")
    try:
        hit = float(rate)
    except (TypeError, ValueError):
        return None
    return {
        "window": days_label,
        "score_json": str(score_json.relative_to(ROOT)).replace("\\", "/"),
        "price_directional_hit_rate": hit,
        "n_evaluated": int(m.get("n_evaluated") or 0),
        "price_hits": int(m.get("price_hits") or 0),
        "alert_1_pass": hit >= ALERT1_THRESHOLD,
        "candidate_type": "prod_baseline",
        "candidate_id": f"prod_baseline_{days_label}",
    }


def _implied_all_row(active_hit: float, n_active: int, n_days: int) -> float | None:
    if n_days <= 0:
        return None
    return round((active_hit * n_active) / n_days, 6)


def _candidates_from_lens_combo(doc: dict[str, Any], *, window: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in doc.get("ranked_strategies") or []:
        if not isinstance(row, dict):
            continue
        m = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        n_days = int(m.get("n_days") or 0)
        n_active = int(m.get("n_active_days") or 0)
        try:
            active_hit = float(m.get("directional_hit_rate_active") or 0)
        except (TypeError, ValueError):
            active_hit = 0.0
        implied = _implied_all_row(active_hit, n_active, n_days)
        out.append(
            {
                "candidate_type": "lens_combo_research",
                "candidate_id": f"lens_{row.get('strategy_id')}_{window}",
                "window": window,
                "strategy_id": row.get("strategy_id"),
                "directional_hit_rate_active": active_hit,
                "n_active_days": n_active,
                "n_days": n_days,
                "implied_all_row_hit_rate": implied,
                "alert_1_pass": implied is not None and implied >= ALERT1_THRESHOLD,
                "promotable_to_track_a": False,
                "note": "Parallel vote harness; does not replace prod ensemble score JSON.",
            }
        )
    return out


def _candidates_from_fusion(doc: dict[str, Any], *, window: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in doc.get("rows") or []:
        if not isinstance(row, dict) or not row.get("eligible"):
            continue
        try:
            hit = float(row.get("price_directional_hit_rate"))
        except (TypeError, ValueError):
            continue
        profile = str(row.get("profile") or "")
        out.append(
            {
                "candidate_type": "ensemble_profile_rebuild",
                "candidate_id": f"ensemble_{profile}_{window}",
                "window": window,
                "profile": profile,
                "ensemble_mode": row.get("ensemble_mode"),
                "price_directional_hit_rate": hit,
                "n_evaluated": int(row.get("n_evaluated") or 0),
                "alert_1_pass": hit >= ALERT1_THRESHOLD,
                "promotable_to_track_a": False,
                "note": "Requires hypothesis regen + score rebuild; human gate before any apply.",
            }
        )
    return out


def _candidates_from_aux_grid(doc: dict[str, Any] | None, *, window: str) -> list[dict[str, Any]]:
    if not doc:
        return []
    met_key = f"metrics_{window}" if window != "30" else "metrics_30d"
    if window == "180":
        met_key = "metrics_180d"
    out: list[dict[str, Any]] = []
    for row in doc.get("variants") or []:
        if not isinstance(row, dict):
            continue
        m = row.get(met_key) or row.get("metrics_180d") or row.get("metrics_30d")
        if not isinstance(m, dict):
            continue
        try:
            hit = float(m.get("price_directional_hit_rate") or 0)
        except (TypeError, ValueError):
            continue
        h7 = row.get("holdout_7") if isinstance(row.get("holdout_7"), dict) else {}
        tw = row.get("train_wrong_dir") if isinstance(row.get("train_wrong_dir"), dict) else {}
        hw = row.get("holdout_wrong_dir") if isinstance(row.get("holdout_wrong_dir"), dict) else {}
        out.append(
            {
                "candidate_type": "aux_post_ensemble",
                "candidate_id": f"aux_{row.get('slug')}_{window}",
                "window": window,
                "slug": row.get("slug"),
                "price_directional_hit_rate": hit,
                "n_evaluated": int(m.get("n_evaluated") or 0),
                "alert_1_pass": hit >= ALERT1_THRESHOLD,
                "holdout_wrong_dir_neutralized": int(hw.get("neutralized") or 0),
                "train_wrong_dir_neutralized": int(tw.get("neutralized") or 0),
                "holdout7_safe": int(hw.get("neutralized") or 0) >= 7 and int(tw.get("neutralized") or 0) == 0,
                "promotable_to_track_a": False,
                "note": "Post-ensemble shield; headline unchanged on true prod rows.",
            }
        )
    return out


def _pick_best(candidates: list[dict[str, Any]], *, ctype: str, window: str) -> dict[str, Any] | None:
    pool = [c for c in candidates if c.get("candidate_type") == ctype and c.get("window") == window]
    if not pool:
        return None
    return max(pool, key=lambda c: float(c.get("price_directional_hit_rate") or c.get("implied_all_row_hit_rate") or -1))


def _pick_best_lens(candidates: list[dict[str, Any]], *, window: str) -> dict[str, Any] | None:
    pool = [c for c in candidates if c.get("candidate_type") == "lens_combo_research" and c.get("window") == window]
    if not pool:
        return None
    return max(pool, key=lambda c: float(c.get("implied_all_row_hit_rate") or -1))


def _pick_best_aux_safe(candidates: list[dict[str, Any]], *, window: str) -> dict[str, Any] | None:
    pool = [
        c
        for c in candidates
        if c.get("candidate_type") == "aux_post_ensemble"
        and c.get("window") == window
        and c.get("holdout7_safe")
    ]
    if not pool:
        return None
    return max(pool, key=lambda c: float(c.get("price_directional_hit_rate") or -1))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-30", type=Path, default=DEFAULT_SCORE_30)
    ap.add_argument("--score-180", type=Path, default=DEFAULT_SCORE_180)
    ap.add_argument("--grid-180", type=Path, default=DEFAULT_GRID_180)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-fusion", action="store_true")
    ap.add_argument("--skip-lens-combo", action="store_true")
    ap.add_argument("--skip-aux-grid", action="store_true")
    ap.add_argument("--include-180-fusion", action="store_true", help="Also sweep ensemble profiles on 180d panel.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    work = ROOT / "reports" / "_auto_optimal_combo_work"
    fusion_30_out = work / "fusion_ablation_30d.json"
    fusion_180_out = work / "fusion_ablation_180d.json"
    lens_30_out = work / "lens_combo_30d.json"
    lens_180_out = work / "lens_combo_180d.json"

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": True,
                    "score_30": str(args.score_30),
                    "score_180": str(args.score_180),
                },
                ensure_ascii=False,
            )
        )
        return 0

    candidates: list[dict[str, Any]] = []

    b30 = _eval_headline(args.score_30, days_label="30")
    if b30:
        candidates.append(b30)
    b180 = _eval_headline(args.score_180, days_label="180")
    if b180:
        candidates.append(b180)

    if not args.skip_fusion:
        work.mkdir(parents=True, exist_ok=True)
        if _run(
            [
                sys.executable,
                str(FUSION_SCRIPT),
                "--score-json",
                str(args.score_30),
                "--recent-trading-days",
                "30",
                "--output",
                str(fusion_30_out),
            ]
        ) != 0:
            print("WARN: fusion ablation 30d failed", file=sys.stderr)
        else:
            fd = _load(fusion_30_out)
            if fd:
                candidates.extend(_candidates_from_fusion(fd, window="30"))

        if args.include_180_fusion and args.score_180.is_file():
            if _run(
                [
                    sys.executable,
                    str(FUSION_SCRIPT),
                    "--score-json",
                    str(args.score_180),
                    "--recent-trading-days",
                    "180",
                    "--output",
                    str(fusion_180_out),
                ]
            ) != 0:
                print("WARN: fusion ablation 180d failed", file=sys.stderr)
            else:
                fd = _load(fusion_180_out)
                if fd:
                    candidates.extend(_candidates_from_fusion(fd, window="180"))

    if not args.skip_lens_combo:
        work.mkdir(parents=True, exist_ok=True)
        if _run(
            [
                sys.executable,
                str(LENS_COMBO_SCRIPT),
                "--score-json",
                str(args.score_30),
                "--output",
                str(lens_30_out),
            ]
        ) == 0:
            ld = _load(lens_30_out)
            if ld:
                candidates.extend(_candidates_from_lens_combo(ld, window="30"))
        if args.score_180.is_file() and _run(
            [
                sys.executable,
                str(LENS_COMBO_SCRIPT),
                "--score-json",
                str(args.score_180),
                "--output",
                str(lens_180_out),
            ]
        ) == 0:
            ld = _load(lens_180_out)
            if ld:
                candidates.extend(_candidates_from_lens_combo(ld, window="180"))

    if not args.skip_aux_grid:
        gd = _load(args.grid_180)
        candidates.extend(_candidates_from_aux_grid(gd, window="180"))

    best_ens_30 = _pick_best(candidates, ctype="ensemble_profile_rebuild", window="30")
    best_ens_180 = _pick_best(candidates, ctype="ensemble_profile_rebuild", window="180")
    best_lens_30 = _pick_best_lens(candidates, window="30")
    best_lens_180 = _pick_best_lens(candidates, window="180")
    best_aux = _pick_best_aux_safe(candidates, window="180")

    prod_30 = b30.get("price_directional_hit_rate") if b30 else None
    verdict = {
        "auto_promote": False,
        "track_a_promotion": "NO",
        "reason_ko": (
            "자동 탐색은 B-track 연구용이다. ALERT_1(전체행 50%) 미달 시 본선 승격 없음. "
            "최적 ensemble 프로필이 나와도 human review + 게이트 체인 필요."
        ),
    }
    if best_ens_30 and prod_30 is not None:
        uplift = float(best_ens_30["price_directional_hit_rate"]) - float(prod_30)
        verdict["best_ensemble_uplift_vs_prod_30d"] = round(uplift, 6)
        if uplift > 0 and best_ens_30.get("alert_1_pass"):
            verdict["note"] = "ensemble profile beats prod on 30d ablation — still not auto-applied"
        elif best_ens_30.get("alert_1_pass"):
            verdict["note"] = "ensemble passes ALERT_1 on ablation window"
        else:
            verdict["note"] = "no ensemble profile reached ALERT_1 on searched windows"

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "alert_1_threshold": ALERT1_THRESHOLD,
        "inputs": {
            "score_30": str(args.score_30.relative_to(ROOT)).replace("\\", "/"),
            "score_180": str(args.score_180.relative_to(ROOT)).replace("\\", "/"),
            "ensemble_config": str(DEFAULT_ENSEMBLE_CFG.relative_to(ROOT)).replace("\\", "/"),
            "grid_180": str(args.grid_180.relative_to(ROOT)).replace("\\", "/"),
        },
        "candidates": candidates,
        "recommendations": {
            "prod_baseline_30d": b30,
            "prod_baseline_180d": b180,
            "best_ensemble_profile_30d": best_ens_30,
            "best_ensemble_profile_180d": best_ens_180,
            "best_lens_combo_implied_30d": best_lens_30,
            "best_lens_combo_implied_180d": best_lens_180,
            "best_defensive_aux_180d": best_aux,
        },
        "verdict": verdict,
        "operator_lines": [
            f"- [MKM-AUTO-OPT] prod_30d={prod_30:.1%}" if prod_30 is not None else "- [MKM-AUTO-OPT] prod_30d=missing",
            f"- [MKM-AUTO-OPT] best_ensemble_30d={best_ens_30.get('candidate_id') if best_ens_30 else 'none'} "
            f"hit={best_ens_30.get('price_directional_hit_rate') if best_ens_30 else 'n/a'}",
            f"- [MKM-AUTO-OPT] best_lens_implied_180d={best_lens_180.get('candidate_id') if best_lens_180 else 'none'} "
            f"implied={best_lens_180.get('implied_all_row_hit_rate') if best_lens_180 else 'n/a'}",
            f"- [MKM-AUTO-OPT] defensive_aux={best_aux.get('slug') if best_aux else 'none'} auto_promote=false",
        ],
        "rerun": f"py scripts/run_btrack_prophecy_auto_optimal_combo_v1.py --include-180-fusion",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best_ens_30:
        print(
            f"BEST_ENSEMBLE_30={best_ens_30.get('candidate_id')} "
            f"hit={best_ens_30.get('price_directional_hit_rate')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
