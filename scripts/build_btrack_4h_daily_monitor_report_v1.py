#!/usr/bin/env python3
"""Build daily monitor report for VPS 4h B-track loop."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/opt/bitcoin-trading")
ART = ROOT / "docs" / "final" / "artifacts"
LOG = ROOT / "logs" / "btrack_4h_daily_monitor.log"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _append_log(payload: dict[str, Any]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _read_last_log_payload() -> dict[str, Any]:
    if not LOG.is_file():
        return {}
    try:
        lines = LOG.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    for line in reversed(lines):
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return {}


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    hyp = _read_json(ART / "btrack_hypothesis_prophecy_latest.json")
    eval_doc = _read_json(ART / "prophecy_hit_rate_eval_latest.json")
    health = _read_json(ART / "btrack_4h_health_latest.json")
    runner = _read_json(ART / "btrack_4h_fullish_runner_latest.json")

    pred = hyp.get("prediction") if isinstance(hyp.get("prediction"), dict) else {}
    rt = hyp.get("runtime_meta") if isinstance(hyp.get("runtime_meta"), dict) else {}
    guard = rt.get("confidence_cap_guard") if isinstance(rt.get("confidence_cap_guard"), dict) else {}
    metrics = eval_doc.get("metrics") if isinstance(eval_doc.get("metrics"), dict) else {}
    prev = _read_last_log_payload()
    prev_eval = prev.get("evaluation") if isinstance(prev.get("evaluation"), dict) else {}
    prev_pred = prev.get("prediction") if isinstance(prev.get("prediction"), dict) else {}

    cur_n = _to_float(metrics.get("n_evaluated"))
    cur_hit = _to_float(metrics.get("price_directional_hit_rate"))
    cur_conf = _to_float(pred.get("confidence"))
    prev_n = _to_float(prev_eval.get("n_evaluated"))
    prev_hit = _to_float(prev_eval.get("price_hit_rate"))
    prev_conf = _to_float(prev_pred.get("confidence"))

    delta = {
        "from_generated_at_utc": prev.get("generated_at_utc"),
        "delta_n_evaluated": (cur_n - prev_n) if cur_n is not None and prev_n is not None else None,
        "delta_price_hit_rate": (cur_hit - prev_hit) if cur_hit is not None and prev_hit is not None else None,
        "delta_confidence": (cur_conf - prev_conf) if cur_conf is not None and prev_conf is not None else None,
    }

    payload = {
        "schema": "btrack_4h_daily_monitor_report_v1",
        "generated_at_utc": _utc_now(),
        "status": {
            "health_ok": bool(health.get("ok", False)),
            "runner_ok": bool(runner.get("ok", False)),
        },
        "prediction": {
            "direction": pred.get("direction"),
            "confidence": pred.get("confidence"),
        },
        "evaluation": {
            "n_evaluated": metrics.get("n_evaluated"),
            "price_hit_rate": metrics.get("price_directional_hit_rate"),
            "price_hits": metrics.get("price_hits"),
        },
        "delta": delta,
        "confidence_guard": guard,
    }

    out = ART / "btrack_4h_daily_monitor_report_latest.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_log(payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
