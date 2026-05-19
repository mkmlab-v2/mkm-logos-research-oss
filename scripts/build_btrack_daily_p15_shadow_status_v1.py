#!/usr/bin/env python3
"""7d panel: tag daily chain with P1.5 vs B0 abstain posture (research_only)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILD_DIRS = ROOT / "scripts/build_btrack_ensemble_per_date_directions_v1.py"
CURVE = ROOT / "scripts/confidence_abstain_curve_v1.py"
OUT = ROOT / "reports/btrack_daily_p15_shadow_status_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _preset_metrics(curve: dict[str, Any], policy_id: str) -> dict[str, Any]:
    presets = curve.get("presets") if isinstance(curve.get("presets"), list) else []
    for block in presets:
        if not isinstance(block, dict) or block.get("policy_id") != policy_id:
            continue
        full = block.get("full_panel") if isinstance(block.get("full_panel"), dict) else {}
        return {
            "call_rate": full.get("call_rate"),
            "directional_skill": full.get("directional_skill"),
            "headline_skill": full.get("headline_skill"),
            "n_directional_calls": full.get("n_directional_calls"),
        }
    return {}


def _slice_v2_latest_7d(dirs_out: Path, n: int) -> int:
    """Reuse frozen v2 per-date panel (no v2 builder regen — avoids missing v2 hook)."""
    src = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
    if not src.is_file():
        return 2
    try:
        doc = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 2
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    dated = [r for r in rows if isinstance(r, dict) and r.get("eval_date")]
    dated.sort(key=lambda r: str(r.get("eval_date")))
    tail = dated[-n:] if len(dated) >= n else dated
    if not tail:
        return 2
    out_doc = {
        **{k: v for k, v in doc.items() if k != "rows"},
        "rows": tail,
        "inputs": {
            **(doc.get("inputs") if isinstance(doc.get("inputs"), dict) else {}),
            "n_eval_dates": len(tail),
            "sliced_from": str(src.relative_to(ROOT)).replace("\\", "/"),
        },
        "note": f"Last {len(tail)} eval_date rows sliced from v2_latest (7d shadow; no rebuild).",
    }
    dirs_out.parent.mkdir(parents=True, exist_ok=True)
    dirs_out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {dirs_out} rows={len(tail)} mode=slice_v2_latest")
    return 0


def main() -> int:
    n = 7
    dirs_out = ROOT / "reports/btrack_ensemble_per_date_directions_v2_7d_shadow.json"
    curve_out = ROOT / "reports/confidence_abstain_curve_v1_7d_latest.json"

    rc_dirs = _slice_v2_latest_7d(dirs_out, n)
    if rc_dirs != 0:
        rc_dirs = _run(
            [
                sys.executable,
                str(BUILD_DIRS),
                "--recent-trading-days",
                str(n),
                "--ensemble-mode",
                "v1",
                "--output",
                str(dirs_out),
            ]
        )
    if rc_dirs != 0:
        print("direction build failed", file=sys.stderr)
        return rc_dirs

    # abstain curve requires >=20 rows; 7d uses score join — may fail
    rc_curve = _run(
        [
            sys.executable,
            str(CURVE),
            "--recent-trading-days",
            str(n),
            "--output",
            str(curve_out),
        ]
    )
    curve: dict[str, Any] = {}
    curve_note = None
    if rc_curve == 0 and curve_out.is_file():
        curve = json.loads(curve_out.read_text(encoding="utf-8"))
    else:
        curve_note = f"abstain_curve_skipped_or_failed exit={rc_curve} (MIN_PANEL_ROWS=20)"

    doc = {
        "schema": "btrack_daily_p15_shadow_status_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "window_trading_days": n,
        "per_date_directions_json": str(dirs_out.relative_to(ROOT)).replace("\\", "/"),
        "abstain_curve_json": str(curve_out.relative_to(ROOT)).replace("\\", "/")
        if curve_out.is_file()
        else None,
        "abstain_curve_note": curve_note,
        "policy_posture_7d": {
            "B0_operational_score_panel": _preset_metrics(curve, "B0_operational_score_panel"),
            "P1_5_balanced_sniper_proxy": _preset_metrics(curve, "P1_5_balanced_sniper_proxy"),
        }
        if curve
        else None,
        "daily_chain_hook": {
            "recommended": "Append reports/btrack_daily_p15_shadow_status_v1_latest.json to ops digest",
            "operator_recommendation": "shadow_only_not_headline",
            "do_not_auto_promote": True,
        },
        "pointer_180d_brief": "reports/btrack_p15_abstain_shadow_brief_v1_latest.json",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
