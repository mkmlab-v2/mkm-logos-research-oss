#!/usr/bin/env python3
"""P1.5 abstain policy shadow brief from pre-registered abstain curve (180d). research_only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WINDOWS_SUMMARY = ROOT / "reports/confidence_abstain_curve_windows_summary_v1_latest.json"
CURVE_180 = ROOT / "reports/confidence_abstain_curve_v1_180d_latest.json"
OUT_JSON = ROOT / "reports/btrack_p15_abstain_shadow_brief_v1_latest.json"
OUT_MD = ROOT / "reports/btrack_p15_abstain_shadow_brief_v1_latest.md"
TARGET = "P1_5_balanced_sniper_proxy"
BASELINE = "B0_operational_score_panel"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _preset_row(presets: list[dict[str, Any]], policy_id: str) -> dict[str, Any] | None:
    for p in presets:
        if isinstance(p, dict) and p.get("policy_id") == policy_id:
            return p
    return None


def main() -> int:
    if not CURVE_180.is_file():
        print(f"Missing: {CURVE_180}", file=sys.stderr)
        return 2

    curve = _load(CURVE_180)
    presets = curve.get("presets") if isinstance(curve.get("presets"), list) else []
    b0 = _preset_row(presets, BASELINE)
    p15 = _preset_row(presets, TARGET)
    if not p15:
        print(f"Missing preset {TARGET} in {CURVE_180}", file=sys.stderr)
        return 2

    def _fp(p: dict[str, Any] | None) -> dict[str, Any]:
        if not p:
            return {}
        full = p.get("full_panel") if isinstance(p.get("full_panel"), dict) else {}
        hold = p.get("holdout_split") if isinstance(p.get("holdout_split"), dict) else {}
        return {
            "call_rate": full.get("call_rate"),
            "directional_skill": full.get("directional_skill"),
            "headline_skill": full.get("headline_skill"),
            "n_directional_calls": full.get("n_directional_calls"),
            "n_evaluated": full.get("n_evaluated"),
            "holdout_directional_skill": hold.get("directional_skill"),
            "holdout_n_directional_calls": hold.get("n_directional_calls"),
        }

    b0m = _fp(b0)
    p15m = _fp(p15)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    doc = {
        "schema": "btrack_p15_abstain_shadow_brief_v1",
        "generated_at_utc": generated,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "policy_id": TARGET,
        "baseline_policy_id": BASELINE,
        "window_days": 180,
        "sources": {
            "curve_180d": str(CURVE_180.relative_to(ROOT)).replace("\\", "/"),
            "windows_summary": str(WINDOWS_SUMMARY.relative_to(ROOT)).replace("\\", "/")
            if WINDOWS_SUMMARY.is_file()
            else None,
        },
        "baseline_metrics": b0m,
        "p15_metrics": p15m,
        "delta_vs_baseline": {
            "call_rate_pp": round((float(p15m.get("call_rate") or 0) - float(b0m.get("call_rate") or 0)) * 100, 2)
            if p15m.get("call_rate") is not None and b0m.get("call_rate") is not None
            else None,
            "directional_skill_pp": round(
                (float(p15m.get("directional_skill") or 0) - float(b0m.get("directional_skill") or 0)) * 100,
                2,
            )
            if p15m.get("directional_skill") is not None and b0m.get("directional_skill") is not None
            else None,
            "headline_skill_pp": round(
                (float(p15m.get("headline_skill") or 0) - float(b0m.get("headline_skill") or 0)) * 100,
                2,
            )
            if p15m.get("headline_skill") is not None and b0m.get("headline_skill") is not None
            else None,
        },
        "operator_recommendation": "shadow_only_not_headline",
        "note": "Holdout n is small (policy holdout last 10 trading days). No live trading or Track A promotion.",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = f"""# P1.5 Abstain Shadow Brief (180d) — [HYPO]

- **generated_at_utc:** `{generated}`
- **status:** shadow_only_not_headline · research_only

## vs B0 (operational panel)

| metric | B0 | P1.5 | Δ (pp) |
|--------|----|------|--------|
| call_rate | {b0m.get('call_rate')} | {p15m.get('call_rate')} | {doc['delta_vs_baseline'].get('call_rate_pp')} |
| directional_skill | {b0m.get('directional_skill')} | {p15m.get('directional_skill')} | {doc['delta_vs_baseline'].get('directional_skill_pp')} |
| headline_skill | {b0m.get('headline_skill')} | {p15m.get('headline_skill')} | {doc['delta_vs_baseline'].get('headline_skill_pp')} |
| holdout directional_skill | {b0m.get('holdout_directional_skill')} | {p15m.get('holdout_directional_skill')} | — |

**경계:** 실매매·Track A 승격 없음. holdout 표본 작음 — 브리핑에 승률 단정 금지.
"""
    OUT_MD.write_text(md, encoding="utf-8", newline="\n")
    print(f"WROTE: {OUT_JSON}")
    print(f"WROTE: {OUT_MD}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
