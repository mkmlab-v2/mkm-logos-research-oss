#!/usr/bin/env python3
"""[HYPO] Temporal holdout on frozen OOS params — promotion review memo only (no SSOT write)."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUT = ROOT / "reports/logos_oos_temporal_holdout_memo_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _eval_holdout_halves(
    *,
    score_json: Path,
    sidecar_json: Path,
    btc_csv: Path,
    instrument: str,
    oos_tail_days: int,
    lb: int,
    nz: float,
    gate_min_hit: float,
    myeongni_base_mode: str,
) -> dict[str, Any]:
    gate_path = ROOT / "scripts" / "run_prophecy_lens_role_router_oos_gate_v1.py"
    spec = importlib.util.spec_from_file_location("gate_mod", gate_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load gate module: {gate_path}")
    gate_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate_mod)

    score = gate_mod._read_json(score_json)
    sidecar = gate_mod._read_json(sidecar_json)
    rows = score.get("rows") or []
    inst = instrument.strip().lower()
    panel = [r for r in rows if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == inst]
    panel.sort(key=lambda x: str(x.get("eval_date") or ""))
    oos_tail = max(3, int(oos_tail_days))
    train_rows = panel[:-oos_tail]
    oos_rows = panel[-oos_tail:]
    mid = len(oos_rows) // 2
    oos_a = oos_rows[:mid]
    oos_b = oos_rows[mid:]

    btc_prior = gate_mod._prior_completed_daily_return_by_eval_date(btc_csv) if btc_csv.is_file() else {}
    m_map, s_map, logos_sign = gate_mod._extract_sidecar_maps(sidecar)

    candidates = []
    for lb_c, nz_c in [(lb, nz)]:
        train_m = gate_mod._run_router(
            train_rows,
            btc_prior=btc_prior,
            m_map=m_map,
            s_map=s_map,
            logos_sign=logos_sign,
            fee_bps=5.0,
            month_lookback_days=lb_c,
            neutral_size=nz_c,
            annual_days=252,
            myeongni_base_mode=myeongni_base_mode,
        )
        candidates.append({"params": {"month_lookback_days": lb_c, "neutral_size": nz_c}, "train_metrics": train_m})

    def _train_rank_key(cand: dict[str, Any]) -> tuple[float, ...]:
        tm = cand.get("train_metrics") if isinstance(cand.get("train_metrics"), dict) else {}
        n_active = int(tm.get("n_active_days") or 0)
        sharpe = float(tm.get("sharpe") or -999.0)
        cagr = float(tm.get("cagr") or -999.0)
        mdd = float(tm.get("mdd") or -999.0)
        if n_active > 0:
            return (1.0, sharpe, cagr, mdd)
        sig = sum(1 for r in train_rows if int(m_map.get(str(r.get("eval_date") or "")[:10], 0)) != 0)
        nz_c = float((cand.get("params") or {}).get("neutral_size") or 0.0)
        return (0.0, float(sig), -nz_c, sharpe)

    best = max(candidates, key=_train_rank_key)
    params = best["params"]
    lb_f = int(params["month_lookback_days"])
    nz_f = float(params["neutral_size"])

    def _frozen(rows_slice: list[dict[str, Any]]) -> dict[str, Any]:
        return gate_mod._run_router(
            rows_slice,
            btc_prior=btc_prior,
            m_map=m_map,
            s_map=s_map,
            logos_sign=logos_sign,
            fee_bps=5.0,
            month_lookback_days=lb_f,
            neutral_size=nz_f,
            annual_days=252,
            myeongni_base_mode=myeongni_base_mode,
        )

    full_oos = _frozen(oos_rows)
    half_a = _frozen(oos_a)
    half_b = _frozen(oos_b)

    def _pass_hit(m: dict[str, Any]) -> bool:
        try:
            return float(m.get("directional_hit_rate_active") or 0) >= gate_min_hit
        except (TypeError, ValueError):
            return False

    return {
        "sidecar_json": str(sidecar_json.relative_to(ROOT)).replace("\\", "/"),
        "frozen_params": params,
        "train_metrics": best.get("train_metrics"),
        "oos_full": full_oos,
        "oos_holdout_early": {
            **half_a,
            "window": {
                "start": str(oos_a[0].get("eval_date") or "")[:10] if oos_a else None,
                "end": str(oos_a[-1].get("eval_date") or "")[:10] if oos_a else None,
                "n_calendar_days": len(oos_a),
            },
            "hit_pass_vs_threshold": _pass_hit(half_a),
        },
        "oos_holdout_late": {
            **half_b,
            "window": {
                "start": str(oos_b[0].get("eval_date") or "")[:10] if oos_b else None,
                "end": str(oos_b[-1].get("eval_date") or "")[:10] if oos_b else None,
                "n_calendar_days": len(oos_b),
            },
            "hit_pass_vs_threshold": _pass_hit(half_b),
        },
        "stability_ko": (
            "early/late OOS halves both pass hit gate"
            if _pass_hit(half_a) and _pass_hit(half_b)
            else "holdout unstable — do not promote from full-OOS hit alone"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=ROOT / "docs/final/artifacts/btrack_prophecy_score_30y_dual_latest.json")
    ap.add_argument("--btc-csv", type=Path, default=ROOT / "research/market_data/btc_daily_external_yf.csv")
    ap.add_argument("--target-instrument", default="kospi")
    ap.add_argument("--oos-tail-days", type=int, default=252)
    ap.add_argument("--lb", type=int, default=28)
    ap.add_argument("--nz", type=float, default=0.15)
    ap.add_argument("--gate-min-hit-rate", type=float, default=0.52)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    variants = [
        (
            "golden_sparse_orig",
            ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_sparse_orig_v1.json",
        ),
        (
            "birth_overlay_sw025_band006",
            ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_birth_overlay_sw025_band006_v1.json",
        ),
        (
            "hybrid_sparse_session_ext",
            ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_hybrid_ext_v1.json",
        ),
    ]
    rows = []
    for label, sidecar in variants:
        if not sidecar.is_file():
            rows.append({"label": label, "missing": True, "path": str(sidecar)})
            continue
        rows.append(
            {
                "label": label,
                **_eval_holdout_halves(
                    score_json=args.score_json,
                    sidecar_json=sidecar,
                    btc_csv=args.btc_csv,
                    instrument=args.target_instrument,
                    oos_tail_days=args.oos_tail_days,
                    lb=args.lb,
                    nz=args.nz,
                    gate_min_hit=args.gate_min_hit_rate,
                    myeongni_base_mode="sidecar_only",
                ),
            }
        )

    golden_ref = 0.565217
    birth = next((r for r in rows if r.get("label") == "birth_overlay_sw025_band006"), {})
    full_hit = float((birth.get("oos_full") or {}).get("directional_hit_rate_active") or 0)
    memo = {
        "schema": "logos_oos_temporal_holdout_memo_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "promotion_action": "none",
        "logos_oos_gate_ssot_unchanged": "docs/final/artifacts/prophecy_logos_revalidation_oos_gate_latest.json",
        "golden_sparse_hit_reference": golden_ref,
        "method_ko": (
            "Train=panel[:-252], params=lb28/nz0.15 from train rank, frozen on full OOS 252d; "
            "holdout=동일 params로 OOS 전반/전반·후반 각 절반(캘린더 순)."
        ),
        "variants": rows,
        "review_ko": [
            "성숙도 D·prophecy_logos_revalidation_oos_gate_latest.json 은 golden 0.565217 유지.",
            f"birth full-OOS hit={full_hit:.6f} — holdout early/late 모두 gate 통과 시에만 승격 검토 후보.",
            "birth train active 높음 → holdout 실패 시 과적합·조건 불일치로 SSOT 대체 금지.",
        ],
    }
    text = json.dumps(memo, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(text)
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
