#!/usr/bin/env python3
"""[HYPO] Build gte beat-bull human sign-off readiness packet (research shadow; not production)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WF = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_ABLATION = ROOT / "reports/prophecy_lens_beat_bull_policy_ablation_v1_latest.json"
DEFAULT_FREEZE = ROOT / "reports/btrack_prophecy_research_freeze_v1_latest.json"
DEFAULT_TEMPLATE = ROOT / "reports/prophecy_lens_beat_bull_gte_human_signoff_v1.template.json"
DEFAULT_SIGNOFF = ROOT / "reports/prophecy_lens_beat_bull_gte_human_signoff_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_beat_bull_gte_signoff_readiness_v1_latest.json"
ABLATE = ROOT / "scripts/ablate_prophecy_lens_beat_bull_policy_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--walkforward-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--ablation-json", type=Path, default=DEFAULT_ABLATION)
    ap.add_argument("--freeze-json", type=Path, default=DEFAULT_FREEZE)
    ap.add_argument("--template-json", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--refresh-ablation", action="store_true")
    args = ap.parse_args()

    if args.refresh_ablation or not args.ablation_json.is_file():
        rc = subprocess.run(
            [
                sys.executable,
                str(ABLATE),
                "--walkforward-json",
                str(args.walkforward_json),
                "--output",
                str(args.ablation_json),
            ],
            cwd=str(ROOT),
        ).returncode
        if rc != 0:
            return int(rc)

    ablation = _load(args.ablation_json)
    freeze = _load(args.freeze_json) or {}
    signoff = _load(args.signoff_json) or _load(args.template_json) or {}

    policies = (ablation or {}).get("policies") if isinstance((ablation or {}).get("policies"), dict) else {}
    gt = policies.get("gt") if isinstance(policies.get("gt"), dict) else {}
    gte = policies.get("gte") if isinstance(policies.get("gte"), dict) else {}

    readiness: dict[str, Any] = {
        "schema": "prophecy_lens_beat_bull_gte_signoff_readiness_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "walkforward_json": str(args.walkforward_json),
            "ablation_json": str(args.ablation_json),
            "freeze_json": str(args.freeze_json),
            "signoff_json": str(args.signoff_json),
        },
        "counterfactual": {
            "gt_fraction_folds_pass": gt.get("fraction_folds_pass"),
            "gte_fraction_folds_pass": gte.get("fraction_folds_pass"),
            "gt_gate_would_pass": gt.get("lens_beat_bull_gate_would_pass"),
            "gte_gate_would_pass": gte.get("lens_beat_bull_gate_would_pass"),
        },
        "signoff_status": {
            "approved": bool(signoff.get("approved")),
            "gate_definition_change_acknowledged": bool(signoff.get("gate_definition_change_acknowledged")),
            "decision": signoff.get("decision"),
        },
        "checklist": [
            "Confirm production stays gt (strict >) on recommended chain.",
            "Acknowledge gte is tie-inclusive (>=) — gate definition change, not model uplift.",
            "Review freeze + micro ablation rejections before any gte shadow eval.",
            "Record sign-off via record_prophecy_lens_beat_bull_gte_human_signoff_v1.py --acknowledge-gate-definition-change.",
            "Run build_prophecy_promotion_gates_gte_research_shadow_v1.py only after approved sign-off.",
        ],
        "operator_lines": [],
    }
    readiness["operator_lines"] = [
        "- [GTE-SIGNOFF] Production lens beat-bull comparator remains gt (strict >).",
        f"- [GTE-SIGNOFF] Counterfactual gte fraction={gte.get('fraction_folds_pass')} "
        f"gt_fraction={gt.get('fraction_folds_pass')}.",
        f"- [GTE-SIGNOFF] signoff approved={readiness['signoff_status']['approved']} "
        f"ack={readiness['signoff_status']['gate_definition_change_acknowledged']}.",
        "- [GTE-SIGNOFF] gte shadow does NOT imply Track A / live / SEND_GATE lift.",
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
