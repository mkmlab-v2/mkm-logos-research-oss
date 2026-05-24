#!/usr/bin/env python3
"""Consolidate shield sweep + ablation into role-retirement pack (research_only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "reports/btrack_phase3_shield_threshold_sweep_v1_latest.json"
ABL_30 = ROOT / "reports/btrack_phase3_leading_sensors_ablation_v1_latest.json"
ABL_180 = ROOT / "reports/btrack_phase3_leading_sensors_ablation_180d_v1_latest.json"
SIZE_AUX = ROOT / "reports/btrack_phase3_size_confidence_aux_ablation_v1_latest.json"
HR_PACK = ROOT / "reports/btrack_v1_price_only_human_review_pack_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_phase3_shield_role_retirement_pack_v1_latest.json"
DEFAULT_MD = ROOT / "reports/btrack_phase3_shield_role_retirement_pack_v1_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _render_md(p: dict[str, Any]) -> str:
    v = p.get("verdict") or {}
    lines = [
        "# Phase 3 — Shield role retirement pack (research_only)",
        "",
        f"- generated: `{p.get('generated_at_utc')}`",
        f"- **shield_as_direction_gate:** `{v.get('shield_as_direction_gate')}`",
        f"- **next_role:** `{v.get('next_role')}`",
        "",
        "## Verdict",
        "",
        v.get("reason_ko", ""),
        "",
        "## Evidence summary",
        "",
    ]
    ev = p.get("evidence") or {}
    for k, val in ev.items():
        if isinstance(val, dict):
            lines.append(f"### {k}")
            lines.append(f"- baseline: `{val.get('baseline_hit')}`")
            lines.append(f"- best_shield: `{val.get('best_shield_hit')}` @ threshold `{val.get('best_threshold')}`")
            lines.append(f"- beats_baseline: `{val.get('any_threshold_beats_baseline')}`")
            lines.append("")
    lines.append("## Policy")
    lines.append("")
    lines.append("- `apply_prod=false` · Track A OFF")
    lines.append("- Leading sensors → **size/confidence aux** in sidecar only")
    lines.append("- Do NOT wire funding/LS into direction shield/confirm for headline ALERT_1")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    args = ap.parse_args()

    sweep = _load(SWEEP)
    abl30 = _load(ABL_30)
    abl180 = _load(ABL_180)
    size_aux = _load(SIZE_AUX)
    hr = _load(HR_PACK)

    retire = False
    reason = "sweep_missing"
    evidence: dict[str, Any] = {}

    if sweep:
        retire = bool((sweep.get("verdict") or {}).get("shield_as_direction_gate") == "RETIRED")
        reason = (sweep.get("verdict") or {}).get("reason_ko", reason)
        for w in sweep.get("windows") or []:
            if not isinstance(w, dict):
                continue
            wid = w.get("window", "unknown")
            best = w.get("best_shield") or {}
            base = w.get("baseline") or {}
            evidence[wid] = {
                "baseline_hit": base.get("price_directional_hit_rate"),
                "best_shield_hit": (best.get("metrics") or {}).get("price_directional_hit_rate"),
                "best_threshold": best.get("disagree_threshold"),
                "any_threshold_beats_baseline": w.get("any_threshold_beats_baseline"),
            }

    payload = {
        "schema": "btrack_phase3_shield_role_retirement_pack_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "verdict": {
            "shield_as_direction_gate": "RETIRED" if retire else "HOLD_RESEARCH",
            "next_role": "size_confidence_aux_only",
            "track_a_promotion": "NO",
            "apply_prod": False,
            "auto_promote": False,
            "reason_ko": reason,
        },
        "evidence": evidence,
        "inputs": {
            "sweep": str(SWEEP) if SWEEP.is_file() else None,
            "ablation_30": str(ABL_30) if ABL_30.is_file() else None,
            "ablation_180": str(ABL_180) if ABL_180.is_file() else None,
            "size_confidence_aux": str(SIZE_AUX) if SIZE_AUX.is_file() else None,
            "human_review_pack": str(HR_PACK) if HR_PACK.is_file() else None,
        },
        "human_review_decision": (hr or {}).get("decision"),
        "size_confidence_aux_summary": (size_aux or {}).get("aux_size_confidence"),
        "operator_lines": [
            f"- [MKM-SHIELD-RETIRE] status={'RETIRED' if retire else 'HOLD'}",
            "- [MKM-SHIELD-RETIRE] next=size_confidence_aux_only apply_prod=false",
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(_render_md(payload), encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"WROTE: {args.out_md.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
