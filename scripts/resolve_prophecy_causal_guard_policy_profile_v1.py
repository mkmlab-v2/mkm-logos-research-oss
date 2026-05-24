#!/usr/bin/env python3
"""Resolve active causal guard policy from A/B profile presets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prophecy_hit_rate_ssot_v1 import DAILY_OPERATIONAL  # noqa: E402

DEFAULT_PROFILES = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_guard_policy_profiles_v1_latest.json"
DEFAULT_EVAL = DAILY_OPERATIONAL
DEFAULT_WF = ROOT / "docs" / "final" / "artifacts" / "prophecy_instrument_combo_walkforward_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_guard_policy_v1_latest.json"
DEFAULT_DECISION = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_active_guard_policy_decision_latest.json"
DEFAULT_LOG = ROOT / "reports" / "prophecy_causal_active_guard_policy_decision_log.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve active guard policy using A/B profiles.")
    ap.add_argument("--profiles-json", type=Path, default=DEFAULT_PROFILES)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--walkforward-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--profile", type=str, default="", help="Force profile name. If empty, auto/default applies.")
    ap.add_argument("--out-policy-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-decision-json", type=Path, default=DEFAULT_DECISION)
    ap.add_argument("--append-log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    profiles_path = args.profiles_json if args.profiles_json.is_absolute() else ROOT / args.profiles_json
    eval_path = args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json
    wf_path = args.walkforward_json if args.walkforward_json.is_absolute() else ROOT / args.walkforward_json
    out_policy_path = args.out_policy_json if args.out_policy_json.is_absolute() else ROOT / args.out_policy_json
    out_decision_path = args.out_decision_json if args.out_decision_json.is_absolute() else ROOT / args.out_decision_json
    log_path = args.append_log_jsonl if args.append_log_jsonl.is_absolute() else ROOT / args.append_log_jsonl

    profiles_doc = _load(profiles_path)
    profiles = profiles_doc.get("profiles") if isinstance(profiles_doc, dict) else None
    if not isinstance(profiles, dict) or not profiles:
        raise SystemExit("profiles_json must contain non-empty profiles map")

    default_profile = str(profiles_doc.get("default_profile") or "conservative")
    selected = (args.profile or os.getenv("MKM_PROPHECY_GUARD_PROFILE") or "").strip()

    eval_doc = _load(eval_path) if eval_path.is_file() else {}
    wf_doc = _load(wf_path) if wf_path.is_file() else {}
    hit_rate = _safe_float(((eval_doc.get("metrics") or {}) if isinstance(eval_doc, dict) else {}).get("price_directional_hit_rate"))
    wf_mean = _safe_float(((wf_doc.get("aggregate") or {}) if isinstance(wf_doc, dict) else {}).get("mean_test_accuracy"))

    if not selected:
        selected = default_profile
        auto_cfg = profiles_doc.get("auto_selection") if isinstance(profiles_doc, dict) else {}
        enable_auto = bool((auto_cfg or {}).get("enable", False))
        gate = (auto_cfg or {}).get("promote_to_aggressive_when") if isinstance(auto_cfg, dict) else {}
        gate_hit = _safe_float((gate or {}).get("min_hit_rate"), 0.6)
        gate_wf = _safe_float((gate or {}).get("min_walkforward_mean_test_accuracy"), 0.55)
        if enable_auto and ("aggressive" in profiles) and hit_rate >= gate_hit and wf_mean >= gate_wf:
            selected = "aggressive"

    if selected not in profiles:
        selected = default_profile if default_profile in profiles else sorted(profiles.keys())[0]

    chosen = profiles[selected] if isinstance(profiles[selected], dict) else {}
    policy = {
        "schema": "prophecy_causal_active_guard_policy_v1",
        "updated_at_utc": _now(),
        "min_hit_rate": _safe_float(chosen.get("min_hit_rate"), 0.5),
        "min_n_evaluated_for_enforcement": int(chosen.get("min_n_evaluated_for_enforcement", 20)),
        "selected_profile": selected,
        "source_profiles_json": str(profiles_path),
        "note": "Resolved from profile presets by resolver script.",
    }
    _write(out_policy_path, policy)

    decision = {
        "schema": "prophecy_causal_active_guard_policy_decision_v1",
        "generated_at_utc": _now(),
        "profiles_json": str(profiles_path),
        "selected_profile": selected,
        "observed_hit_rate": hit_rate,
        "observed_walkforward_mean_test_accuracy": wf_mean,
        "out_policy_json": str(out_policy_path),
    }
    _write(out_decision_path, decision)
    _append_jsonl(log_path, decision)
    print(f"WROTE: {out_policy_path.resolve()}")
    print(f"WROTE: {out_decision_path.resolve()}")
    print(f"APPEND: {log_path.resolve()}")
    print(f"selected_profile={selected} hit_rate={hit_rate} wf_mean={wf_mean}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
