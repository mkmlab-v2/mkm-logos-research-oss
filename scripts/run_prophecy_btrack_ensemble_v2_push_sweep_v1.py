#!/usr/bin/env python3
"""Grid search v2 ensemble lane: neutral_bps x instrument policy until dual WF improves.

Runs build per-date v2 directions once, then recommended eval chain per grid cell.
Writes summary with lens/instrument means and combined_all_passed per cell.

B-track / research_only — does not promote to A-track or live.
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
BUILD_DIRS = ROOT / "scripts" / "build_btrack_ensemble_per_date_directions_v1.py"
REC_CHAIN = ROOT / "scripts" / "run_prophecy_btrack_recommended_eval_chain_v1.py"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_SCORE_REF = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_V2_DIRS = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_ensemble_v2_push_sweep_v1_latest.json"
DEFAULT_SWEEP_DIR = ROOT / "reports/btrack_ensemble_v2_push_sweep_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _gate_mean(doc: dict[str, Any] | None, *, track: str, gate_id: str) -> float | None:
    if not isinstance(doc, dict):
        return None
    tr = doc.get("tracks") or {}
    block = tr.get(track) if isinstance(tr, dict) else None
    if not isinstance(block, dict):
        return None
    gates = block.get("gates")
    if not isinstance(gates, list):
        return None
    for g in gates:
        if isinstance(g, dict) and g.get("gate_id") == gate_id:
            obs = g.get("observed") or {}
            if isinstance(obs, dict):
                v = obs.get("mean_test_accuracy")
                if isinstance(v, (int, float)):
                    return float(v)
    return None


def _slug_f(f: float) -> str:
    s = f"{float(f):g}".replace(".", "p")
    return s


def _parse_csv_floats(raw: str) -> list[float]:
    out: list[float] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument(
        "--neutral-bps-grid",
        default="1.5,2,2.5,3,3.5,4,5,6",
        help="Comma-separated neutral_bps values.",
    )
    ap.add_argument(
        "--instrument-variants",
        default="prior|prior,panel+panel_kospi",
        help="Pipe-separated variants: prior | prior,panel+panel_kospi | force_panel",
    )
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPO)
    ap.add_argument("--btc-csv", type=Path, default=None)
    ap.add_argument("--score-ref-json", type=Path, default=DEFAULT_SCORE_REF)
    ap.add_argument("--per-date-v2-json", type=Path, default=DEFAULT_V2_DIRS)
    ap.add_argument("--sweep-dir", type=Path, default=DEFAULT_SWEEP_DIR)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stop-on-combined-pass", action="store_true")
    args = ap.parse_args(argv)

    btc_csv = args.btc_csv
    if btc_csv is None:
        btc_csv = DEFAULT_BTC if DEFAULT_BTC.is_file() else DEFAULT_BTC_FALLBACK

    grid = _parse_csv_floats(str(args.neutral_bps_grid))
    if not grid:
        print("Empty --neutral-bps-grid", file=sys.stderr)
        return 2

    variants_raw = [v.strip() for v in str(args.instrument_variants).split("|") if v.strip()]
    variant_specs: list[dict[str, Any]] = []
    for v in variants_raw:
        if v == "prior":
            variant_specs.append(
                {"id": "prior", "btc_policies": "prior", "panel_kospi": False, "force_panel": False}
            )
        elif v in ("prior,panel+panel_kospi", "prior_panel"):
            variant_specs.append(
                {
                    "id": "prior_panel_kospi",
                    "btc_policies": "prior,panel",
                    "panel_kospi": True,
                    "force_panel": False,
                }
            )
        elif v == "force_panel":
            variant_specs.append(
                {"id": "force_panel", "btc_policies": "prior", "panel_kospi": False, "force_panel": True}
            )
        else:
            print(f"Unknown instrument variant: {v}", file=sys.stderr)
            return 2

    args.sweep_dir.mkdir(parents=True, exist_ok=True)

    rc_dirs = _run(
        [
            sys.executable,
            str(BUILD_DIRS),
            "--bundle-json",
            str(args.bundle_json),
            "--ensemble-config",
            str(args.ensemble_config),
            "--btc-csv",
            str(btc_csv),
            "--kospi-csv",
            str(DEFAULT_KOSPI),
            "--recent-trading-days",
            str(args.recent_trading_days),
            "--ensemble-mode",
            "v2_confidence_fusion",
            "--output",
            str(args.per_date_v2_json),
        ]
    )
    if rc_dirs != 0:
        return rc_dirs

    rows_out: list[dict[str, Any]] = []
    best_combined: dict[str, Any] | None = None
    best_lex: tuple[float, float] | None = None

    for nb in grid:
        for spec in variant_specs:
            vid = str(spec["id"])
            slug = f"nbps_{_slug_f(nb)}_{vid}"
            score_path = args.sweep_dir / f"btrack_prophecy_score_v2push_{slug}.json"
            lens_path = args.sweep_dir / f"prophecy_lens_wf_v2push_{slug}.json"
            inst_path = args.sweep_dir / f"prophecy_inst_wf_v2push_{slug}.json"
            gates_path = args.sweep_dir / f"prophecy_gates_v2push_{slug}.json"

            cmd = [
                sys.executable,
                str(REC_CHAIN),
                "--recent-trading-days",
                str(args.recent_trading_days),
                "--neutral-bps",
                str(float(nb)),
                "--n-folds",
                str(args.n_folds),
                "--hypothesis-json",
                str(args.hypothesis_json),
                "--btc-csv",
                str(btc_csv),
                "--score-json",
                str(score_path),
                "--lens-walkforward-out",
                str(lens_path),
                "--instrument-walkforward-out",
                str(inst_path),
                "--gates-out",
                str(gates_path),
                "--per-date-direction-json",
                str(args.per_date_v2_json),
                "--include-source-direction-signal",
                "--include-expanded-prior-features",
                "--instrument-btc-policies",
                str(spec["btc_policies"]),
                "--calibration-note",
                f"ensemble_v2_push_sweep neutral_bps={nb} variant={vid}",
            ]
            if spec.get("panel_kospi"):
                cmd.append("--instrument-include-panel-kospi-mode")
            if spec.get("force_panel"):
                cmd.append("--instrument-force-panel-policy")

            rc = _run(cmd)
            gates = _load(gates_path)
            lens_m = _gate_mean(gates, track="per_date_lens", gate_id="lens_wf_mean_test_accuracy")
            inst_m = _gate_mean(gates, track="instrument_combo", gate_id="instrument_wf_mean_test_accuracy")
            combined = bool(gates.get("combined_all_passed")) if gates else False

            row = {
                "neutral_bps": float(nb),
                "instrument_variant": vid,
                "exit_code": rc,
                "lens_mean_test_accuracy": lens_m,
                "instrument_mean_test_accuracy": inst_m,
                "combined_all_passed": combined,
                "gates_json": str(gates_path),
                "score_json": str(score_path),
            }
            rows_out.append(row)
            print(
                f"cell nbps={nb} {vid} rc={rc} lens={lens_m} inst={inst_m} combined={combined}",
                file=sys.stderr,
            )

            if rc == 0 and lens_m is not None and inst_m is not None:
                lex = (float(lens_m) + float(inst_m), min(float(lens_m), float(inst_m)))
                if best_lex is None or lex > best_lex:
                    best_lex = lex
                    best_combined = row

            if combined and args.stop_on_combined_pass:
                break
        if args.stop_on_combined_pass and any(r.get("combined_all_passed") for r in rows_out):
            break

    first_pass = next((r for r in rows_out if r.get("combined_all_passed")), None)
    doc = {
        "schema": "btrack_ensemble_v2_push_sweep_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc_now(),
        "recent_trading_days": int(args.recent_trading_days),
        "neutral_bps_grid": grid,
        "instrument_variants": [s["id"] for s in variant_specs],
        "per_date_v2_json": str(args.per_date_v2_json),
        "sweep_dir": str(args.sweep_dir.resolve()),
        "rows": rows_out,
        "best_by_lens_plus_instrument_mean": best_combined,
        "first_combined_all_passed": first_pass,
        "note": "research_only; human gate required before A-track. Threshold 0.55 strict unchanged.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if first_pass:
        print(f"COMBINED PASS: neutral_bps={first_pass['neutral_bps']} variant={first_pass['instrument_variant']}")
    elif best_combined:
        print(
            f"BEST LEX: neutral_bps={best_combined['neutral_bps']} variant={best_combined['instrument_variant']} "
            f"lens={best_combined['lens_mean_test_accuracy']} inst={best_combined['instrument_mean_test_accuracy']}"
        )
    return 0 if rows_out and all(int(r.get("exit_code") or 1) == 0 for r in rows_out) else 1


if __name__ == "__main__":
    raise SystemExit(main())
