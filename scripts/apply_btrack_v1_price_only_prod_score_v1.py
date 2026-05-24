#!/usr/bin/env python3
"""Apply v1_price_only ensemble profile to prod btrack_prophecy_score JSON (human-approved).

Backs up SSOT score, rebuilds via generate → build_btrack_prophecy_score_from_ohlcv chain.
Does NOT enable Track A or live trading.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SCORE = ART / "btrack_prophecy_score_latest.json"
DEFAULT_BACKUP = ART / "btrack_prophecy_score_pre_v1_price_only_apply_latest.json"
DEFAULT_CFG = ART / "btrack_lens_ensemble_v1.json"
DEFAULT_BUNDLE = ART / "btrack_llm_input_bundle_latest.json"
DEFAULT_REPORT = ROOT / "reports/btrack_v1_price_only_prod_apply_v1_latest.json"
PROFILE = "v1_price_only"
GENERATOR = ROOT / "scripts/generate_btrack_hypothesis_prophecy_v1.py"
BUILD_SCORE = ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"
EVAL_HIT = ROOT / "scripts/eval_prophecy_hit_rate_v1.py"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    cp = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return int(cp.returncode)


def _profile_cfg(base: dict[str, Any]) -> dict[str, Any]:
    cfg = json.loads(json.dumps(base, ensure_ascii=False))
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    rules["ensemble_mode"] = "v1"
    rules["price_instrument"] = "btc"
    rules["enforce_btc_only_guard"] = True
    cfg["rules"] = rules
    cfg["weights"] = {"price": 1.0, "macro": 0.0, "news": 0.0, "myeongni_sasang": 0.0}
    return cfg


def _eval_headline(score_json: Path) -> dict[str, Any]:
    cp = subprocess.run(
        [
            sys.executable,
            str(EVAL_HIT),
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
    if cp.returncode != 0:
        return {"error": (cp.stderr or cp.stdout or "")[-500:]}
    try:
        doc = json.loads((cp.stdout or "").strip())
    except json.JSONDecodeError:
        return {"error": "invalid eval json"}
    m = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
    try:
        hit = float(m.get("price_directional_hit_rate"))
    except (TypeError, ValueError):
        hit = None
    return {
        "price_directional_hit_rate": hit,
        "n_evaluated": int(m.get("n_evaluated") or 0),
        "alert_1_pass": hit is not None and hit >= 0.5,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--backup-json", type=Path, default=DEFAULT_BACKUP)
    ap.add_argument("--config-json", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument(
        "--strict-30d-alert1",
        action="store_true",
        help="Rollback if post-apply 30d ALERT_1 fails (no commander override).",
    )
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for p in (args.score_json, args.config_json, args.bundle_json, KOSPI, BTC):
        if not p.is_file():
            print(f"Missing required path: {p}", file=sys.stderr)
            return 2

    pre_eval = _eval_headline(args.score_json)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "profile": PROFILE,
                    "pre_eval": pre_eval,
                    "score_json": str(args.score_json),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    args.backup_json.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.score_json, args.backup_json)
    print(f"BACKUP: {args.backup_json.resolve()}")

    base = json.loads(args.config_json.read_text(encoding="utf-8-sig"))
    cfg_doc = _profile_cfg(base)

    with tempfile.TemporaryDirectory(prefix="v1_price_only_apply_") as td:
        tdp = Path(td)
        cfg_path = tdp / "cfg.json"
        hyp_path = tdp / "hyp.json"
        built_path = tdp / "score_built.json"
        cfg_path.write_text(json.dumps(cfg_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        if _run(
            [
                sys.executable,
                str(GENERATOR),
                "--bundle",
                str(args.bundle_json),
                "--score-json",
                str(args.score_json),
                "--ensemble-config",
                str(cfg_path),
                "--output",
                str(hyp_path),
            ]
        ) != 0:
            return 1

        if _run(
            [
                sys.executable,
                str(BUILD_SCORE),
                "--hypothesis-json",
                str(hyp_path),
                "--kospi-csv",
                str(KOSPI),
                "--btc-csv",
                str(BTC),
                "--output",
                str(built_path),
                "--recent-trading-days",
                str(args.recent_trading_days),
            ]
        ) != 0:
            return 1

        shutil.copy2(built_path, args.score_json)

    post_eval = _eval_headline(args.score_json)
    human_override = not args.strict_30d_alert1
    if not human_override and not post_eval.get("alert_1_pass"):
        shutil.copy2(args.backup_json, args.score_json)
        print("ROLLBACK: 30d ALERT_1 fail without override", file=sys.stderr)
        return 1

    built_doc = json.loads(args.score_json.read_text(encoding="utf-8-sig"))
    if isinstance(built_doc.get("meta"), dict):
        built_doc["meta"]["ensemble_profile_applied"] = PROFILE
        built_doc["meta"]["human_prod_apply_at_utc"] = _now()
        built_doc["meta"]["human_reviewer"] = args.reviewer
        built_doc["meta"]["human_override_30d_alert1"] = human_override
    args.score_json.write_text(json.dumps(built_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "btrack_v1_price_only_prod_apply_v1",
        "generated_at_utc": _now(),
        "profile": PROFILE,
        "reviewer": args.reviewer,
        "score_json": str(args.score_json.relative_to(ROOT)).replace("\\", "/"),
        "backup_score_json": str(args.backup_json.relative_to(ROOT)).replace("\\", "/"),
        "recent_trading_days": args.recent_trading_days,
        "human_override_30d_alert1": human_override,
        "pre_apply_eval": pre_eval,
        "post_apply_eval": post_eval,
        "track_a_promotion": False,
        "live_trading": False,
        "research_only": False,
        "note_ko": "지휘관 승인 v1_price_only prod score 적용. Track A·실매매 자동 합선 없음.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.score_json.resolve()}")
    print(f"WROTE: {args.report.resolve()}")
    print(
        f"post_hit={post_eval.get('price_directional_hit_rate')} "
        f"alert1={post_eval.get('alert_1_pass')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
