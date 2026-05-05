#!/usr/bin/env python3
"""Apply winning BTC-first ensemble weights from btc_weight_ab_sweep_latest.json.

Default: choose among profiles listed in --candidates (comma-separated) by highest
confidence; ties break in candidate list order (earlier wins).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP = ROOT / "docs/final/artifacts/btc_weight_ab_sweep_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pick_winner(
    sweep: dict[str, Any],
    *,
    candidates: list[str],
) -> tuple[str, dict[str, float], dict[str, Any]]:
    profiles = sweep.get("profiles") if isinstance(sweep.get("profiles"), list) else []
    by_name: dict[str, dict[str, Any]] = {}
    for row in profiles:
        if not isinstance(row, dict):
            continue
        name = str(row.get("profile") or "").strip()
        if name:
            by_name[name] = row

    best_name: str | None = None
    best_conf = -1.0
    best_weights: dict[str, float] = {}
    best_result: dict[str, Any] = {}

    for cand in candidates:
        row = by_name.get(cand)
        if not row:
            continue
        if not bool(row.get("ok")):
            continue
        res = row.get("result") if isinstance(row.get("result"), dict) else {}
        if bool(res.get("guard_blocked")):
            continue
        conf = float(res.get("confidence") or 0.0)
        w = row.get("weights") if isinstance(row.get("weights"), dict) else {}
        if conf > best_conf:
            best_conf = conf
            best_name = cand
            best_weights = {k: float(v) for k, v in w.items() if isinstance(v, (int, float))}
            best_result = dict(res)

    if not best_name or not best_weights:
        raise ValueError("no eligible winner (check sweep ok/guard_blocked/candidates)")
    return best_name, best_weights, best_result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--config-json", type=Path, default=DEFAULT_CFG)
    ap.add_argument(
        "--candidates",
        default="btc_70,btc_80",
        help="Comma-separated profile names to compare (order = tie-break priority).",
    )
    args = ap.parse_args(argv)

    sweep_path = args.sweep_json if args.sweep_json.is_absolute() else ROOT / args.sweep_json
    cfg_path = args.config_json if args.config_json.is_absolute() else ROOT / args.config_json
    sweep = _load(sweep_path)
    cfg = _load(cfg_path)

    cands = [x.strip() for x in str(args.candidates).split(",") if x.strip()]
    name, weights, res = pick_winner(sweep, candidates=cands)

    cfg["weights"] = weights
    cfg["ts_utc"] = _utc_now()
    note = (
        f"Applied btc_weight_ab_sweep winner={name} (candidates={','.join(cands)}); "
        f"confidence={res.get('confidence')} direction={res.get('direction')}."
    )
    cfg["note"] = note

    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"winner": name, "weights": weights, "config": str(cfg_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
