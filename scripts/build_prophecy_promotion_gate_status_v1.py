#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
THRESH_PATH = ROOT / "docs" / "final" / "artifacts" / "prophecy_go_nogo_thresholds_v1_latest.json"
PRICE_EVAL_PATH = ROOT / "docs" / "final" / "artifacts" / "prophecy_hit_rate_eval_latest.json"
BRIER_EVAL_PATH = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_brier_eval_latest.json"
OUT_PATH = ROOT / "reports" / "prophecy_promotion_gate_status_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int | None:
    try:
        if v is None:
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    th = _read_json(THRESH_PATH)
    pe = _read_json(PRICE_EVAL_PATH)
    be = _read_json(BRIER_EVAL_PATH)

    windows = th.get("windows") if isinstance(th.get("windows"), dict) else {}
    gates = th.get("gates") if isinstance(th.get("gates"), dict) else {}

    pe_metrics = pe.get("metrics") if isinstance(pe.get("metrics"), dict) else {}
    be_metrics = be.get("metrics") if isinstance(be.get("metrics"), dict) else {}

    hit_rate = _to_float(pe_metrics.get("price_directional_hit_rate"))
    n_eval = _to_int(pe_metrics.get("n_evaluated"))
    brier = _to_float(be_metrics.get("mean_brier_score"))
    brier_n = _to_int(be_metrics.get("n_evaluated"))

    reasons: list[str] = []

    min_n_total = _to_int(windows.get("minimum_n_total"))
    if min_n_total is not None and (n_eval is None or n_eval < min_n_total):
        reasons.append(f"insufficient_n_total:{n_eval}<{min_n_total}")

    hit_gate = gates.get("price_directional_hit_rate") if isinstance(gates.get("price_directional_hit_rate"), dict) else {}
    hit_watch = _to_float(hit_gate.get("watch"))
    if hit_watch is not None and (hit_rate is None or hit_rate < hit_watch):
        reasons.append(f"hit_rate_below_watch:{hit_rate}<{hit_watch}")

    brier_gate = gates.get("brier_score_mean") if isinstance(gates.get("brier_score_mean"), dict) else {}
    brier_watch = _to_float(brier_gate.get("watch_at_or_below"))
    if brier_watch is not None and (brier is None or brier > brier_watch):
        reasons.append(f"brier_above_watch:{brier}>{brier_watch}")

    # Conservative policy: GO only if no blocking reason; WATCH otherwise.
    decision = "GO" if not reasons else "WATCH"

    out = {
        "schema": "prophecy_promotion_gate_status_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "thresholds_path": str(THRESH_PATH.relative_to(ROOT)),
            "price_eval_path": str(PRICE_EVAL_PATH.relative_to(ROOT)),
            "brier_eval_path": str(BRIER_EVAL_PATH.relative_to(ROOT)),
        },
        "metrics": {
            "price_directional_hit_rate": hit_rate,
            "n_evaluated": n_eval,
            "mean_brier_score": brier,
            "brier_n_evaluated": brier_n,
        },
        "decision": decision,
        "reasons": reasons,
        "note": "B-track gate status only; no direct order trigger wiring.",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote={OUT_PATH.as_posix()} decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
