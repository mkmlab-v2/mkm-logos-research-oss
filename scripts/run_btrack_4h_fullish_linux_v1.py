#!/usr/bin/env python3
"""Linux-friendly 4h B-track fullish chain for VPS.

Purpose:
- Avoid PowerShell-only orchestration on Linux VPS.
- Keep chain resilient: refresh market CSV -> generate -> score -> eval -> health.
- Uses only Python scripts already deployed on VPS.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen


ROOT = Path("/opt/bitcoin-trading")
ART = ROOT / "docs" / "final" / "artifacts"
MD = ROOT / "research" / "market_data"
LOG = ROOT / "logs" / "btrack_4h_fullish_runner.log"
BFX_1D_URL = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1d&limit=300"


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{_utc_now()}] {msg}\n")


def _ensure_minimal_inputs() -> StepResult:
    ART.mkdir(parents=True, exist_ok=True)
    MD.mkdir(parents=True, exist_ok=True)
    bundle = ART / "btrack_llm_input_bundle_latest.json"
    cfg = ART / "btrack_lens_ensemble_v1.json"
    if not bundle.exists():
        bundle.write_text(
            json.dumps({"schema": "btrack_llm_input_bundle_v1", "artifacts": {}}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if not cfg.exists():
        cfg.write_text(
            json.dumps(
                {
                    "weights": {"price": 1.0, "macro": 0.0, "news": 0.0, "myeongni_sasang": 0.0},
                    "rules": {
                        "price_instrument": "btc",
                        "price_lookback_days": 5,
                        "tie_break_min_margin": 0.03,
                        "neutral_penalty": -0.1,
                        "max_neutral_streak_before_recalibration": 3,
                        "tie_breaker_order": ["price", "macro", "news", "myeongni_sasang"],
                        "enforce_btc_only_guard": True,
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return StepResult("ensure_minimal_inputs", True, "bundle/config ready")


def _refresh_daily_csv() -> StepResult:
    try:
        raw = urlopen(BFX_1D_URL, timeout=15).read().decode("utf-8")
        arr = json.loads(raw)
        if not isinstance(arr, list) or len(arr) < 30:
            return StepResult("refresh_daily_csv", False, "insufficient klines")
        rows: list[dict[str, Any]] = []
        for k in arr:
            ts = int(k[0]) // 1000
            d = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            rows.append(
                {
                    "date": d,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
            )
        for fn in ("btc_daily_external_yf.csv", "kospi_daily_external_yf.csv"):
            p = MD / fn
            with p.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume"])
                w.writeheader()
                w.writerows(rows)
        return StepResult("refresh_daily_csv", True, f"rows={len(rows)}")
    except Exception as e:  # noqa: BLE001
        return StepResult("refresh_daily_csv", False, str(e))


def _run_step(name: str, cmd: list[str]) -> StepResult:
    p = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if p.returncode == 0:
        return StepResult(name, True, "ok")
    err = (p.stderr or p.stdout or "").strip()
    err = err[-500:]
    return StepResult(name, False, f"rc={p.returncode} {err}")


def _apply_confidence_cap_by_sample_size() -> StepResult:
    hyp_path = ART / "btrack_hypothesis_prophecy_latest.json"
    eval_path = ART / "prophecy_hit_rate_eval_latest.json"
    if not hyp_path.is_file() or not eval_path.is_file():
        return StepResult("confidence_cap_guard", False, "missing hypothesis/eval artifact")
    try:
        hyp = json.loads(hyp_path.read_text(encoding="utf-8"))
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return StepResult("confidence_cap_guard", False, f"json_decode:{e}")

    pred = hyp.get("prediction") if isinstance(hyp.get("prediction"), dict) else {}
    metrics = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    if not isinstance(pred, dict) or not isinstance(metrics, dict):
        return StepResult("confidence_cap_guard", False, "invalid payload shape")

    try:
        n = int(metrics.get("n_evaluated") or 0)
        old_conf = float(pred.get("confidence") or 0.5)
    except (TypeError, ValueError):
        return StepResult("confidence_cap_guard", False, "invalid confidence/n")

    # Small-sample anti-overconfidence caps.
    if n < 5:
        cap = 0.55
    elif n < 20:
        cap = 0.65
    else:
        cap = 0.80

    new_conf = min(old_conf, cap)
    pred["confidence"] = round(new_conf, 4)
    hyp["prediction"] = pred
    runtime_meta = hyp.get("runtime_meta") if isinstance(hyp.get("runtime_meta"), dict) else {}
    runtime_meta["confidence_cap_guard"] = {
        "enabled": True,
        "n_evaluated": n,
        "cap": cap,
        "old_confidence": round(old_conf, 4),
        "new_confidence": round(new_conf, 4),
    }
    hyp["runtime_meta"] = runtime_meta
    hyp_path.write_text(json.dumps(hyp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return StepResult("confidence_cap_guard", True, f"n={n} cap={cap} conf={old_conf:.4f}->{new_conf:.4f}")


def _write_confidence_cap_policy_simulation() -> StepResult:
    base_conf = 0.9
    cases = [0, 1, 4, 5, 19, 20, 50]
    rows: list[dict[str, Any]] = []
    for n in cases:
        if n < 5:
            cap = 0.55
        elif n < 20:
            cap = 0.65
        else:
            cap = 0.80
        rows.append(
            {
                "n_evaluated": n,
                "cap": cap,
                "base_confidence": base_conf,
                "capped_confidence": min(base_conf, cap),
            }
        )
    out = ART / "btrack_confidence_cap_policy_latest.json"
    out.write_text(
        json.dumps(
            {
                "schema": "btrack_confidence_cap_policy_v1",
                "generated_at_utc": _utc_now(),
                "note": "Boundary simulation for confidence cap guard (n<5, n<20, else).",
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return StepResult("confidence_cap_policy_sim", True, f"rows={len(rows)}")


def main() -> int:
    results: list[StepResult] = []
    results.append(_ensure_minimal_inputs())
    results.append(_refresh_daily_csv())
    results.append(_run_step("generate_hypothesis", [sys.executable, "scripts/generate_btrack_hypothesis_prophecy_v1.py"]))
    results.append(
        _run_step(
            "build_score",
            [
                sys.executable,
                "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                "--btc-csv",
                "research/market_data/btc_daily_external_yf.csv",
                "--kospi-csv",
                "research/market_data/kospi_daily_external_yf.csv",
            ],
        )
    )
    results.append(
        _run_step(
            "eval_hit_rate",
            [
                sys.executable,
                "scripts/eval_prophecy_hit_rate_v1.py",
                "--run-mode",
                "price",
                "--score-json",
                "docs/final/artifacts/btrack_prophecy_score_latest.json",
            ],
        )
    )
    results.append(_apply_confidence_cap_by_sample_size())
    results.append(_write_confidence_cap_policy_simulation())
    results.append(_run_step("health_check", [sys.executable, "scripts/check_btrack_4h_health_v1.py"]))

    ok = all(r.ok for r in results)
    summary = {
        "schema": "btrack_4h_fullish_runner_v1",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "steps": [{"name": r.name, "ok": r.ok, "detail": r.detail} for r in results],
    }
    out = ART / "btrack_4h_fullish_runner_latest.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_log(f"ok={ok} steps=" + ",".join(f"{r.name}:{'ok' if r.ok else 'fail'}" for r in results))
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
