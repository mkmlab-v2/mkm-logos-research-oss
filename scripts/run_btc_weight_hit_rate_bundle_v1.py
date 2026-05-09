#!/usr/bin/env python3
"""BTC-first ensemble profiles × OHLCV → price hit-rate (B-track measurement loop).

For each weight profile (same grid as run_btc_weight_ab_sweep_v1.py):
  1) generate_btrack_hypothesis_prophecy_v1.py (ensemble temp cfg)
  2) build_btrack_prophecy_score_from_ohlcv.py (--hypothesis-json + --btc-csv + --recent-trading-days)
  3) eval_prophecy_hit_rate_v1.py --run-mode price --stdout-only

Writes one consolidated report (default: reports/btrack_btc_weight_hit_rate_bundle_latest.json).
Optional --apply-winner updates docs/final/artifacts/btrack_lens_ensemble_v1.json weights by best **hit rate**
(not confidence — unlike apply_btc_weight_sweep_winner_v1.py).

Does not touch live trading. Requires KOSPI CSV present (build script uses it for trading-date spine).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_GENERATOR = ROOT / "scripts/generate_btrack_hypothesis_prophecy_v1.py"
DEFAULT_BUILD_SCORE = ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"
DEFAULT_EVAL_HIT = ROOT / "scripts/eval_prophecy_hit_rate_v1.py"
DEFAULT_KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/btrack_btc_weight_hit_rate_bundle_latest.json"
FETCH_BTC = ROOT / "scripts/fetch_btc_yfinance_csv.py"
FETCH_KOSPI = ROOT / "scripts/fetch_kospi_yfinance_csv.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _profile_weights(profile: str) -> dict[str, float]:
    m = {
        "btc_65": {"price": 0.65, "macro": 0.2, "news": 0.1, "myeongni_sasang": 0.05},
        "btc_70": {"price": 0.7, "macro": 0.15, "news": 0.1, "myeongni_sasang": 0.05},
        "btc_80": {"price": 0.8, "macro": 0.1, "news": 0.05, "myeongni_sasang": 0.05},
    }
    if profile not in m:
        raise ValueError(f"unknown profile: {profile}")
    return m[profile]


def _run(
    cmd: list[str],
) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def _run_generator(
    generator: Path,
    bundle: Path,
    score: Path,
    cfg: Path,
    out: Path,
) -> tuple[int, dict[str, Any]]:
    code, out_s, err_s = _run(
        [
            sys.executable,
            str(generator),
            "--bundle",
            str(bundle),
            "--score-json",
            str(score),
            "--ensemble-config",
            str(cfg),
            "--output",
            str(out),
        ]
    )
    if code != 0:
        return code, {"stderr": err_s[-4000:], "stdout": out_s[-2000:]}
    doc = _load(out)
    pred = doc.get("prediction") if isinstance(doc.get("prediction"), dict) else {}
    meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
    guard = meta.get("btc_only_guard") if isinstance(meta.get("btc_only_guard"), dict) else {}
    return 0, {
        "instrument": pred.get("instrument"),
        "direction": pred.get("direction"),
        "confidence": pred.get("confidence"),
        "weighted_score": meta.get("weighted_score"),
        "guard_blocked": guard.get("blocked"),
    }


def _run_build_score(
    build_script: Path,
    hypothesis: Path,
    kospi_csv: Path,
    btc_csv: Path,
    out_score: Path,
    recent_days: int,
) -> int:
    code, _, err = _run(
        [
            sys.executable,
            str(build_script),
            "--hypothesis-json",
            str(hypothesis),
            "--kospi-csv",
            str(kospi_csv),
            "--btc-csv",
            str(btc_csv),
            "--output",
            str(out_score),
            "--recent-trading-days",
            str(recent_days),
        ]
    )
    if code != 0 and err:
        print(err[-3000:], file=sys.stderr)
    return code


def _run_eval_price(eval_script: Path, score_json: Path) -> tuple[int, dict[str, Any] | None]:
    code, out, err = _run(
        [
            sys.executable,
            str(eval_script),
            "--run-mode",
            "price",
            "--score-json",
            str(score_json),
            "--stdout-only",
        ]
    )
    if code != 0:
        return code, {"parse_error": err[-2000:] if err else None}
    text = (out or "").strip()
    if not text:
        return 2, {"parse_error": "empty stdout"}
    try:
        doc = json.loads(text)
        return 0, doc if isinstance(doc, dict) else None
    except json.JSONDecodeError:
        return 2, {"parse_error": "invalid JSON on stdout", "stdout_tail": text[-2000:]}


def _pick_hit_rate_winner(
    rows: list[dict[str, Any]],
    *,
    min_eval_rows: int,
) -> tuple[str | None, dict[str, Any]]:
    best_name: str | None = None
    best_rate = -1.0
    best_conf = -1.0
    best_row: dict[str, Any] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("profile") or "").strip()
        if not name or not row.get("generator_ok"):
            continue
        res = row.get("generator_result") if isinstance(row.get("generator_result"), dict) else {}
        if bool(res.get("guard_blocked")):
            continue
        metrics = row.get("hit_eval_payload") if isinstance(row.get("hit_eval_payload"), dict) else {}
        mblock = metrics.get("metrics") if isinstance(metrics.get("metrics"), dict) else {}
        rate = mblock.get("price_directional_hit_rate")
        n_ev = int(mblock.get("n_evaluated") or 0)
        if rate is None or n_ev < min_eval_rows:
            continue
        try:
            rf = float(rate)
        except (TypeError, ValueError):
            continue
        conf = float(res.get("confidence") or 0.0)
        if rf > best_rate or (rf == best_rate and conf > best_conf):
            best_rate = rf
            best_conf = conf
            best_name = name
            best_row = row

    return best_name, best_row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profiles", default="btc_65,btc_70,btc_80")
    ap.add_argument("--config-json", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument(
        "--score-json",
        type=Path,
        default=DEFAULT_SCORE,
        help="Frozen score JSON for generator input (same as daily chain).",
    )
    ap.add_argument("--generator", type=Path, default=DEFAULT_GENERATOR)
    ap.add_argument("--build-score-script", type=Path, default=DEFAULT_BUILD_SCORE)
    ap.add_argument("--eval-hit-script", type=Path, default=DEFAULT_EVAL_HIT)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--min-eval-rows", type=int, default=5, help="Minimum n_evaluated for --apply-winner eligibility.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--apply-winner",
        action="store_true",
        help="Write winning weights into --config-json (hit-rate winner).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Validate inputs only; no subprocess work.")
    ap.add_argument(
        "--refresh-market-data",
        action="store_true",
        help="Run fetch_kospi_yfinance_csv.py and fetch_btc_yfinance_csv.py first (network).",
    )
    args = ap.parse_args(argv)

    if args.refresh_market_data:
        rc1, _, e1 = _run([sys.executable, str(FETCH_KOSPI)])
        rc2, _, e2 = _run([sys.executable, str(FETCH_BTC)])
        if rc1 != 0:
            print(e1[-2000:], file=sys.stderr)
            return 2
        if rc2 != 0:
            print(e2[-2000:], file=sys.stderr)
            return 2

    if not args.bundle_json.is_file():
        print(f"Missing bundle: {args.bundle_json}", file=sys.stderr)
        return 2
    if not args.config_json.is_file():
        print(f"Missing ensemble config: {args.config_json}", file=sys.stderr)
        return 2
    if not args.score_json.is_file():
        print(f"Missing score JSON (for generator): {args.score_json}", file=sys.stderr)
        return 2
    if not args.kospi_csv.is_file():
        print(f"Missing KOSPI CSV: {args.kospi_csv}", file=sys.stderr)
        return 2
    if not args.btc_csv.is_file():
        print(f"Missing BTC CSV: {args.btc_csv}", file=sys.stderr)
        return 2

    base = _load(args.config_json)
    base_rules = base.get("rules") if isinstance(base.get("rules"), dict) else {}
    base_rules["price_instrument"] = "btc"
    base_rules["enforce_btc_only_guard"] = True
    base["rules"] = base_rules

    profiles = [p.strip() for p in str(args.profiles).split(",") if p.strip()]
    if args.dry_run:
        print(json.dumps({"ok": True, "profiles": profiles, "dry_run": True}, ensure_ascii=False))
        return 0

    profile_rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="btc_hit_bundle_") as td:
        tdp = Path(td)
        for p in profiles:
            cfg = dict(base)
            cfg["weights"] = _profile_weights(p)
            cfg_path = tdp / f"{p}_cfg.json"
            hyp_path = tdp / f"{p}_hypothesis.json"
            score_path = tdp / f"{p}_score.json"
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            g_code, g_rec = _run_generator(args.generator, args.bundle_json, args.score_json, cfg_path, hyp_path)
            row: dict[str, Any] = {
                "profile": p,
                "weights": cfg["weights"],
                "generator_ok": g_code == 0,
                "generator_result": g_rec,
            }
            if g_code != 0:
                row["hit_eval_payload"] = None
                profile_rows.append(row)
                continue

            b_code = _run_build_score(
                args.build_score_script,
                hyp_path,
                args.kospi_csv,
                args.btc_csv,
                score_path,
                args.recent_trading_days,
            )
            row["build_score_ok"] = b_code == 0
            if b_code != 0:
                row["hit_eval_payload"] = None
                profile_rows.append(row)
                continue

            ev_code, ev_doc = _run_eval_price(args.eval_hit_script, score_path)
            row["hit_eval_ok"] = ev_code == 0
            row["hit_eval_payload"] = ev_doc
            profile_rows.append(row)

    winner_name, winner_row = _pick_hit_rate_winner(profile_rows, min_eval_rows=args.min_eval_rows)
    summary = {
        "winner_profile": winner_name,
        "winner_hit_rate": None,
        "winner_n_evaluated": None,
        "apply_winner_eligible": winner_name is not None,
    }
    if winner_row:
        pl = winner_row.get("hit_eval_payload") if isinstance(winner_row.get("hit_eval_payload"), dict) else {}
        mb = pl.get("metrics") if isinstance(pl.get("metrics"), dict) else {}
        summary["winner_hit_rate"] = mb.get("price_directional_hit_rate")
        summary["winner_n_evaluated"] = mb.get("n_evaluated")

    payload: dict[str, Any] = {
        "schema": "btc_weight_hit_rate_bundle_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "profiles": profiles,
            "bundle_json": str(args.bundle_json.relative_to(ROOT)),
            "base_config_json": str(args.config_json.relative_to(ROOT)),
            "generator_score_json": str(args.score_json.relative_to(ROOT)),
            "kospi_csv": str(args.kospi_csv.relative_to(ROOT)),
            "btc_csv": str(args.btc_csv.relative_to(ROOT)),
            "recent_trading_days": args.recent_trading_days,
            "min_eval_rows_for_apply": args.min_eval_rows,
        },
        "summary": summary,
        "profiles": profile_rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")

    if args.apply_winner:
        if not winner_name:
            print("apply-winner: no eligible winner (hit rate / n_evaluated / guard).", file=sys.stderr)
            return 3
        wrow = winner_row.get("weights") if isinstance(winner_row.get("weights"), dict) else {}
        if not wrow:
            print("apply-winner: missing weights on winner row.", file=sys.stderr)
            return 3
        cfg_live = _load(args.config_json)
        cfg_live["weights"] = {k: float(v) for k, v in wrow.items()}
        cfg_live["ts_utc"] = _utc_now()
        note = (
            f"Applied btc_weight_hit_rate_bundle winner={winner_name} "
            f"(hit_rate={summary.get('winner_hit_rate')} n={summary.get('winner_n_evaluated')}); "
            f"report={args.output.relative_to(ROOT)}."
        )
        cfg_live["note"] = note
        args.config_json.write_text(json.dumps(cfg_live, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"UPDATED ensemble config: {args.config_json.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
