#!/usr/bin/env python3
"""Prophecy Sandbox daily chain — multi-asset / multi-lens matrix (research_only).

Never writes docs/final/artifacts/btrack_prophecy_score_latest.json.
Appends scored rows to reports/sandbox_prophecy_stream_v1.jsonl.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DEFAULT_STREAM = REPORTS / "sandbox_prophecy_stream_v1.jsonl"
DEFAULT_PANEL = REPORTS / "sandbox_prophecy_panel_v1_latest.json"
DEFAULT_CHAIN_REPORT = REPORTS / "sandbox_prophecy_daily_chain_v1_latest.json"
PROD_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
ENSEMBLE_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
GENERATOR = ROOT / "scripts/generate_btrack_hypothesis_prophecy_v1.py"
BUILD_SCORE = ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"
EVAL_HIT = ROOT / "scripts/eval_prophecy_hit_rate_v1.py"
FETCH_BTC = ROOT / "scripts/fetch_btc_yfinance_csv.py"
FETCH_ETH = ROOT / "scripts/fetch_eth_yfinance_csv.py"
FETCH_SOL = ROOT / "scripts/fetch_sol_yfinance_csv.py"
FETCH_GLD = ROOT / "scripts/fetch_gld_yfinance_csv.py"
FETCH_NDX = ROOT / "scripts/fetch_ndx_yfinance_csv.py"
FETCH_QQQ = ROOT / "scripts/fetch_qqq_yfinance_csv.py"
FETCH_KOSPI = ROOT / "scripts/fetch_kospi_yfinance_csv.py"
PHASE3_JOINED = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.jsonl"
PHASE3_EVAL = ROOT / "scripts/sandbox_phase3_sensor_eval_v1.py"
PHASE3_JOIN = ROOT / "scripts/join_btrack_phase3_leading_sensors_score_v1.py"
SASANG_EVAL = ROOT / "scripts/sandbox_sasang_dynamics_eval_v1.py"
BRIEF_BUILD = ROOT / "scripts/build_sandbox_prophecy_brief_v1.py"
ROLLUP_BUILD = ROOT / "scripts/build_sandbox_prophecy_stream_rollup_v1.py"
HOLDOUT_BUILD = ROOT / "scripts/build_sandbox_prophecy_holdout_report_v1.py"
PROMOTION_BUILD = ROOT / "scripts/build_sandbox_prophecy_promotion_research_pack_v1.py"
BRIDGE_DRAFT_BUILD = ROOT / "scripts/build_sandbox_track_a_candidate_bridge_draft_v1.py"
HEALTH_CHECK = ROOT / "scripts/check_prophecy_sandbox_health_v1.py"
PATCH_CALENDAR = ROOT / "scripts/patch_sandbox_prophecy_stream_calendar_v1.py"
DASHBOARD_BUILD = ROOT / "scripts/build_sandbox_prophecy_ops_dashboard_v1.py"
WATCHLIST_WEBHOOK = ROOT / "scripts/dispatch_sandbox_prophecy_watchlist_webhook_v1.py"
ACCUMULATION_BUILD = ROOT / "scripts/build_sandbox_prophecy_accumulation_status_v1.py"
EVIDENCE_MANIFEST = ROOT / "scripts/build_sandbox_prophecy_evidence_manifest_v1.py"
HUMAN_REVIEW_PACK = ROOT / "scripts/build_sandbox_prophecy_human_review_pack_v1.py"
OPERATOR_DIGEST = ROOT / "scripts/build_sandbox_prophecy_operator_digest_v1.py"
ACCUMULATION_GATE_WEBHOOK = ROOT / "scripts/dispatch_sandbox_prophecy_accumulation_gate_webhook_v1.py"
ARTIFACTS_VERIFY = ROOT / "scripts/verify_sandbox_prophecy_artifacts_v1.py"
DAILY_THREAD_SYNC = ROOT / "scripts/athena_daily_thread_log_sync_v1.py"
FETCH_BINANCE_P3 = ROOT / "scripts/fetch_btrack_phase3_binance_micro_daily_v1.py"
DEFAULT_BRIEF = REPORTS / "sandbox_prophecy_brief_v1_latest.json"
DEFAULT_ROLLUP = REPORTS / "sandbox_prophecy_rollup_v1_latest.json"
DEFAULT_WATCHLIST = REPORTS / "sandbox_prophecy_watchlist_v1_latest.json"
DEFAULT_HOLDOUT = REPORTS / "sandbox_prophecy_holdout_report_v1_latest.json"
DEFAULT_PROMOTION = REPORTS / "sandbox_prophecy_promotion_research_pack_v1_latest.json"
DEFAULT_BRIDGE_DRAFT = REPORTS / "sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json"
DEFAULT_HEALTH = REPORTS / "sandbox_prophecy_health_v1_latest.json"
DEFAULT_DASHBOARD = REPORTS / "sandbox_prophecy_ops_dashboard_v1_latest.json"
DEFAULT_ACCUMULATION = REPORTS / "sandbox_prophecy_accumulation_status_v1_latest.json"
DEFAULT_EVIDENCE_MANIFEST = REPORTS / "sandbox_prophecy_evidence_manifest_v1_latest.json"
DEFAULT_HUMAN_REVIEW = REPORTS / "sandbox_prophecy_human_review_pack_v1_latest.json"
DEFAULT_OPERATOR_DIGEST = REPORTS / "sandbox_prophecy_operator_digest_v1_latest.json"
DEFAULT_ARTIFACTS_VERIFY = REPORTS / "sandbox_prophecy_artifacts_verify_v1_latest.json"


def _sync_daily_thread_log(digest_path: Path, thread: int) -> int:
    if not DAILY_THREAD_SYNC.is_file() or not digest_path.is_file():
        return 0
    try:
        doc = json.loads(digest_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return 0
    line = (doc.get("digest_line_ko") or "").strip()
    if not line:
        return 0
    return _run(
        [
            sys.executable,
            str(DAILY_THREAD_SYNC),
            "--thread",
            str(thread),
            "--bullet",
            line,
        ]
    )


def _load_lib():
    spec = importlib.util.spec_from_file_location(
        "sandbox_prophecy_lib_v1", ROOT / "scripts/sandbox_prophecy_lib_v1.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def _eval_headline(score_json: Path, instrument: str) -> dict[str, Any]:
    cp = subprocess.run(
        [
            sys.executable,
            str(EVAL_HIT),
            "--run-mode",
            "price",
            "--score-json",
            str(score_json),
            "--headline-instrument",
            instrument,
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if cp.returncode != 0:
        return {"error": (cp.stderr or cp.stdout or "")[-400:]}
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
        "price_hits": int(m.get("price_hits") or 0),
        "alert_1_pass": hit is not None and hit >= 0.5,
    }


def _load_phase3_eval():
    spec = importlib.util.spec_from_file_location(
        "sandbox_phase3_sensor_eval_v1", PHASE3_EVAL
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _run_phase3_sensor_target(
    lib: Any,
    *,
    target: dict[str, Any],
    joined_jsonl: Path,
    recent_days: int,
) -> dict[str, Any]:
    tid = str(target["target_id"])
    p3 = _load_phase3_eval()
    metrics = p3.eval_phase3_sensor(
        joined_jsonl,
        sensor_z_key=str(target["sensor_z_key"]),
        recent_trading_days=recent_days,
        invert=bool(target.get("invert")),
        deadband=float(target.get("deadband") or 0.0),
    )
    return {
        "schema": "sandbox_prophecy_stream_row_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": lib.SANDBOX_TIER,
        "boundary_ack": True,
        "research_only": True,
        "target_id": tid,
        "asset": target.get("asset"),
        "instrument": "btc",
        "lens_profile": target.get("lens_profile"),
        "mode": "phase3_sensor",
        "recent_trading_days": recent_days,
        "metrics": metrics,
        "paths": {"phase3_joined_jsonl": lib.rel(joined_jsonl)},
        "ok": "error" not in metrics and int(metrics.get("n_evaluated") or 0) > 0,
    }


def _load_sasang_eval():
    spec = importlib.util.spec_from_file_location("sandbox_sasang_dynamics_eval_v1", SASANG_EVAL)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _run_sasang_dynamics_target(
    lib: Any,
    *,
    target: dict[str, Any],
    joined_jsonl: Path,
    recent_days: int,
) -> dict[str, Any]:
    tid = str(target["target_id"])
    sasang = _load_sasang_eval()
    sj = ROOT / str(target.get("sasang_jsonl") or "")
    metrics = sasang.eval_sasang_dynamics(
        joined_jsonl,
        sj,
        strategy=str(target["strategy"]),
        recent_trading_days=recent_days,
    )
    return {
        "schema": "sandbox_prophecy_stream_row_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": lib.SANDBOX_TIER,
        "boundary_ack": True,
        "research_only": True,
        "target_id": tid,
        "asset": target.get("asset"),
        "instrument": "btc",
        "lens_profile": target.get("lens_profile"),
        "mode": "sasang_dynamics",
        "recent_trading_days": recent_days,
        "metrics": metrics,
        "paths": {
            "phase3_joined_jsonl": lib.rel(joined_jsonl),
            "sasang_jsonl": lib.rel(sj) if sj.is_file() else str(target.get("sasang_jsonl")),
        },
        "ok": "error" not in metrics and int(metrics.get("n_evaluated") or 0) > 0,
    }


def _run_target(
    lib: Any,
    *,
    target: dict[str, Any],
    base_cfg: dict[str, Any],
    prod_score: Path,
    bundle: Path,
    kospi: Path,
    recent_days: int,
    tdp: Path,
) -> dict[str, Any]:
    tid = str(target["target_id"])
    profile = str(target["lens_profile"])
    inst = str(target["instrument"])
    headline_inst = str(target.get("asset") or inst)

    cfg_doc = lib.profile_cfg(base_cfg, profile)
    cfg_path = tdp / f"{tid}_cfg.json"
    hyp_path = tdp / f"{tid}_hyp.json"
    score_path = tdp / f"{tid}_score.json"
    cfg_path.write_text(json.dumps(cfg_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if _run(
        [
            sys.executable,
            str(GENERATOR),
            "--bundle",
            str(bundle),
            "--score-json",
            str(prod_score),
            "--ensemble-config",
            str(cfg_path),
            "--output",
            str(hyp_path),
        ]
    ) != 0:
        return {"target_id": tid, "ok": False, "stage": "generate"}

    hyp = json.loads(hyp_path.read_text(encoding="utf-8-sig"))
    hyp = lib.tag_hypothesis_sandbox(hyp, target_id=tid, lens_profile=profile)
    pred = hyp.get("prediction") if isinstance(hyp.get("prediction"), dict) else {}
    pred["instrument"] = inst
    hyp["prediction"] = pred
    hyp_path.write_text(json.dumps(hyp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    btc_csv = target.get("btc_csv")
    build_cmd = [
        sys.executable,
        str(BUILD_SCORE),
        "--hypothesis-json",
        str(hyp_path),
        "--kospi-csv",
        str(kospi),
        "--output",
        str(score_path),
        "--recent-trading-days",
        str(recent_days),
    ]
    if btc_csv:
        bp = ROOT / str(btc_csv)
        if bp.is_file():
            build_cmd.extend(["--btc-csv", str(bp)])
        else:
            return {"target_id": tid, "ok": False, "stage": "build", "error": f"missing {bp}"}

    if _run(build_cmd) != 0:
        return {"target_id": tid, "ok": False, "stage": "build"}

    metrics = _eval_headline(score_path, headline_inst if headline_inst in ("btc", "kospi") else "btc")
    row = {
        "schema": "sandbox_prophecy_stream_row_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": lib.SANDBOX_TIER,
        "boundary_ack": True,
        "research_only": True,
        "target_id": tid,
        "asset": target.get("asset"),
        "instrument": inst,
        "lens_profile": profile,
        "recent_trading_days": recent_days,
        "metrics": metrics,
        "paths": {
            "hypothesis": str(hyp_path),
            "score": str(score_path),
        },
        "ok": "error" not in metrics,
    }
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stream-jsonl", type=Path, default=DEFAULT_STREAM)
    ap.add_argument("--panel-json", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--report", type=Path, default=DEFAULT_CHAIN_REPORT)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--skip-market-fetch", action="store_true")
    ap.add_argument(
        "--refresh-phase3-join",
        action="store_true",
        help="Re-run Phase3 join against prod score (read-only on score body).",
    )
    ap.add_argument(
        "--refresh-phase3-binance",
        action="store_true",
        help="Fetch Binance funding/LS measured JSONL before join (network).",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--backfill-stream-calendar",
        action="store_true",
        help="Backfill snapshot_calendar_date_utc on existing stream rows before append.",
    )
    ap.add_argument("--skip-watchlist-webhook", action="store_true")
    ap.add_argument(
        "--sync-daily-thread-log",
        action="store_true",
        help="Append operator digest line to reports/daily_thread_work_*.md",
    )
    ap.add_argument(
        "--daily-thread",
        type=int,
        default=5,
        help="Thread section number for --sync-daily-thread-log (default 5).",
    )
    ap.add_argument(
        "--skip-artifacts-verify",
        action="store_true",
        help="Skip post-chain artifact bundle verify gate.",
    )
    ap.add_argument(
        "--strict-health",
        action="store_true",
        help="Pass --strict to sandbox health (fail when max_n_calendar_days<3).",
    )
    args = ap.parse_args()

    lib = _load_lib()
    targets = lib.all_targets()

    if not args.dry_run and not args.skip_market_fetch:
        for fetch in (FETCH_KOSPI, FETCH_BTC, FETCH_ETH, FETCH_SOL, FETCH_GLD, FETCH_NDX, FETCH_QQQ):
            if Path(fetch).is_file():
                _run([sys.executable, str(fetch)])

    if not PROD_SCORE.is_file() or not ENSEMBLE_CFG.is_file() or not BUNDLE.is_file():
        print("Missing prod score, ensemble cfg, or bundle", file=sys.stderr)
        return 2
    if not KOSPI.is_file():
        print(f"Missing KOSPI CSV: {KOSPI}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps({"targets": [t["target_id"] for t in targets], "dry_run": True}, indent=2))
        return 0

    if args.backfill_stream_calendar and PATCH_CALENDAR.is_file() and args.stream_jsonl.is_file():
        _run([sys.executable, str(PATCH_CALENDAR), "--stream-jsonl", str(args.stream_jsonl)])

    if args.refresh_phase3_binance and FETCH_BINANCE_P3.is_file():
        rc = _run([sys.executable, str(FETCH_BINANCE_P3)])
        if rc != 0:
            print("Phase3 Binance fetch failed (continuing with cached feeds)", file=sys.stderr)

    if args.refresh_phase3_join:
        rc = _run(
            [
                sys.executable,
                str(PHASE3_JOIN),
                "--score-json",
                str(PROD_SCORE),
                "--out-jsonl",
                str(PHASE3_JOINED),
            ]
        )
        if rc != 0:
            print("Phase3 join failed", file=sys.stderr)
            return rc

    base_cfg = json.loads(ENSEMBLE_CFG.read_text(encoding="utf-8-sig"))
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="prophecy_sandbox_") as td:
        tdp = Path(td)
        for target in targets:
            mode = target.get("mode")
            if mode == "phase3_sensor":
                rows.append(
                    _run_phase3_sensor_target(
                        lib,
                        target=target,
                        joined_jsonl=PHASE3_JOINED,
                        recent_days=args.recent_trading_days,
                    )
                )
            elif mode == "sasang_dynamics":
                rows.append(
                    _run_sasang_dynamics_target(
                        lib,
                        target=target,
                        joined_jsonl=PHASE3_JOINED,
                        recent_days=args.recent_trading_days,
                    )
                )
            else:
                rows.append(
                    _run_target(
                        lib,
                        target=target,
                        base_cfg=base_cfg,
                        prod_score=PROD_SCORE,
                        bundle=BUNDLE,
                        kospi=KOSPI,
                        recent_days=args.recent_trading_days,
                        tdp=tdp,
                    )
                )

    for row in rows:
        lib.finalize_stream_row(row)

    args.stream_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.stream_jsonl.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    ok_n = sum(1 for r in rows if r.get("ok"))
    panel = {
        "schema": "sandbox_prophecy_panel_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": lib.SANDBOX_TIER,
        "research_only": True,
        "prod_score_isolated": True,
        "prod_score_ref": lib.rel(PROD_SCORE),
        "recent_trading_days": args.recent_trading_days,
        "targets": [
            {
                "target_id": r.get("target_id"),
                "asset": r.get("asset"),
                "lens_profile": r.get("lens_profile"),
                "hit_rate": (r.get("metrics") or {}).get("price_directional_hit_rate"),
                "n_evaluated": (r.get("metrics") or {}).get("n_evaluated"),
                "alert_1_pass": (r.get("metrics") or {}).get("alert_1_pass"),
                "ok": r.get("ok"),
            }
            for r in rows
        ],
        "stream_jsonl_ref": lib.rel(args.stream_jsonl),
        "note_ko": "본선 score·실매매·Track A auto_bridge와 격벽. SANDBOX 라벨만 적재.",
    }
    args.panel_json.parent.mkdir(parents=True, exist_ok=True)
    args.panel_json.write_text(json.dumps(panel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if ROLLUP_BUILD.is_file():
        _run(
            [
                sys.executable,
                str(ROLLUP_BUILD),
                "--stream-jsonl",
                str(args.stream_jsonl),
            ]
        )

    if HOLDOUT_BUILD.is_file():
        _run(
            [
                sys.executable,
                str(HOLDOUT_BUILD),
                "--stream-jsonl",
                str(args.stream_jsonl),
            ]
        )

    if ACCUMULATION_BUILD.is_file() and DEFAULT_ROLLUP.is_file():
        _run([sys.executable, str(ACCUMULATION_BUILD)])

    if ACCUMULATION_GATE_WEBHOOK.is_file():
        _run(
            [
                sys.executable,
                str(ACCUMULATION_GATE_WEBHOOK),
                "--notify-one-day-left",
            ]
        )

    if PROMOTION_BUILD.is_file():
        promo_cmd = [
            sys.executable,
            str(PROMOTION_BUILD),
            "--panel-json",
            str(args.panel_json),
        ]
        if DEFAULT_HOLDOUT.is_file():
            promo_cmd.extend(["--holdout-json", str(DEFAULT_HOLDOUT)])
        _run(promo_cmd)

    if BRIDGE_DRAFT_BUILD.is_file():
        _run(
            [
                sys.executable,
                str(BRIDGE_DRAFT_BUILD),
                "--panel-json",
                str(args.panel_json),
            ]
        )

    if HUMAN_REVIEW_PACK.is_file():
        _run([sys.executable, str(HUMAN_REVIEW_PACK)])

    if BRIEF_BUILD.is_file():
        brief_cmd = [sys.executable, str(BRIEF_BUILD), "--panel-json", str(args.panel_json)]
        if DEFAULT_ROLLUP.is_file():
            brief_cmd.extend(["--rollup-json", str(DEFAULT_ROLLUP)])
        if DEFAULT_PROMOTION.is_file():
            brief_cmd.extend(["--promotion-json", str(DEFAULT_PROMOTION)])
        if DEFAULT_BRIDGE_DRAFT.is_file():
            brief_cmd.extend(["--bridge-draft-json", str(DEFAULT_BRIDGE_DRAFT)])
        _run(brief_cmd)

    report: dict[str, Any] = {
        "schema": "sandbox_prophecy_daily_chain_v1",
        "generated_at_utc": panel["generated_at_utc"],
        "ok": ok_n == len(rows),
        "n_targets": len(rows),
        "n_ok": ok_n,
        "stream_jsonl": lib.rel(args.stream_jsonl),
        "panel_json": lib.rel(args.panel_json),
        "brief_json": lib.rel(DEFAULT_BRIEF) if DEFAULT_BRIEF.is_file() else None,
        "rollup_json": lib.rel(DEFAULT_ROLLUP) if DEFAULT_ROLLUP.is_file() else None,
        "watchlist_json": lib.rel(DEFAULT_WATCHLIST) if DEFAULT_WATCHLIST.is_file() else None,
        "holdout_json": lib.rel(DEFAULT_HOLDOUT) if DEFAULT_HOLDOUT.is_file() else None,
        "promotion_research_json": lib.rel(DEFAULT_PROMOTION) if DEFAULT_PROMOTION.is_file() else None,
        "bridge_draft_json": lib.rel(DEFAULT_BRIDGE_DRAFT) if DEFAULT_BRIDGE_DRAFT.is_file() else None,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    health_exit = 0
    if HEALTH_CHECK.is_file():
        health_cmd = [sys.executable, str(HEALTH_CHECK)]
        if args.strict_health:
            health_cmd.append("--strict")
        health_exit = _run(health_cmd)

    if DASHBOARD_BUILD.is_file():
        _run([sys.executable, str(DASHBOARD_BUILD)])

    if not args.skip_watchlist_webhook and WATCHLIST_WEBHOOK.is_file():
        _run([sys.executable, str(WATCHLIST_WEBHOOK)])

    if EVIDENCE_MANIFEST.is_file():
        _run([sys.executable, str(EVIDENCE_MANIFEST)])

    if OPERATOR_DIGEST.is_file():
        _run([sys.executable, str(OPERATOR_DIGEST)])

    artifacts_verify_exit = 0
    if not args.skip_artifacts_verify and ARTIFACTS_VERIFY.is_file():
        artifacts_verify_exit = _run([sys.executable, str(ARTIFACTS_VERIFY)])

    daily_thread_sync_exit = 0
    if args.sync_daily_thread_log:
        daily_thread_sync_exit = _sync_daily_thread_log(DEFAULT_OPERATOR_DIGEST, args.daily_thread)

    report["health_json"] = lib.rel(DEFAULT_HEALTH) if DEFAULT_HEALTH.is_file() else None
    report["health_check_exit_code"] = health_exit
    report["ops_dashboard_json"] = lib.rel(DEFAULT_DASHBOARD) if DEFAULT_DASHBOARD.is_file() else None
    report["accumulation_status_json"] = (
        lib.rel(DEFAULT_ACCUMULATION) if DEFAULT_ACCUMULATION.is_file() else None
    )
    report["evidence_manifest_json"] = (
        lib.rel(DEFAULT_EVIDENCE_MANIFEST) if DEFAULT_EVIDENCE_MANIFEST.is_file() else None
    )
    report["human_review_pack_json"] = (
        lib.rel(DEFAULT_HUMAN_REVIEW) if DEFAULT_HUMAN_REVIEW.is_file() else None
    )
    report["operator_digest_json"] = (
        lib.rel(DEFAULT_OPERATOR_DIGEST) if DEFAULT_OPERATOR_DIGEST.is_file() else None
    )
    report["artifacts_verify_json"] = (
        lib.rel(DEFAULT_ARTIFACTS_VERIFY) if DEFAULT_ARTIFACTS_VERIFY.is_file() else None
    )
    report["artifacts_verify_exit_code"] = artifacts_verify_exit
    report["daily_thread_sync_exit_code"] = daily_thread_sync_exit
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.stream_jsonl.resolve()} (+{len(rows)} rows)")
    print(f"WROTE: {args.panel_json.resolve()}")
    print(f"WROTE: {args.report.resolve()}")
    for r in rows:
        m = r.get("metrics") or {}
        print(
            f"  {r.get('target_id')}: hit={m.get('price_directional_hit_rate')} "
            f"n={m.get('n_evaluated')} ok={r.get('ok')}"
        )
    if artifacts_verify_exit != 0:
        return artifacts_verify_exit
    if daily_thread_sync_exit != 0:
        return daily_thread_sync_exit
    if health_exit != 0:
        return health_exit
    return 0 if ok_n == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
