#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EXODUS = ROOT / "docs" / "final" / "artifacts" / "exodus_pressure_v1_latest.json"
DEFAULT_MACRO_SMOKE = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_smoke_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_4d_state_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _quadrant(x: float, y: float) -> str:
    x_hi = x >= 50.0
    y_hi = y >= 50.0
    if x_hi and y_hi:
        return "Q1"
    if (not x_hi) and y_hi:
        return "Q2"
    if (not x_hi) and (not y_hi):
        return "Q3"
    return "Q4"


def _quadrant_label(q: str) -> str:
    labels = {
        "Q1": "균열 가속 + 자본 이동 급증",
        "Q2": "균열 선행, 이동 지연",
        "Q3": "안정 구간",
        "Q4": "선제적 이동",
    }
    return labels.get(q, "unknown")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build logos_4d_state_v1 artifact from X/Y engines.")
    p.add_argument("--exodus-json", type=Path, default=DEFAULT_EXODUS)
    p.add_argument("--macro-smoke-json", type=Path, default=DEFAULT_MACRO_SMOKE)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    exodus_path = args.exodus_json if args.exodus_json.is_absolute() else (ROOT / args.exodus_json)
    smoke_path = args.macro_smoke_json if args.macro_smoke_json.is_absolute() else (ROOT / args.macro_smoke_json)
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)

    exodus = _read_json(exodus_path)
    smoke = _read_json(smoke_path)
    frag = smoke.get("fragility_composite") if isinstance(smoke.get("fragility_composite"), dict) else {}
    narrative = smoke.get("non_gating_narrative") if isinstance(smoke.get("non_gating_narrative"), dict) else {}

    x_score = _clamp(_to_float(exodus.get("score_0_100"), 50.0), 0.0, 100.0)
    y_score = _clamp(_to_float(frag.get("score_0_100"), 50.0), 0.0, 100.0)
    q = _quadrant(x_score, y_score)
    regime_tag = str(smoke.get("decision_state") or "WATCH").upper()

    band = str(smoke.get("confidence_band") or "").strip().lower()
    if band == "high":
        conv = 0.85
    elif band == "medium":
        conv = 0.65
    else:
        conv = 0.45

    state = {
        "schema": "logos_4d_state_v1",
        "generated_at_utc": _utc_now(),
        "timestamp": str(smoke.get("timestamp_utc") or _utc_now()),
        "coordinates": {
            "x_exodus_pressure": round(x_score, 6),
            "y_babel_fragility": round(y_score, 6),
        },
        "quadrant_info": {
            "current_quadrant": q,
            "regime_tag": regime_tag,
            "label": _quadrant_label(q),
        },
        "visual_markers": {
            "conviction_size": round(_clamp(conv, 0.1, 1.0), 6),
            "core_atom_thickness": round(2.0 + _clamp(_to_float((narrative.get("state_4d") or {}).get("stress"), 0.0), 0.0, 1.0) * 4.0, 6),
            "trajectory_tail": [],
        },
        "narrative_oracle": {
            "policy_tag": "[NON_GATING]",
            "field": narrative.get("field"),
            "logos": narrative.get("logos"),
            "conflict": narrative.get("conflict"),
            "action": narrative.get("action"),
        },
        "evidence": {
            "exodus_artifact": str(exodus_path.relative_to(ROOT)),
            "macro_smoke_artifact": str(smoke_path.relative_to(ROOT)),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"logos_4d_state_v1: PASS -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

