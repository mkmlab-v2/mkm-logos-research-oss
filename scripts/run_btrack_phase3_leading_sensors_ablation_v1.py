#!/usr/bin/env python3
"""Ablation: price-only vs leading-sensor shield/aux overlays (B-track, research_only).

Profiles (no Track A / no prod score mutation):
  price_only_baseline     — joined rows, predictions unchanged
  leading_shield_v1       — counterfactual neutral when composite flow opposes bull/bear
  leading_confirm_active  — hit rate on directional calls where sensor confirms prediction only

Does not promote direction from multilens or leading sensors.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOINED = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.jsonl"
DEFAULT_JOIN_META = ROOT / "reports/btrack_phase3_leading_sensors_joined_v1_latest.meta.json"
DEFAULT_OUT = ROOT / "reports/btrack_phase3_leading_sensors_ablation_v1_latest.json"
SCHEMA = "btrack_phase3_leading_sensors_ablation_v1"
ALERT1 = 0.5

# Import hit helpers from eval (same logic as prophecy hit-rate)
sys.path.insert(0, str(ROOT))
from scripts.eval_prophecy_hit_rate_v1 import _hit_on_rows, _hit_on_directional_calls_only  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _sensor_opposes(pred: str, composite: float | None, *, threshold: float) -> bool:
    if composite is None:
        return False
    p = pred.strip().lower()
    if p == "bull":
        return composite < -threshold
    if p == "bear":
        return composite > threshold
    return False


def _sensor_confirms(pred: str, composite: float | None, *, threshold: float) -> bool:
    if composite is None:
        return False
    p = pred.strip().lower()
    if p == "bull":
        return composite >= threshold
    if p == "bear":
        return composite <= -threshold
    if p == "neutral":
        return True
    return False


def _rows_for_profile(rows: list[dict[str, Any]], profile: str, *, threshold: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        pred = str(r.get("predicted_direction") or "")
        actual = str(r.get("actual_direction") or "")
        comp = r.get("leading_composite_signed_flow_z")
        comp_f = float(comp) if isinstance(comp, (int, float)) else None

        if profile == "price_only_baseline":
            eff_pred = pred
        elif profile == "leading_shield_v1":
            eff_pred = pred
            if _sensor_opposes(pred, comp_f, threshold=threshold):
                eff_pred = "neutral"
        elif profile == "leading_confirm_active":
            if not _sensor_confirms(pred, comp_f, threshold=threshold):
                continue
            eff_pred = pred
        else:
            raise ValueError(profile)

        out.append(
            {
                "eval_date": r.get("eval_date"),
                "instrument": r.get("instrument"),
                "predicted_direction": eff_pred,
                "actual_direction": actual,
                "profile": profile,
                "leading_composite_signed_flow_z": comp_f,
            }
        )
    return out


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits, n, rate = _hit_on_rows(rows)
    ch, nc, nn, cr = _hit_on_directional_calls_only(rows)
    return {
        "price_directional_hit_rate": round(rate, 6) if rate is not None else None,
        "n_evaluated": n,
        "price_hits": hits,
        "price_hit_rate_on_directional_calls": round(cr, 6) if cr is not None else None,
        "n_directional_calls": nc,
        "directional_call_hits": ch,
        "n_neutral_predictions": nn,
        "alert_1_pass": rate is not None and rate >= ALERT1,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--joined-jsonl", type=Path, default=DEFAULT_JOINED)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--disagree-threshold", type=float, default=0.05, help="Composite |z| threshold for oppose/confirm.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not args.joined_jsonl.is_file():
        print(f"MISSING joined jsonl: {args.joined_jsonl}", file=sys.stderr)
        return 2

    base_rows = _read_jsonl(args.joined_jsonl)
    if args.dry_run:
        print(json.dumps({"ok": True, "n_rows": len(base_rows)}, indent=2))
        return 0

    profiles = ("price_only_baseline", "leading_shield_v1", "leading_confirm_active")
    ablation_rows: list[dict[str, Any]] = []
    for prof in profiles:
        shaped = _rows_for_profile(base_rows, prof, threshold=args.disagree_threshold)
        m = _metrics(shaped)
        ablation_rows.append(
            {
                "profile": prof,
                "role_ko": {
                    "price_only_baseline": "현행 예측 그대로 (비교 기준)",
                    "leading_shield_v1": "센서 반대 시 neutral 반사실 (방패; 방향 승격 아님)",
                    "leading_confirm_active": "센서 일치일만 채점 (size/confidence 보조 관측)",
                }.get(prof, ""),
                "n_rows_scored": len(shaped),
                "metrics": m,
                "promotable_to_track_a": False,
                "auto_promote": False,
            }
        )

    baseline = next(r for r in ablation_rows if r["profile"] == "price_only_baseline")
    shield = next(r for r in ablation_rows if r["profile"] == "leading_shield_v1")
    b_rate = baseline["metrics"].get("price_directional_hit_rate")
    s_rate = shield["metrics"].get("price_directional_hit_rate")
    uplift = None
    if isinstance(b_rate, (int, float)) and isinstance(s_rate, (int, float)):
        uplift = round(float(s_rate) - float(b_rate), 6)

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "alert_1_threshold": ALERT1,
        "inputs": {
            "joined_jsonl": _rel(args.joined_jsonl),
        },
        "disagree_threshold": args.disagree_threshold,
        "profiles": ablation_rows,
        "verdict": {
            "auto_promote": False,
            "track_a_promotion": "NO",
            "direction_promotion_from_leading_sensors": False,
            "shield_uplift_vs_baseline": uplift,
            "note_ko": (
                "선행 센서 stub 기준 ablation. 실측 피드·holdout7·30d ALERT_1 재검증 전 prod 적용 금지. "
                "leading_confirm_active는 관측용 부분집합이며 전체행 헤드라인 대체 아님."
            ),
        },
        "operator_lines": [
            f"- [MKM-PHASE3-ABL] baseline={b_rate} shield={s_rate} uplift={uplift}",
            f"- [MKM-PHASE3-ABL] auto_promote=false track_a=NO",
        ],
        "rerun": "py scripts/run_btrack_phase3_leading_sensors_ablation_v1.py",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for row in ablation_rows:
        print(f"  {row['profile']}: hit={row['metrics'].get('price_directional_hit_rate')} n={row['n_rows_scored']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
