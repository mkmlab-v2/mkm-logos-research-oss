#!/usr/bin/env python3
"""[HYPO] V2 ensemble / lens-feature recovery grid (not neutral_bps panel sweep).

Sweeps ``btrack_lens_ensemble_v1.json`` muscle (weights_v2, v2 rules, min_direction_confidence)
then runs the standard 180d recommended eval chain with fixed neutral_bps (instrument anchor).

On first honest ``combined_all_passed``, copies artifacts to recommended_chain *_latest paths and
optionally invokes ``Run-BtrackEnsembleV2PromotionBundle_v1.ps1 -SkipEvalRun``.

research_only — does not enable live trading or lower promotion thresholds.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DIRS_DEFAULT = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
OUT = ROOT / "reports/btrack_lens_v2_recovery_sweep_v1_latest.json"
WORK = ROOT / "reports/btrack_lens_v2_recovery_work"
REC = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
PROMO_PS1 = ROOT / "scripts/Run-BtrackEnsembleV2PromotionBundle_v1.ps1"


def _obs(g: dict, track: str, gid: str) -> dict:
    for x in (g.get("tracks") or {}).get(track, {}).get("gates") or []:
        if x.get("gate_id") == gid:
            return x.get("observed") or {}
    return {}


def _candidates() -> list[dict[str, Any]]:
    """Ensemble-muscle grid (small, interpretable)."""
    rows: list[dict[str, Any]] = [{"slug": "baseline", "patch": {}}]
    for floor in (0.10, 0.12, 0.18):
        rows.append({"slug": f"floor_{str(floor).replace('.', 'p')}", "patch": {"rules": {"v2": {"min_confidence_floor": floor}}}})
    for mdc in (0.12, 0.15, 0.22):
        rows.append(
            {
                "slug": f"mdc_{str(mdc).replace('.', 'p')}",
                "patch": {"rules": {"min_direction_confidence": mdc}},
            }
        )
    for damp in (0.75, 0.92, 1.0):
        rows.append(
            {
                "slug": f"damp_{str(damp).replace('.', 'p')}",
                "patch": {"rules": {"v2": {"conflict_dampen": damp}}},
            }
        )
    for margin in (0.02, 0.025):
        rows.append(
            {
                "slug": f"margin_{str(margin).replace('.', 'p')}",
                "patch": {"rules": {"tie_break_min_margin": margin}},
            }
        )
    for lb in (3, 8):
        rows.append({"slug": f"lookback_{lb}", "patch": {"rules": {"price_lookback_days": lb}}})
    rows.append(
        {
            "slug": "price_heavy_wv2",
            "patch": {
                "weights_v2": {
                    "price": 0.62,
                    "macro": 0.15,
                    "news": 0.10,
                    "myeongni": 0.05,
                    "sasang": 0.05,
                    "logos": 0.03,
                }
            },
        }
    )
    rows.append(
        {
            "slug": "drop_logos_conflict",
            "patch": {"rules": {"v2": {"drop_logos_on_conflict": True}}},
        }
    )
    price_heavy_patch = {
        "weights_v2": {
            "price": 0.62,
            "macro": 0.15,
            "news": 0.10,
            "myeongni": 0.05,
            "sasang": 0.05,
            "logos": 0.03,
        }
    }
    rows.append(
        {
            "slug": "price_heavy_drop_logos",
            "patch": {
                **price_heavy_patch,
                "rules": {"v2": {"drop_logos_on_conflict": True}},
            },
        }
    )
    rows.append(
        {
            "slug": "price_heavy_floor_0p12",
            "patch": {**price_heavy_patch, "rules": {"v2": {"min_confidence_floor": 0.12}}},
        }
    )
    return rows


def _beat_bull_tune_candidates() -> list[dict[str, Any]]:
    """A-track tune: top ensemble patches × beat-bull train weights (instrument WF uses test_acc >= always-bull)."""
    bases: list[tuple[str, dict[str, Any]]] = [
        (
            "price_heavy_wv2",
            {
                "weights_v2": {
                    "price": 0.62,
                    "macro": 0.15,
                    "news": 0.10,
                    "myeongni": 0.05,
                    "sasang": 0.05,
                    "logos": 0.03,
                }
            },
        ),
        ("drop_logos_conflict", {"rules": {"v2": {"drop_logos_on_conflict": True}}}),
        (
            "price_heavy_drop_logos",
            {
                "weights_v2": {
                    "price": 0.62,
                    "macro": 0.15,
                    "news": 0.10,
                    "myeongni": 0.05,
                    "sasang": 0.05,
                    "logos": 0.03,
                },
                "rules": {"v2": {"drop_logos_on_conflict": True}},
            },
        ),
    ]
    weights = (0.05, 0.08, 0.12, 0.15)
    out: list[dict[str, Any]] = []
    for base_slug, patch in bases:
        for w in weights:
            slug = f"{base_slug}_bbw{str(w).replace('.', 'p')}"
            out.append({"slug": slug, "patch": patch, "beat_bull_train_weight": w, "phase": "beat_bull_tune"})
    return out


def _all_candidates(*, include_beat_bull_tune: bool) -> list[dict[str, Any]]:
    rows = _candidates()
    for r in rows:
        r.setdefault("beat_bull_train_weight", 0.05)
        r.setdefault("phase", "ensemble_muscle")
    if include_beat_bull_tune:
        rows.extend(_beat_bull_tune_candidates())
    return rows


def _deep_merge(base: dict, patch: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def _write_progress(doc: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--neutral-bps", type=float, default=0.4, help="Fixed score neutral band (instrument anchor).")
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--run-promotion-bundle-on-pass", action="store_true", help="Invoke promotion bundle PS1 when combined passes.")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument(
        "--include-beat-bull-tune",
        action="store_true",
        default=True,
        help="Append price_heavy/drop_logos patches × beat-bull train weights (default on).",
    )
    ap.add_argument(
        "--no-beat-bull-tune",
        action="store_true",
        help="Disable beat-bull tune phase (ensemble muscle grid only).",
    )
    args = ap.parse_args()

    if not args.ensemble_config.is_file():
        print(f"Missing ensemble config: {args.ensemble_config}", file=sys.stderr)
        return 2
    if not args.bundle_json.is_file():
        print(f"Missing bundle: {args.bundle_json}", file=sys.stderr)
        return 2

    base_cfg = json.loads(args.ensemble_config.read_text(encoding="utf-8"))
    base_cfg = _deep_merge(base_cfg, {"rules": {"ensemble_mode": "v2_confidence_fusion"}})

    done_slugs: set[str] = set()
    first_pass: dict[str, Any] | None = None
    result_rows: list[dict[str, Any]] = []
    if not args.no_resume and OUT.is_file():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
            result_rows = list(prev.get("rows") or [])
            first_pass = prev.get("first_combined_all_passed")
            for r in result_rows:
                done_slugs.add(str(r.get("slug") or ""))
        except json.JSONDecodeError:
            pass

    WORK.mkdir(parents=True, exist_ok=True)
    build_dirs = ROOT / "scripts/build_btrack_ensemble_per_date_directions_v1.py"
    include_tune = bool(args.include_beat_bull_tune) and not bool(args.no_beat_bull_tune)
    grid = _all_candidates(include_beat_bull_tune=include_tune)
    n_expected = len(grid)

    for cand in grid:
        slug = str(cand["slug"])
        bbw = float(cand.get("beat_bull_train_weight") or 0.05)
        if slug in done_slugs:
            print(f"skip {slug} (resume)", flush=True)
            continue
        cfg = _deep_merge(base_cfg, cand.get("patch") or {})
        cfg_path = WORK / f"ensemble_{slug}.json"
        dirs_path = WORK / f"directions_{slug}.json"
        gates_path = WORK / f"gates_{slug}.json"
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

        rc = subprocess.run(
            [
                sys.executable,
                str(build_dirs),
                "--recent-trading-days",
                str(int(args.recent_trading_days)),
                "--ensemble-config",
                str(cfg_path),
                "--bundle-json",
                str(args.bundle_json),
                "--btc-csv",
                str(DEFAULT_BTC),
                "--kospi-csv",
                str(DEFAULT_KOSPI),
                "--ensemble-mode",
                "v2_confidence_fusion",
                "--output",
                str(dirs_path),
            ],
            cwd=str(ROOT),
            capture_output=True,
        ).returncode
        if rc != 0:
            row = {"slug": slug, "rc": rc, "stage": "build_directions", "combined_all_passed": False}
            result_rows.append(row)
            _write_progress(
                {
                    "rows": result_rows,
                    "first_combined_all_passed": first_pass,
                    "fixed_neutral_bps": args.neutral_bps,
                    "n_expected": n_expected,
                }
            )
            print(f"FAIL {slug} build_directions rc={rc}", flush=True)
            continue

        cmd = [
            sys.executable,
            str(REC),
            "--recent-trading-days",
            str(int(args.recent_trading_days)),
            "--neutral-bps",
            str(float(args.neutral_bps)),
            "--per-date-direction-json",
            str(dirs_path),
            "--include-source-direction-signal",
            "--instrument-beat-bull-train-weight",
            str(bbw),
            "--calibration-note",
            f"btrack_lens_v2_recovery_sweep_v1 slug={slug} bbw={bbw}; inst_fold_beats_always_bull uses test_acc>=control",
            "--gates-out",
            str(gates_path),
            "--score-json",
            str(WORK / f"score_{slug}.json"),
            "--lens-walkforward-out",
            str(WORK / f"lens_{slug}.json"),
            "--instrument-walkforward-out",
            str(WORK / f"inst_{slug}.json"),
        ]
        rc = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        g = json.loads(gates_path.read_text(encoding="utf-8")) if gates_path.is_file() else {}
        lm = _obs(g, "per_date_lens", "lens_wf_mean_test_accuracy").get("mean_test_accuracy")
        im = _obs(g, "instrument_combo", "instrument_wf_mean_test_accuracy").get("mean_test_accuracy")
        ibf = _obs(g, "instrument_combo", "instrument_wf_fraction_folds_beat_always_bull").get(
            "fraction_test_beats_always_bull"
        )
        comb = bool(g.get("combined_all_passed"))
        row = {
            "slug": slug,
            "rc": rc,
            "phase": cand.get("phase") or "ensemble_muscle",
            "beat_bull_train_weight": bbw,
            "patch": cand.get("patch"),
            "lens_mean": lm,
            "inst_mean": im,
            "inst_beat_bull_fold_fraction": ibf,
            "combined_all_passed": comb,
            "strict_passed": g.get("strict_passed"),
            "gates_json": str(gates_path.relative_to(ROOT)).replace("\\", "/"),
        }
        result_rows.append(row)
        _write_progress(
            {
                "schema": "btrack_lens_v2_recovery_sweep_v1",
                "rows": result_rows,
                "first_combined_all_passed": first_pass,
                "fixed_neutral_bps": float(args.neutral_bps),
                "n_expected": n_expected,
                "grid_complete": len(result_rows) >= n_expected,
            }
        )
        mark = "PASS" if comb else "   "
        print(f"{mark} {slug} rc={rc} lens={lm} inst={im} inst_bb={ibf} bbw={bbw}", flush=True)

        if comb and first_pass is None:
            first_pass = row
            _write_progress(
                {
                    "schema": "btrack_lens_v2_recovery_sweep_v1",
                    "rows": result_rows,
                    "first_combined_all_passed": first_pass,
                    "fixed_neutral_bps": float(args.neutral_bps),
                    "n_expected": n_expected,
                    "grid_complete": len(result_rows) >= n_expected,
                }
            )
            # Promote winning row to recommended_chain latest paths (honest copy, no gate edit).
            import shutil

            shutil.copy2(dirs_path, DIRS_DEFAULT)
            shutil.copy2(gates_path, ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json")
            shutil.copy2(WORK / f"score_{slug}.json", ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json")
            shutil.copy2(WORK / f"lens_{slug}.json", ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json")
            shutil.copy2(
                WORK / f"inst_{slug}.json",
                ROOT / "reports/prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json",
            )
            (ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json").write_text(
                gates_path.read_text(encoding="utf-8"), encoding="utf-8"
            )
            if args.run_promotion_bundle_on_pass and PROMO_PS1.is_file():
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(PROMO_PS1),
                        "-SkipEvalRun",
                    ],
                    cwd=str(ROOT),
                )
            break

    doc = {
        "schema": "btrack_lens_v2_recovery_sweep_v1",
        "rows": result_rows,
        "first_combined_all_passed": first_pass,
        "fixed_neutral_bps": float(args.neutral_bps),
        "n_expected": n_expected,
        "include_beat_bull_tune": include_tune,
        "grid_complete": len(result_rows) >= n_expected,
        "note": "Ensemble-muscle + optional beat-bull tune; instrument WF fold beats always-bull uses test_acc>=control; strict 0.55 dual.",
    }
    _write_progress(doc)
    print(f"WROTE {OUT} grid_complete={doc['grid_complete']} first_pass={bool(first_pass)}")
    return 0 if first_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
