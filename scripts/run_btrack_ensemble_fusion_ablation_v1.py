#!/usr/bin/env python3
"""Ablation: ensemble v1 vs v2 confidence fusion × BTC price hit-rate (B-track).

Profiles (research_only):
  v1_baseline          — rules.ensemble_mode=v1 (myeongni+sasang average)
  v2_confidence_fusion — v2_confidence_fusion (separate lenses + conf weights)
  v2_no_logos          — v2 with logos weight 0
  v1_price_only        — v1 price=1, others 0
  v2_price_macro_news  — v2 price+macro+news only

Chain per profile: generate_btrack_hypothesis_prophecy_v1.py → build_btrack_prophecy_score_from_ohlcv.py
→ eval_prophecy_hit_rate_v1.py --run-mode price

Output: reports/btrack_ensemble_fusion_ablation_v1_latest.json
Does not modify live trading or promotion gates.
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
DEFAULT_OUT = ROOT / "reports/btrack_ensemble_fusion_ablation_v1_latest.json"
SCHEMA = "btrack_ensemble_fusion_ablation_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def _profile_cfg(base: dict[str, Any], profile: str) -> dict[str, Any]:
    cfg = json.loads(json.dumps(base, ensure_ascii=False))
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    rules["price_instrument"] = "btc"
    rules["enforce_btc_only_guard"] = True

    if profile == "v1_baseline":
        rules["ensemble_mode"] = "v1"
        cfg["weights"] = {"price": 0.65, "macro": 0.2, "news": 0.1, "myeongni_sasang": 0.05}
    elif profile == "v2_confidence_fusion":
        rules["ensemble_mode"] = "v2_confidence_fusion"
    elif profile == "v2_no_logos":
        rules["ensemble_mode"] = "v2_confidence_fusion"
        cfg["weights_v2"] = {
            "price": 0.58,
            "macro": 0.2,
            "news": 0.14,
            "myeongni": 0.04,
            "sasang": 0.04,
            "logos": 0.0,
        }
    elif profile == "v1_price_only":
        rules["ensemble_mode"] = "v1"
        cfg["weights"] = {"price": 1.0, "macro": 0.0, "news": 0.0, "myeongni_sasang": 0.0}
    elif profile == "v2_price_macro_news":
        rules["ensemble_mode"] = "v2_confidence_fusion"
        cfg["weights_v2"] = {
            "price": 0.7,
            "macro": 0.18,
            "news": 0.12,
            "myeongni": 0.0,
            "sasang": 0.0,
            "logos": 0.0,
        }
    else:
        raise ValueError(f"unknown profile: {profile}")

    cfg["rules"] = rules
    return cfg


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
    prov = doc.get("provenance") if isinstance(doc.get("provenance"), dict) else {}
    return 0, {
        "instrument": pred.get("instrument"),
        "direction": pred.get("direction"),
        "confidence": pred.get("confidence"),
        "ensemble_mode": meta.get("ensemble_mode"),
        "llm_model": prov.get("llm_model"),
        "weighted_score": meta.get("weighted_score"),
        "effective_weights": meta.get("effective_weights"),
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


def _hit_rate(payload: dict[str, Any] | None) -> tuple[float | None, int]:
    if not isinstance(payload, dict):
        return None, 0
    mblock = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    rate = mblock.get("price_directional_hit_rate")
    n_ev = int(mblock.get("n_evaluated") or 0)
    try:
        return float(rate), n_ev
    except (TypeError, ValueError):
        return None, n_ev


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--profiles",
        default="v1_baseline,v2_confidence_fusion,v2_no_logos,v1_price_only,v2_price_macro_news",
    )
    ap.add_argument("--config-json", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--generator", type=Path, default=DEFAULT_GENERATOR)
    ap.add_argument("--build-score-script", type=Path, default=DEFAULT_BUILD_SCORE)
    ap.add_argument("--eval-hit-script", type=Path, default=DEFAULT_EVAL_HIT)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--min-eval-rows", type=int, default=5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    for p in (args.bundle_json, args.config_json, args.score_json, args.kospi_csv, args.btc_csv):
        if not p.is_file():
            print(f"Missing required path: {p}", file=sys.stderr)
            return 2

    base = _load(args.config_json)
    profiles = [x.strip() for x in str(args.profiles).split(",") if x.strip()]

    if args.dry_run:
        print(json.dumps({"ok": True, "profiles": profiles, "dry_run": True}, ensure_ascii=False))
        return 0

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="ensemble_ablation_") as td:
        tdp = Path(td)
        for profile in profiles:
            cfg_doc = _profile_cfg(base, profile)
            cfg_path = tdp / f"{profile}_cfg.json"
            hyp_path = tdp / f"{profile}_hyp.json"
            score_path = tdp / f"{profile}_score.json"
            cfg_path.write_text(json.dumps(cfg_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            g_code, g_res = _run_generator(
                args.generator, args.bundle_json, args.score_json, cfg_path, hyp_path
            )
            row: dict[str, Any] = {
                "profile": profile,
                "ensemble_mode": cfg_doc.get("rules", {}).get("ensemble_mode"),
                "generator_ok": g_code == 0,
                "generator_result": g_res,
            }
            if g_code != 0:
                rows.append(row)
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
                rows.append(row)
                continue

            e_code, e_payload = _run_eval_price(args.eval_hit_script, score_path)
            row["eval_ok"] = e_code == 0
            row["hit_eval_payload"] = e_payload
            rate, n_ev = _hit_rate(e_payload)
            row["price_directional_hit_rate"] = rate
            row["n_evaluated"] = n_ev
            row["eligible"] = rate is not None and n_ev >= args.min_eval_rows
            rows.append(row)

    best_name: str | None = None
    best_rate = -1.0
    for row in rows:
        if not row.get("eligible"):
            continue
        r = float(row["price_directional_hit_rate"])
        if r > best_rate:
            best_rate = r
            best_name = str(row["profile"])

    out_doc = {
        "schema": SCHEMA,
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc_now(),
        "profiles": profiles,
        "recent_trading_days": args.recent_trading_days,
        "min_eval_rows": args.min_eval_rows,
        "promotion_gate_note": "strict walk-forward 0.55 is separate; this is OHLCV price hit-rate ablation only",
        "rows": rows,
        "best_eligible_profile": best_name,
        "best_eligible_hit_rate": best_rate if best_name else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best_name:
        print(f"best_eligible={best_name} hit_rate={best_rate:.4f}")
    else:
        print("best_eligible=none (check rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
