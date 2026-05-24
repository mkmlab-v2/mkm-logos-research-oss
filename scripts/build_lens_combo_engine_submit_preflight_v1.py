#!/usr/bin/env python3
"""Build pre-submit checklist and operator command set for lens-combo handoff."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_ENGINE_INPUT = ART / "btc_limited_live_engine_input_from_lens_combo_latest.json"
DEFAULT_OUT_JSON = ART / "lens_combo_engine_submit_preflight_v1_latest.json"
DEFAULT_OUT_CMDS = ART / "lens_combo_engine_submit_commands_v1_latest.txt"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bool(v: Any) -> bool:
    return bool(v)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-input-json", type=Path, default=DEFAULT_ENGINE_INPUT)
    ap.add_argument(
        "--expected-dry-run",
        type=str,
        choices=("any", "true", "false"),
        default="any",
        help="Expected dry_run mode for the engine payload.",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-commands", type=Path, default=DEFAULT_OUT_CMDS)
    args = ap.parse_args()

    doc = _read(args.engine_input_json)
    guards = doc.get("guards") or {}
    engine_input = doc.get("engine_input") or {}
    metrics = engine_input.get("candidate_metrics") or {}

    dry_run_value = _bool(doc.get("dry_run"))
    if args.expected_dry_run == "true":
        dry_run_mode_ok = dry_run_value is True
    elif args.expected_dry_run == "false":
        dry_run_mode_ok = dry_run_value is False
    else:
        dry_run_mode_ok = True

    checks = {
        "engine_status_ready_for_submit": str(doc.get("status") or "") == "READY_FOR_ENGINE_SUBMIT",
        "engine_action_submit_to_queue": str(doc.get("action") or "") == "submit_to_engine_queue",
        "dry_run_mode_ok": dry_run_mode_ok,
        "candidate_tradable": _bool(guards.get("candidate_tradable")),
        "signoff_approve": _bool(guards.get("signoff_approve")),
        "limited_live_mode_ok": _bool(guards.get("signoff_mode_limited_live")),
        "approve_submit_flag_true": _bool(guards.get("approve_submit_flag")),
        "max_drawdown_guard_present": (engine_input.get("max_drawdown_pct") is not None),
        "max_consecutive_losses_present": (engine_input.get("max_consecutive_losses") is not None),
        "candidate_hit_rate_gte_0p55": float(metrics.get("directional_hit_rate_active") or 0.0) >= 0.55,
    }
    all_pass = all(bool(v) for v in checks.values())
    failed = [k for k, v in checks.items() if not bool(v)]

    payload = {
        "schema": "lens_combo_engine_submit_preflight_v1",
        "generated_at_utc": _now(),
        "engine_input_json": str(args.engine_input_json.resolve()),
        "expected_dry_run": args.expected_dry_run,
        "observed_dry_run": dry_run_value,
        "result": "PASS" if all_pass else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "candidate_metrics_snapshot": metrics,
        "operator_note": (
            "non-execution preflight only; actual queue submit must follow runtime policy and human control."
        ),
    }

    commands = [
        "# 1) Refresh strict backtest + candidate artifacts",
        'py "scripts/run_prophecy_lens_combo_backtest_v1.py" --logos-vote-mode omit --fee-bps-grid "5,10,20" --walkforward-mode expanding --walkforward-min-train-rows 10 --walkforward-test-window-rows 5',
        "",
        "# 2) Build engine handoff (explicit approval, still dry-run payload)",
        'py "scripts/run_lens_combo_limited_live_engine_handoff_v1.py" --approve-submit',
        "",
        "# 2b) Build engine handoff (explicit approval, live payload)",
        'py "scripts/run_lens_combo_limited_live_engine_handoff_v1.py" --approve-submit --live',
        "",
        "# 3) Pre-submit checklist",
        'py "scripts/build_lens_combo_engine_submit_preflight_v1.py" --expected-dry-run any',
        "",
        "# 4) Rollback rehearsal (force HOLD payload)",
        'py "scripts/run_lens_combo_limited_live_engine_handoff_v1.py"',
    ]

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_commands.parent.mkdir(parents=True, exist_ok=True)
    args.out_commands.write_text("\n".join(commands) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out_json}")
    print(f"WROTE: {args.out_commands}")
    print(f"result={payload['result']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
