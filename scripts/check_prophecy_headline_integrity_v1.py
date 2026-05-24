#!/usr/bin/env python3
"""B-track: Observe prophecy headline KPI integrity (frozen batch, low hit rate, eval/score skew).

Does not change score builder, promotion gates, or live trading. Infrastructure errors exit 1;
semantic headline warnings exit 0 with optional info webhook.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HIT_EVAL = Path("docs/final/artifacts/prophecy_hit_rate_eval_latest.json")
DEFAULT_SCORE = Path("reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json")
DEFAULT_GATES = Path("docs/final/artifacts/prophecy_promotion_gates_v1_latest.json")
DEFAULT_STRATEGY = Path("reports/btrack_prophecy_strategy_comparison_v1_latest.json")
DEFAULT_OUT = Path("reports/prophecy_headline_integrity_observation_latest.json")
DEFAULT_DEDUP = Path("reports/prophecy_headline_integrity_dedup_state_v1.json")


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.strptime(ts.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _uniform_direction(rows: list[Any]) -> tuple[bool, str | None, int]:
    preds = [
        str(r.get("predicted_direction") or "")
        for r in rows
        if isinstance(r, dict) and r.get("predicted_direction")
    ]
    if not preds:
        return False, None, 0
    counts = Counter(preds)
    dominant, n = counts.most_common(1)[0]
    if len(counts) == 1 and n >= 10:
        return True, dominant, n
    return False, dominant if len(counts) == 1 else None, len(preds)


def _fingerprint(flags: list[str], hit_rate: float | None) -> str:
    hr = f"{hit_rate:.4f}" if hit_rate is not None else "na"
    raw = "|".join(sorted(flags)) + f"|hr={hr}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _dedup_allows(fp: str, state: dict[str, Any], now: datetime, window: timedelta) -> bool:
    if state.get("last_fingerprint") != fp:
        return True
    last = _parse_utc(str(state.get("last_fired_utc") or ""))
    if last is None:
        return True
    return (now - last) >= window


def _webhook(skip: bool) -> str:
    if skip:
        return ""
    if (os.getenv("MKM_PROPHECY_HEADLINE_SKIP_WEBHOOK") or "").strip().lower() in {"1", "true", "yes", "on"}:
        return ""
    return (os.getenv("MKM_PROPHECY_HEADLINE_WEBHOOK_URL") or os.getenv("OPS_ALARM_WEBHOOK_URL") or "").strip()


def _post(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            code = int(getattr(resp, "status", 0) or 0)
            return 200 <= code < 300, f"http_status={code}"
    except error.HTTPError as exc:
        return False, f"http_error_{exc.code}"
    except error.URLError as exc:
        return False, f"url_error_{exc.reason}"
    except OSError as exc:
        return False, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--hit-eval-json", type=Path, default=DEFAULT_HIT_EVAL)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--gates-json", type=Path, default=DEFAULT_GATES)
    ap.add_argument("--strategy-json", type=Path, default=DEFAULT_STRATEGY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dedup-state-json", type=Path, default=DEFAULT_DEDUP)
    ap.add_argument("--min-hit-rate", type=float, default=0.35)
    ap.add_argument("--max-eval-score-skew-hours", type=float, default=6.0)
    ap.add_argument("--dedup-hours", type=float, default=24.0)
    ap.add_argument("--skip-webhook", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    hit_path = args.hit_eval_json if args.hit_eval_json.is_absolute() else root / args.hit_eval_json
    score_path = args.score_json if args.score_json.is_absolute() else root / args.score_json
    gates_path = args.gates_json if args.gates_json.is_absolute() else root / args.gates_json
    strategy_path = args.strategy_json if args.strategy_json.is_absolute() else root / args.strategy_json
    out_path = args.out_json if args.out_json.is_absolute() else root / args.out_json
    dedup_path = args.dedup_state_json if args.dedup_state_json.is_absolute() else root / args.dedup_state_json

    now = datetime.now(timezone.utc)
    generated = _iso_now()

    if not hit_path.is_file():
        print(f"[FATAL] Missing hit eval: {hit_path}")
        return 1

    try:
        hit_eval = _load(hit_path)
    except json.JSONDecodeError as exc:
        print(f"[FATAL] Invalid hit eval JSON: {exc}")
        return 1

    if hit_eval.get("schema") != "prophecy_hit_rate_eval_report_v2":
        print("[FATAL] hit eval schema must be prophecy_hit_rate_eval_report_v2")
        return 1

    metrics = hit_eval.get("metrics") if isinstance(hit_eval.get("metrics"), dict) else {}
    hit_rate = metrics.get("price_directional_hit_rate")
    n_eval = metrics.get("n_evaluated")

    score_doc: dict[str, Any] = {}
    if score_path.is_file():
        try:
            score_doc = _load(score_path)
        except json.JSONDecodeError:
            score_doc = {}

    inputs_score = score_doc.get("inputs") if isinstance(score_doc.get("inputs"), dict) else {}
    meta_score = score_doc.get("meta") if isinstance(score_doc.get("meta"), dict) else {}
    rows = score_doc.get("rows") if isinstance(score_doc.get("rows"), list) else []

    eval_ts = _parse_utc(str(hit_eval.get("generated_at_utc") or ""))
    score_ts = _parse_utc(str(score_doc.get("generated_at_utc") or ""))
    skew_hours: float | None = None
    if eval_ts and score_ts:
        skew_hours = abs((score_ts - eval_ts).total_seconds()) / 3600.0

    flags: list[str] = []
    if hit_rate is not None and float(hit_rate) < float(args.min_hit_rate):
        flags.append("LOW_HEADLINE_HIT_RATE")
    per_date_absent = inputs_score.get("per_date_direction_json") in (None, "")
    if per_date_absent:
        flags.append("PER_DATE_DIRECTION_ABSENT")
        if meta_score.get("frozen_prediction_note"):
            flags.append("FROZEN_HYPOTHESIS_BATCH_NOTED")
    uniform, dom_dir, n_preds = _uniform_direction(rows)
    if uniform and dom_dir:
        flags.append(f"UNIFORM_PREDICTED_DIRECTION_{dom_dir.upper()}")
    if skew_hours is not None and skew_hours > float(args.max_eval_score_skew_hours):
        flags.append("EVAL_SCORE_TIMESTAMP_SKEW")

    gates = _load(gates_path) if gates_path.is_file() else {}
    if gates.get("combined_all_passed") is True and hit_rate is not None and float(hit_rate) < float(args.min_hit_rate):
        flags.append("WF_GATE_PASS_VS_LOW_HEADLINE_DIVERGENCE")

    strategy = _load(strategy_path) if strategy_path.is_file() else {}
    verdict = strategy.get("verdict") if isinstance(strategy.get("verdict"), dict) else {}
    if verdict.get("myeongni_sasang_as_headline_striker") == "reject_for_now":
        flags.append("STRATEGY_VERDICT_REJECT_HEADLINE_STRIKER")

    out: dict[str, Any] = {
        "schema": "prophecy_headline_integrity_observation_v1",
        "version": "1.0.0",
        "generated_at_utc": generated,
        "hypothesis_tier": "B",
        "research_only": True,
        "observation_only": True,
        "headline_instrument": (hit_eval.get("inputs") or {}).get("headline_instrument"),
        "metrics": {
            "price_directional_hit_rate": hit_rate,
            "n_evaluated": n_eval,
            "min_hit_rate_threshold": float(args.min_hit_rate),
        },
        "paths": {
            "hit_eval_json": str(hit_path),
            "score_json": str(score_path),
            "gates_json": str(gates_path) if gates_path.is_file() else None,
            "strategy_json": str(strategy_path) if strategy_path.is_file() else None,
        },
        "timestamps": {
            "hit_eval_generated_at_utc": hit_eval.get("generated_at_utc"),
            "score_generated_at_utc": score_doc.get("generated_at_utc"),
            "eval_score_skew_hours": round(skew_hours, 3) if skew_hours is not None else None,
        },
        "score_inputs": {
            "per_date_direction_json": inputs_score.get("per_date_direction_json"),
            "effective_instrument": inputs_score.get("effective_instrument"),
            "recent_trading_days": inputs_score.get("recent_trading_days"),
        },
        "uniform_prediction": {
            "is_uniform": uniform,
            "direction": dom_dir,
            "n_rows_with_prediction": n_preds,
        },
        "promotion_gates": {
            "combined_all_passed": gates.get("combined_all_passed"),
            "outcome_class": gates.get("outcome_class"),
        },
        "strategy_verdict_excerpt": {
            "myeongni_sasang_as_headline_striker": verdict.get("myeongni_sasang_as_headline_striker"),
            "track_a_live_auto_promote": verdict.get("track_a_live_auto_promote"),
        },
        "warning_flags": flags,
        "operator_banner_ko": "[B-track / HYPO] 헤드라인 적중·WF 게이트 불일치 관측 — 실매매·Track A 자동 승격 없음",
    }

    if not flags:
        out["status"] = "HEADLINE_OK"
        out["webhook"] = {"status": "skipped_no_warnings"}
        _write(out_path, out)
        print(f"WROTE: {out_path} status=HEADLINE_OK")
        return 0

    out["status"] = "HEADLINE_WARN"
    fp = _fingerprint(flags, float(hit_rate) if hit_rate is not None else None)
    out["alert_fingerprint"] = fp

    dedup_state = _load(dedup_path) if dedup_path.is_file() else {}
    allow = _dedup_allows(fp, dedup_state, now, timedelta(hours=float(args.dedup_hours)))
    url = _webhook(args.skip_webhook)
    wh: dict[str, Any] = {"status": "skipped_dedup_guard", "fingerprint": fp, "configured": bool(url)}

    if allow and url:
        payload = {
            "event": "prophecy_headline_integrity_observation_v1",
            "grade": "MKM_PROPHECY_HEADLINE_WARN",
            "generated_at_utc": generated,
            "hypothesis_tier": "B",
            "research_only": True,
            "warning_flags": flags,
            "price_directional_hit_rate": hit_rate,
            "n_evaluated": n_eval,
            "combined_all_passed": gates.get("combined_all_passed"),
            "per_date_direction_json": inputs_score.get("per_date_direction_json"),
            "uniform_direction": dom_dir,
            "eval_score_skew_hours": skew_hours,
            "operator_banner_ko": out["operator_banner_ko"],
            "alert_fingerprint": fp,
        }
        ok, detail = _post(url, payload)
        wh["status"] = "posted" if ok else f"failed:{detail}"
        wh["post_ok"] = ok
        wh["detail"] = detail
        if ok:
            _write(
                dedup_path,
                {
                    "schema": "prophecy_headline_integrity_dedup_state_v1",
                    "last_fingerprint": fp,
                    "last_fired_utc": generated,
                },
            )
            out["status"] = "ALERT_FIRED"
    elif allow and not url:
        wh["status"] = "skipped_no_webhook"
        out["status"] = "HEADLINE_WARN_NO_WEBHOOK"
    else:
        out["status"] = "HEADLINE_WARN_DEDUP_GUARDED"

    out["webhook"] = wh
    _write(out_path, out)
    print(f"WROTE: {out_path} status={out['status']} flags={flags}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
