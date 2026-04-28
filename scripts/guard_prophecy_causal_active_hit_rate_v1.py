#!/usr/bin/env python3
"""Guard active causal-applied score by minimum hit-rate; rollback to backup when breached."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL = ROOT / "docs" / "final" / "artifacts" / "prophecy_hit_rate_eval_latest.json"
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_BACKUP = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_pre_causal_active_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_guard_latest.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_guard_policy_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_policy(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = _load(path)
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Rollback active causal score when hit-rate drops below threshold.")
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--backup-json", type=Path, default=DEFAULT_BACKUP)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--min-hit-rate", type=float, default=0.50)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    eval_path = args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json
    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    backup_path = args.backup_json if args.backup_json.is_absolute() else ROOT / args.backup_json
    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    policy = _load_policy(policy_path)
    min_hit_rate = float(policy.get("min_hit_rate", args.min_hit_rate))
    min_n_for_enforcement = int(policy.get("min_n_evaluated_for_enforcement", 10))

    eval_doc = _load(eval_path)
    metrics = (eval_doc.get("metrics") or {}) if isinstance(eval_doc, dict) else {}
    hit_rate = metrics.get("price_directional_hit_rate")
    n_eval = metrics.get("n_evaluated")
    n_eval_i = int(n_eval or 0)
    hit_rate_f = float(hit_rate or 0.0)
    enforce_enabled = n_eval_i >= min_n_for_enforcement
    should_rollback = hit_rate is not None and enforce_enabled and hit_rate_f < min_hit_rate

    rolled_back = False
    reason = "ok"
    if should_rollback and backup_path.is_file():
        score_doc = _load(backup_path)
        _write(score_path, score_doc)
        rolled_back = True
        reason = "hit_rate_below_threshold_rollback_applied"
    elif should_rollback:
        reason = "hit_rate_below_threshold_but_backup_missing"
    elif hit_rate is not None and not enforce_enabled:
        reason = "insufficient_sample_size_for_enforcement"

    payload = {
        "schema": "prophecy_causal_active_guard_v1",
        "generated_at_utc": _now(),
        "input_eval_json": str(eval_path),
        "score_json": str(score_path),
        "backup_json": str(backup_path),
        "policy_json": str(policy_path),
        "min_hit_rate": min_hit_rate,
        "min_n_evaluated_for_enforcement": min_n_for_enforcement,
        "observed_hit_rate": hit_rate,
        "observed_n_evaluated": n_eval_i,
        "enforcement_enabled": enforce_enabled,
        "should_rollback": bool(should_rollback),
        "rolled_back": bool(rolled_back),
        "reason": reason,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
    }
    _write(out_path, payload)
    print(f"WROTE: {out_path.resolve()}")
    print(
        f"observed_hit_rate={hit_rate} min={min_hit_rate} "
        f"n={n_eval_i} min_n={min_n_for_enforcement} rolled_back={rolled_back}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
