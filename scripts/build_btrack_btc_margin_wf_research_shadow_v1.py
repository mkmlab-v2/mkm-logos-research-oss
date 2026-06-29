#!/usr/bin/env python3
"""[HYPO] Build BTC margin WF research shadow (Type-A guard eval) after human sign-off."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNOFF = ROOT / "reports/btrack_btc_margin_wf_human_signoff_latest.json"
DEFAULT_MARGIN = ROOT / "reports/btrack_btc_margin_walkforward_gate_v1_latest.json"
DEFAULT_OPER_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_SHADOW_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_btc_typea_guard_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_margin_wf_research_shadow_v1_latest.json"
APPLY = ROOT / "scripts/apply_btrack_btc_typea_guard_to_score_v1.py"
DECISION_PACK = ROOT / "scripts/build_btrack_btc_promotion_decision_pack_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--margin-json", type=Path, default=DEFAULT_MARGIN)
    ap.add_argument("--oper-score-json", type=Path, default=DEFAULT_OPER_SCORE)
    ap.add_argument("--shadow-score-json", type=Path, default=DEFAULT_SHADOW_SCORE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    signoff = _load(args.signoff_json)
    if not signoff.get("approved") or not signoff.get("instrument_layer_change_acknowledged"):
        print(f"BTC sign-off not approved: {args.signoff_json}", flush=True)
        return 2

    rc = subprocess.run([sys.executable, str(APPLY)], cwd=str(ROOT)).returncode
    if rc != 0:
        return int(rc)

    if not args.shadow_score_json.is_file():
        print(f"missing shadow score: {args.shadow_score_json}", flush=True)
        return 1

    eval_out = args.output.parent / "btrack_btc_margin_wf_research_shadow_hit_eval_v1_latest.json"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_prophecy_hit_rate_v1.py"),
            "--run-mode",
            "price",
            "--score-json",
            str(args.shadow_score_json),
            "--headline-instrument",
            "btc",
            "--output",
            str(eval_out),
        ],
        cwd=str(ROOT),
    ).returncode
    if rc != 0:
        return int(rc)

    subprocess.run([sys.executable, str(DECISION_PACK)], cwd=str(ROOT))

    shadow_eval = _load(eval_out)
    oper_eval_path = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
    oper_btc = None
    if oper_eval_path.is_file():
        oper_doc = _load(oper_eval_path)
        legs = oper_doc.get("legs") if isinstance(oper_doc.get("legs"), dict) else {}
        btc_leg = legs.get("btc") if isinstance(legs.get("btc"), dict) else {}
        oper_btc = btc_leg.get("price_directional_hit_rate")

    shadow_metrics = shadow_eval.get("metrics") if isinstance(shadow_eval.get("metrics"), dict) else {}
    shadow_hit = shadow_metrics.get("price_directional_hit_rate")
    margin = _load(args.margin_json)

    report: dict[str, Any] = {
        "schema": "btrack_btc_margin_wf_research_shadow_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "signoff_json": str(args.signoff_json),
        "operational_score_path": str(args.oper_score_json),
        "shadow_score_path": str(args.shadow_score_json),
        "operational_score_sha_unchanged_assertion": "caller must not run apply_btrack_btc_typea_guard_human_approval",
        "btc_headline_hit_rate": {
            "operational_latest_btc": oper_btc,
            "shadow_typea_btc": shadow_hit,
            "shadow_minus_oper": round(float(shadow_hit) - float(oper_btc), 6)
            if shadow_hit is not None and oper_btc is not None
            else None,
        },
        "margin_gate_reference": {
            "promotion_recommendation": margin.get("promotion_recommendation"),
            "global_holdout_best": (margin.get("global_holdout") or {}).get("best"),
        },
        "combined_all_passed": False,
        "auto_promote": False,
        "would_change_active": False,
        "eval_artifact": str(eval_out),
        "operator_lines": [
            "- [BTC-SHADOW] Type-A guard applied to shadow score only.",
            f"- [BTC-SHADOW] oper_btc_hit={oper_btc} shadow_btc_hit={shadow_hit}.",
            "- [BTC-SHADOW] combined_all_passed remains false; lens gt unchanged.",
            "- [BTC-SHADOW] does NOT imply Track A / live / SEND_GATE lift.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
