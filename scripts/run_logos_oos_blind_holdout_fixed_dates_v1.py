#!/usr/bin/env python3
"""[HYPO] Fixed-date blind vs confirm windows — birth overlay promotion review (no SSOT write)."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_oos_blind_holdout_fixed_dates_v1_latest.json"

# From temporal holdout memo: sparse JSONL active coverage starts ~2025-11-25 on OOS tail.
DEFAULT_BLIND_START = "2025-05-21"
DEFAULT_BLIND_END = "2025-11-24"
DEFAULT_CONFIRM_START = "2025-11-25"
DEFAULT_CONFIRM_END = "2026-06-02"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_gate_mod():
    gate_path = ROOT / "scripts" / "run_prophecy_lens_role_router_oos_gate_v1.py"
    spec = importlib.util.spec_from_file_location("gate_mod", gate_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load: {gate_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _slice_rows(rows: list[dict[str, Any]], start: str, end: str) -> list[dict[str, Any]]:
    return [r for r in rows if start <= str(r.get("eval_date") or "")[:10] <= end]


def _eval_variant(
    gate_mod: Any,
    *,
    label: str,
    sidecar_json: Path,
    score_json: Path,
    btc_csv: Path,
    instrument: str,
    oos_tail_days: int,
    lb: int,
    nz: float,
    gate_min_hit: float,
    blind_start: str,
    blind_end: str,
    confirm_start: str,
    confirm_end: str,
) -> dict[str, Any]:
    score = gate_mod._read_json(score_json)
    sidecar = gate_mod._read_json(sidecar_json)
    rows = score.get("rows") or []
    inst = instrument.strip().lower()
    panel = [r for r in rows if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == inst]
    panel.sort(key=lambda x: str(x.get("eval_date") or ""))
    oos_tail = max(3, int(oos_tail_days))
    train_rows = panel[:-oos_tail]
    oos_rows = panel[-oos_tail:]

    btc_prior = gate_mod._prior_completed_daily_return_by_eval_date(btc_csv) if btc_csv.is_file() else {}
    m_map, s_map, logos_sign = gate_mod._extract_sidecar_maps(sidecar)

    train_m = gate_mod._run_router(
        train_rows,
        btc_prior=btc_prior,
        m_map=m_map,
        s_map=s_map,
        logos_sign=logos_sign,
        fee_bps=5.0,
        month_lookback_days=lb,
        neutral_size=nz,
        annual_days=252,
        myeongni_base_mode="sidecar_only",
    )

    def _frozen(slice_rows: list[dict[str, Any]]) -> dict[str, Any]:
        return gate_mod._run_router(
            slice_rows,
            btc_prior=btc_prior,
            m_map=m_map,
            s_map=s_map,
            logos_sign=logos_sign,
            fee_bps=5.0,
            month_lookback_days=lb,
            neutral_size=nz,
            annual_days=252,
            myeongni_base_mode="sidecar_only",
        )

    blind_rows = _slice_rows(oos_rows, blind_start, blind_end)
    confirm_rows = _slice_rows(oos_rows, confirm_start, confirm_end)
    blind_m = _frozen(blind_rows)
    confirm_m = _frozen(confirm_rows)
    full_m = _frozen(oos_rows)

    def _pass(m: dict[str, Any]) -> bool:
        try:
            return float(m.get("directional_hit_rate_active") or 0) >= gate_min_hit
        except (TypeError, ValueError):
            return False

    blind_pass = _pass(blind_m)
    confirm_pass = _pass(confirm_m)
    return {
        "label": label,
        "sidecar_json": str(sidecar_json.relative_to(ROOT)).replace("\\", "/"),
        "frozen_params": {"month_lookback_days": lb, "neutral_size": nz},
        "train_n_active": int(train_m.get("n_active_days") or 0),
        "oos_full": full_m,
        "blind_window": {
            "start": blind_start,
            "end": blind_end,
            "n_calendar_days": len(blind_rows),
            "metrics": blind_m,
        },
        "confirm_window": {
            "start": confirm_start,
            "end": confirm_end,
            "n_calendar_days": len(confirm_rows),
            "metrics": confirm_m,
        },
        "blind_hit_pass": blind_pass,
        "confirm_hit_pass": confirm_pass,
        "promotion_candidate": blind_pass and confirm_pass,
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
    ap.add_argument("--blind-start", default=DEFAULT_BLIND_START)
    ap.add_argument("--blind-end", default=DEFAULT_BLIND_END)
    ap.add_argument("--confirm-start", default=DEFAULT_CONFIRM_START)
    ap.add_argument("--confirm-end", default=DEFAULT_CONFIRM_END)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gate_mod = _load_gate_mod()
    variants = [
        ("golden_sparse_orig", ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_sparse_orig_v1.json"),
        ("sparse_blind_session_fill", ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_sparse_blind_session_fill_v1.json"),
        ("birth_overlay_sw025_band006", ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_birth_overlay_sw025_band006_v1.json"),
        ("hybrid_sparse_session_ext", ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_hybrid_ext_v1.json"),
    ]
    rows_out = []
    for label, sidecar in variants:
        if not sidecar.is_file():
            rows_out.append({"label": label, "missing": True})
            continue
        rows_out.append(
            _eval_variant(
                gate_mod,
                label=label,
                sidecar_json=sidecar,
                score_json=args.score_json,
                btc_csv=args.btc_csv,
                instrument=args.target_instrument,
                oos_tail_days=args.oos_tail_days,
                lb=args.lb,
                nz=args.nz,
                gate_min_hit=args.gate_min_hit_rate,
                blind_start=args.blind_start,
                blind_end=args.blind_end,
                confirm_start=args.confirm_start,
                confirm_end=args.confirm_end,
            )
        )

    birth = next(
        (r for r in rows_out if r.get("label") == "birth_overlay_sw025_band006" and not r.get("missing")),
        {},
    )
    b_blind = ((birth.get("blind_window") or {}).get("metrics") or {})
    b_confirm = ((birth.get("confirm_window") or {}).get("metrics") or {})
    doc = {
        "schema": "logos_oos_blind_holdout_fixed_dates_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "promotion_action": "none",
        "logos_oos_gate_ssot_unchanged": "docs/final/artifacts/prophecy_logos_revalidation_oos_gate_latest.json",
        "windows": {
            "blind": {"start": args.blind_start, "end": args.blind_end, "role_ko": "JSONL 커버리지 전·저활성 구간"},
            "confirm": {"start": args.confirm_start, "end": args.confirm_end, "role_ko": "sparse/hybrid 실질 적중 구간"},
        },
        "gate_min_hit_rate": args.gate_min_hit_rate,
        "variants": rows_out,
        "review_ko": [
            "golden/hybrid: blind 구간 hit=0 → confirm만 통과해도 full-OOS 승격 주장 금지.",
            f"birth: blind hit={b_blind.get('directional_hit_rate_active')} "
            f"n={b_blind.get('n_active_days')} confirm hit={b_confirm.get('directional_hit_rate_active')} "
            f"n={b_confirm.get('n_active_days')} → promotion_candidate={birth.get('promotion_candidate')} "
            "(blind·confirm 각 0.52+ 필요).",
            "SSOT D=0.565217 (sparse KOSPI) 유지.",
        ],
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(text)
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
