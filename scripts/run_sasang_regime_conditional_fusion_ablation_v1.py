#!/usr/bin/env python3
"""[HYPO] Sasang regime conditional fusion ablation (research_only).

Compares fusion policy arms for veto × supplier_tight split vs counterfactual returns.
Does not modify Track A, live trading, or promotion gates.
"""

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

from scripts.sasang_regime_mkm_split_v1 import (  # noqa: E402
    DEFAULT_GEUMHWA_MIN_CONSECUTIVE_DAYS,
    FUSION_POLICY_ARMS,
    RECOMMENDED_REGIME_ID,
    build_supplier_regimes_for_dates,
    daily_fusion_posture,
    load_sasang_rows,
    load_veto_by_date,
    regime_mkm_split_v1,
    veto_for_date,
)

DEFAULT_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_COUNTERFACTUAL = ROOT / "reports/samsung_sasang_veto_hold_counterfactual_v1_latest.json"
DEFAULT_FUSION = ROOT / "docs/final/artifacts/independent_lens_fusion_stub_latest.json"
DEFAULT_OUT = ROOT / "reports/sasang_regime_conditional_fusion_ablation_v1_latest.json"
SCHEMA = "sasang_regime_conditional_fusion_ablation_v1"

TICKERS = {
    "samsung": "005930.KS",
    "hynix": "000660.KS",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _fetch_closes(ticker: str, period: str = "1y") -> dict[str, float]:
    import yfinance as yf

    df = yf.Ticker(ticker).history(period=period, auto_adjust=True).dropna()
    if df.empty:
        raise RuntimeError(f"no history for {ticker}")
    return {idx.date().isoformat(): float(row["Close"]) for idx, row in df.iterrows()}


def _fusion_veto_context(fusion: dict[str, Any]) -> dict[str, Any]:
    for row in fusion.get("inputs") or []:
        if not isinstance(row, dict) or row.get("lens_id") != "market_sasang":
            continue
        block = row.get("market_sasang_lens_v1") or {}
        codes = block.get("veto_reason_codes")
        return {
            "veto_force_hold": bool(block.get("veto_force_hold")),
            "veto_reason_codes": [str(c) for c in codes] if isinstance(codes, list) else [],
        }
    return {"veto_force_hold": None, "veto_reason_codes": []}


def _simulate_policy_path(
    dates: list[str],
    veto_map: dict[str, bool],
    supplier_map: dict[str, bool],
    policy: str,
) -> dict[str, Any]:
    in_market = False
    posture_counts: dict[str, int] = {}
    daily: list[dict[str, Any]] = []
    for d in dates:
        veto = bool(veto_for_date(d, veto_map))
        tight = bool(supplier_map.get(d, False))
        posture, in_market = daily_fusion_posture(
            veto=veto, supplier_tight=tight, in_market=in_market, policy=policy
        )
        posture_counts[posture] = posture_counts.get(posture, 0) + 1
        daily.append(
            {
                "eval_date": d,
                "force_hold": veto,
                "supplier_tight": tight,
                "posture": posture,
                "in_market_after": in_market,
            }
        )
    return {
        "policy": policy,
        "posture_counts": posture_counts,
        "daily": daily,
        "final_in_market": in_market,
    }


def _policy_to_regime_key(policy: str) -> str | None:
    if policy == "regime_mkm_split_tactical":
        return "regime_mkm_split_v1_tactical"
    if policy == "regime_mkm_split_structural":
        return "regime_mkm_split_v1_structural_entry"
    return None


def run_ablation(
    *,
    sasang_path: Path,
    counterfactual_path: Path,
    fusion_path: Path,
    out_path: Path,
    period: str = "1y",
) -> dict[str, Any]:
    veto_map = load_veto_by_date(sasang_path)
    sasang_rows = load_sasang_rows(sasang_path)
    sasang_dates = sorted(veto_map.keys())
    if not sasang_dates:
        raise RuntimeError("no sasang veto rows")

    fusion = _read_json(fusion_path)
    counterfactual = _read_json(counterfactual_path)

    instruments: dict[str, Any] = {}
    for key, ticker in TICKERS.items():
        closes = _fetch_closes(ticker, period=period)
        all_dates = sorted(closes.keys())
        win_sasang = [d for d in all_dates if d in veto_map]
        if len(win_sasang) < 2:
            instruments[key] = {"status": "no_overlap_with_sasang_window"}
            continue

        regimes = build_supplier_regimes_for_dates(closes, win_sasang, sasang_rows)
        supplier = regimes[RECOMMENDED_REGIME_ID]

        policy_paths: dict[str, Any] = {}
        for policy in FUSION_POLICY_ARMS:
            policy_paths[policy] = _simulate_policy_path(win_sasang, veto_map, supplier, policy)

        cf_inst = (counterfactual.get("instruments") or {}).get(key) or {}
        cf_reg = (cf_inst.get("regime_conditional_sasang_window") or {}).get(RECOMMENDED_REGIME_ID) or {}
        cf_1y = (cf_inst.get("regime_conditional_1y") or {}).get(RECOMMENDED_REGIME_ID) or {}

        policy_returns: dict[str, Any] = {}
        for policy in FUSION_POLICY_ARMS:
            rk = _policy_to_regime_key(policy)
            if rk and cf_reg.get(rk):
                policy_returns[policy] = {
                    "sasang_window": cf_reg[rk],
                    "source": "counterfactual_artifact",
                }
            elif policy in ("literal_veto_hold", "eternal_wait_on_veto"):
                sw = cf_inst.get("strategies_sasang_window") or {}
                if policy == "literal_veto_hold" and sw.get("strict_veto_daily"):
                    policy_returns[policy] = {"sasang_window": sw["strict_veto_daily"], "source": "counterfactual_artifact"}
                if policy == "eternal_wait_on_veto" and sw.get("eternal_cash_wait"):
                    policy_returns[policy] = {"sasang_window": sw["eternal_cash_wait"], "source": "counterfactual_artifact"}

        geumhwa_raw = regimes.get("geumhwa_execution") or {}
        geumhwa_gated = regimes.get("geumhwa_execution_gated5") or {}
        geumhwa_true_days = sum(1 for d in win_sasang if geumhwa_raw.get(d))
        geumhwa_gated_days = sum(1 for d in win_sasang if geumhwa_gated.get(d))

        instruments[key] = {
            "ticker": ticker,
            "sasang_window": {"start": win_sasang[0], "end": win_sasang[-1], "n_days": len(win_sasang)},
            "recommended_regime_id": RECOMMENDED_REGIME_ID,
            "policy_paths": policy_paths,
            "policy_returns_vs_counterfactual": policy_returns,
            "geumhwa_sparse_gate": {
                "raw_true_days": geumhwa_true_days,
                "gated5_true_days": geumhwa_gated_days,
                "min_consecutive_days": DEFAULT_GEUMHWA_MIN_CONSECUTIVE_DAYS,
                "gated_regime_1y": cf_1y.get("geumhwa_execution_gated5"),
            },
            "live_split_recompute_sasang": {
                "regime_mkm_split_v1_tactical": regime_mkm_split_v1(
                    closes, win_sasang, veto_map, supplier, structural_entry=False
                ),
            },
        }

    ss = instruments.get("samsung", {})
    bah = (
        ((counterfactual.get("instruments") or {}).get("samsung") or {})
        .get("strategies_sasang_window", {})
        .get("buy_and_hold", {})
        .get("total_return_pct")
    )
    tac_ret = (
        ss.get("policy_returns_vs_counterfactual", {})
        .get("regime_mkm_split_tactical", {})
        .get("sasang_window", {})
        .get("total_return_pct")
    )
    lit_ret = (
        ss.get("policy_returns_vs_counterfactual", {})
        .get("literal_veto_hold", {})
        .get("sasang_window", {})
        .get("total_return_pct")
    )

    headline: list[str] = []
    if bah is not None and tac_ret is not None:
        headline.append(
            f"삼성 sasang창 regime_mkm_split tactical {tac_ret}% vs BAH {bah}% "
            f"(underperform {round(tac_ret - bah, 4)}pp)"
        )
    if bah is not None and lit_ret is not None:
        headline.append(
            f"삼성 sasang창 literal_veto_hold {lit_ret}% vs BAH {bah}% "
            f"(underperform {round(lit_ret - bah, 4)}pp)"
        )

    doc = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "purpose_ko": "fusion policy arms ablation: literal veto vs regime_mkm_split vs eternal wait",
        "recommended_policy": "regime_mkm_split_tactical",
        "recommended_regime_id": RECOMMENDED_REGIME_ID,
        "policy_arms": list(FUSION_POLICY_ARMS),
        "inputs": {
            "sasang_per_date": str(sasang_path.relative_to(ROOT)).replace("\\", "/"),
            "counterfactual_artifact": str(counterfactual_path.relative_to(ROOT)).replace("\\", "/"),
            "fusion_stub": str(fusion_path.relative_to(ROOT)).replace("\\", "/"),
            "fusion_veto_context": _fusion_veto_context(fusion),
        },
        "headline_ko": headline,
        "instruments": instruments,
        "interpretation_ko": [
            "literal_veto_hold = lens_conflict R5 — force_hold를 매도/현금으로 literal 적용",
            "regime_mkm_split_tactical = supplier_tight 롱 + veto는 추격 진입만 차단",
            "eternal_wait_on_veto = generic 관망 negative control",
            "geumhwa_execution_gated5 = sparse geumhwa overfit 완화 — 단독 structural leg 금지",
        ],
        "reproduce": "py scripts/run_sasang_regime_conditional_fusion_ablation_v1.py",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--counterfactual-json", type=Path, default=DEFAULT_COUNTERFACTUAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--period", default="1y")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    def _abs(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    try:
        doc = run_ablation(
            sasang_path=_abs(args.sasang_jsonl),
            counterfactual_path=_abs(args.counterfactual_json),
            fusion_path=_abs(args.fusion_json),
            out_path=_abs(args.output),
            period=args.period,
        )
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"WROTE: {_abs(args.output)}")
    for line in doc.get("headline_ko") or []:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
