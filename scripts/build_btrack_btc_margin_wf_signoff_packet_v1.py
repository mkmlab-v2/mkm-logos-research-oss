#!/usr/bin/env python3
"""[HYPO] Build BTC margin WF human sign-off readiness packet (research shadow; not operational)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARGIN = ROOT / "reports/btrack_btc_margin_walkforward_gate_v1_latest.json"
DEFAULT_FREEZE = ROOT / "reports/btrack_prophecy_research_freeze_v1_latest.json"
DEFAULT_TEMPLATE = ROOT / "reports/btrack_btc_margin_wf_human_signoff_v1.template.json"
DEFAULT_SIGNOFF = ROOT / "reports/btrack_btc_margin_wf_human_signoff_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_margin_wf_signoff_readiness_v1_latest.json"
MARGIN_EVAL = ROOT / "scripts/eval_btrack_btc_margin_walkforward_gate_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--margin-json", type=Path, default=DEFAULT_MARGIN)
    ap.add_argument("--freeze-json", type=Path, default=DEFAULT_FREEZE)
    ap.add_argument("--template-json", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--refresh-margin-gate", action="store_true")
    args = ap.parse_args()

    if args.refresh_margin_gate or not args.margin_json.is_file():
        rc = subprocess.run([sys.executable, str(MARGIN_EVAL)], cwd=str(ROOT)).returncode
        if rc != 0:
            return int(rc)

    margin = _load(args.margin_json) or {}
    freeze = _load(args.freeze_json) or {}
    signoff = _load(args.signoff_json) or _load(args.template_json) or {}
    global_best = (margin.get("global_holdout") or {}).get("best") or {}
    hits = (freeze.get("metrics") or {}).get("price_hit_rates") or {}

    readiness: dict[str, Any] = {
        "schema": "btrack_btc_margin_wf_signoff_readiness_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "margin_json": str(args.margin_json),
            "freeze_json": str(args.freeze_json),
            "signoff_json": str(args.signoff_json),
        },
        "margin_oos": {
            "promotion_recommendation": margin.get("promotion_recommendation"),
            "would_change_active": margin.get("would_change_active"),
            "test_baseline_hit_rate": global_best.get("test_baseline_hit_rate"),
            "test_counterfactual_hit_rate": global_best.get("test_counterfactual_hit_rate"),
            "test_delta_oos": global_best.get("test_delta_oos"),
            "selected_params": global_best.get("selected_params"),
        },
        "frozen_btc_kospi_hit": {
            "btc": hits.get("btc"),
            "kospi": hits.get("kospi"),
            "lens_gt_beat_bull": (freeze.get("metrics") or {}).get("lens_fraction_gt_beat_bull"),
        },
        "signoff_status": {
            "approved": bool(signoff.get("approved")),
            "instrument_layer_change_acknowledged": bool(signoff.get("instrument_layer_change_acknowledged")),
            "decision": signoff.get("decision"),
        },
        "checklist": [
            "Confirm operational btrack_prophecy_score_latest.json stays unchanged by this shadow lane.",
            "Acknowledge Type-A guard is BTC post-process — not lens gt beat-bull fix.",
            "Review margin WF global_holdout OOS delta before sign-off.",
            "Record via record_btrack_btc_margin_wf_human_signoff_v1.py --acknowledge-btc-instrument-layer-change.",
            "Run build_btrack_btc_margin_wf_research_shadow_v1.py only after approved sign-off.",
        ],
        "operator_lines": [],
    }
    readiness["operator_lines"] = [
        "- [BTC-SIGNOFF] Operational score unchanged; lens gt beat-bull blocker remains on prod gates.",
        f"- [BTC-SIGNOFF] margin OOS delta={global_best.get('test_delta_oos')} "
        f"rec={margin.get('promotion_recommendation')}.",
        f"- [BTC-SIGNOFF] signoff approved={readiness['signoff_status']['approved']} "
        f"ack={readiness['signoff_status']['instrument_layer_change_acknowledged']}.",
        "- [BTC-SIGNOFF] shadow does NOT imply Track A / live / SEND_GATE lift.",
    ]

    if not args.signoff_json.is_file() and args.template_json.is_file():
        args.signoff_json.parent.mkdir(parents=True, exist_ok=True)
        if not args.signoff_json.exists():
            args.signoff_json.write_text(
                args.template_json.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            readiness["signoff_template_copied_to"] = str(args.signoff_json)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in readiness["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
