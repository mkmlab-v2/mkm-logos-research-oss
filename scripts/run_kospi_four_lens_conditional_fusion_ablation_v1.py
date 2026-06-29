#!/usr/bin/env python3
"""Conditional 4-lens fusion ablation vs active June KOSPI calendar [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_four_lens_conditional_fusion_ablation_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _sign_from_direction(pred: str) -> str:
    p = str(pred or "").lower()
    if p == "bull":
        return "bull"
    if p == "bear":
        return "bear"
    return "neutral"


def _fusion_adjusted_direction(fusion: dict[str, Any], base_pred: str) -> str:
    """When Field bear + Logos bear conflict with base neutral/bull, tilt bear."""
    res = fusion.get("fusion_resolution") or {}
    field = fusion.get("field") or {}
    logos = (fusion.get("lenses") or {}).get("logos") or {}
    conflicts = res.get("conflict_ids") or []
    base = _sign_from_direction(base_pred)
    if "field_bear_vs_lens_bull_majority" in conflicts:
        if field.get("direction_sign") == "bear" and logos.get("direction_sign") == "bear":
            return "bear"
    if field.get("direction_sign") == "bear" and float(field.get("daily_return_pct") or 0) <= -5.0:
        if base == "neutral":
            return "bear"
    return base


def run_ablation(eval_doc: dict[str, Any], fusion: dict[str, Any]) -> dict[str, Any]:
    rows = eval_doc.get("rows")
    if not isinstance(rows, list):
        rows = []
    active_hits = 0
    fusion_hits = 0
    n = 0
    per_date: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        actual = row.get("actual_direction")
        if actual not in ("bull", "bear", "neutral"):
            continue
        ret = float(row.get("daily_return_pct") or 0.0)
        pred_active = row.get("predicted_direction")
        pred_fusion = _fusion_adjusted_direction(fusion, str(pred_active))
        out_a = str(row.get("outcome") or _outcome(str(pred_active), str(actual)))
        out_f = _outcome(pred_fusion, str(actual))
        hit_a = 1.0 if out_a == "HIT" else (0.5 if out_a == "NEUTRAL_DRAW" else 0.0)
        hit_f = 1.0 if out_f == "HIT" else (0.5 if out_f == "NEUTRAL_DRAW" else 0.0)
        active_hits += hit_a
        fusion_hits += hit_f
        n += 1
        per_date.append(
            {
                "session_date": row.get("session_date"),
                "actual": actual,
                "active_pred": pred_active,
                "fusion_pred": pred_fusion,
                "active_outcome": out_a,
                "fusion_outcome": out_f,
                "improved": out_a != "HIT" and out_f == "HIT",
            }
        )
    soft_a = active_hits / n if n else 0.0
    soft_f = fusion_hits / n if n else 0.0
    delta = soft_f - soft_a
    promotion_candidate = delta >= 0.03 and n >= 10
    return {
        "schema": "kospi_four_lens_conditional_fusion_ablation_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "n_scored": n,
        "metrics": {
            "active_soft_hit_rate": round(soft_a, 4),
            "fusion_adjusted_soft_hit_rate": round(soft_f, 4),
            "delta_fusion_minus_active": round(delta, 4),
        },
        "promotion_candidate": promotion_candidate,
        "verdict_ko": (
            "조건부 fusion이 active 대비 +3%p 이상 — 후속 WF 검증 후보"
            if promotion_candidate
            else "조건부 fusion uplift 미달 — 리포트·충돌 가시화만 유지"
        ),
        "per_date": per_date,
        "fusion_pointer": "reports/kospi_four_lens_graphrag_fusion_v1_latest.json",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    fusion = _read(args.fusion_json)
    if not ev or not fusion:
        print("Missing eval or fusion json", file=sys.stderr)
        return 2
    doc = run_ablation(ev, fusion)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "metrics": doc["metrics"], "promotion_candidate": doc["promotion_candidate"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
