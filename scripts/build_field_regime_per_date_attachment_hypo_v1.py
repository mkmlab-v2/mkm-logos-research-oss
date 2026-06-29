#!/usr/bin/env python3
"""Per-date Field regime_map attachment PoC (B-track, reports lane).

Upgrades year-only quad→regime_map rank to **eval_date** granularity via:
1) quad uft_v2_timeline DOY interpolation within calendar year
2) optional OHLCV rolling state 4D proxy → regime_map cosine rank

Does not attach live trading triggers or mutate production score JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_REGIME_MAP = ROOT / "data/regimes/regime_map.json"
DEFAULT_QUAD_JSON = ROOT / "data/quad_fusion_training/quad_fusion_result_20260308_230751.json"
DEFAULT_KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/field_regime_per_date_attachment_hypo_v1_latest.json"
SCHEMA = "field_regime_per_date_attachment_hypo_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _quad_year_vectors(quad_json: Path) -> dict[int, dict[str, float]]:
    quad = _load_json(quad_json)
    out: dict[int, dict[str, float]] = {}
    for row in quad.get("uft_v2_timeline") or []:
        yr = int(row.get("year", -1))
        u4 = row.get("unified_4d_vector") or {}
        if yr < 0 or not u4:
            continue
        out[yr] = {k: float(u4[k]) for k in ("S", "L", "K", "M") if k in u4}
    return out


def _interp_u4(
    year_vecs: dict[int, dict[str, float]],
    eval_date: str,
) -> tuple[dict[str, float], str]:
    dt = datetime.strptime(eval_date[:10], "%Y-%m-%d")
    yr = dt.year
    doy = dt.timetuple().tm_yday
    alpha = min(1.0, max(0.0, (doy - 1) / 365.0))
    cur = year_vecs.get(yr)
    prev = year_vecs.get(yr - 1)
    if cur and prev:
        u4 = {k: (1.0 - alpha) * prev[k] + alpha * cur[k] for k in ("S", "L", "K", "M")}
        return u4, f"quad_doy_interp_{yr-1}_to_{yr}_alpha_{alpha:.4f}"
    if cur:
        return cur, f"quad_year_flat_{yr}"
    if prev:
        return prev, f"quad_year_flat_{yr-1}_fallback"
    return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}, "missing_quad_fallback_uniform"


def _ohlcv_state_u4(kospi_csv: Path, eval_date: str) -> tuple[dict[str, float] | None, str]:
    if not kospi_csv.is_file():
        return None, "missing_kospi_csv"
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.btrack_causal_ohlc_features_v1 import (  # noqa: WPS433
        build_causal_feature_map,
        load_btc_ohlc_by_date,
    )

    ohlc = load_btc_ohlc_by_date(kospi_csv)
    feat = build_causal_feature_map(ohlc).get(eval_date[:10])
    if not feat:
        return None, "missing_features_at_eval"
    vol5 = float(feat.get("realized_vol_5d") or 0.0)
    dd = abs(float(feat.get("drawdown_20d") or 0.0))
    pr = float(feat.get("prior_range_position") or 0.5)
    ovn = abs(float(feat.get("overnight_return") or 0.0))
    # Observation-only 4D proxy (not asserted as live regime fingerprint SSOT).
    s = min(1.0, ovn * 8.0 + pr * 0.35)
    l = min(1.0, max(0.0, 1.0 - vol5 * 10.0))
    k = min(1.0, vol5 * 12.0)
    m = min(1.0, dd * 4.0)
    total = s + l + k + m
    if total <= 0:
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}, "ohlcv_proxy_uniform_fallback"
    return (
        {"S": s / total, "L": l / total, "K": k / total, "M": m / total},
        "ohlcv_state_proxy_kospi",
    )


def _rank_primary(
    u4_raw: dict[str, float],
    *,
    regime_map: Path,
    exclude_regime_ids: set[str],
    vector_source: str,
) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.rank_quad_timeline_year_vs_regime_fingerprints import (  # noqa: WPS433
        _build_ranking_doc,
        _l2n,
    )

    v = _l2n(u4_raw)
    doc = _build_ranking_doc(
        v_year=v,
        u4_raw=u4_raw,
        vector_source=vector_source,
        extra_meta={},
        regime_map=regime_map,
        btc_ext_map=None,
        no_btc_ext=True,
        exclude_regime_ids=exclude_regime_ids,
    )
    top = (doc.get("historical_regimes_ranking") or [{}])[0]
    return {
        "primary_regime_id": doc.get("primary_historical_regime"),
        "top_cosine": top.get("cosine_similarity"),
        "vector_source": vector_source,
        "ranking_top3": (doc.get("historical_regimes_ranking") or [])[:3],
    }


def _year_level_primary(
    year_vecs: dict[int, dict[str, float]],
    yr: int,
    *,
    regime_map: Path,
    exclude_regime_ids: set[str],
) -> str | None:
    u4 = year_vecs.get(yr)
    if not u4:
        return None
    return _rank_primary(
        u4,
        regime_map=regime_map,
        exclude_regime_ids=exclude_regime_ids,
        vector_source=f"quad_year_flat_{yr}",
    ).get("primary_regime_id")


def build_attachment(
    *,
    eval_dates: list[str],
    regime_map: Path,
    quad_json: Path,
    kospi_csv: Path,
    exclude_regime_ids: set[str],
) -> dict[str, Any]:
    year_vecs = _quad_year_vectors(quad_json)
    rows: list[dict[str, Any]] = []
    diverge_quad_vs_year = 0
    diverge_ohlcv_vs_quad = 0

    for ed in sorted(set(eval_dates)):
        u4_interp, interp_src = _interp_u4(year_vecs, ed)
        quad_attach = _rank_primary(
            u4_interp,
            regime_map=regime_map,
            exclude_regime_ids=exclude_regime_ids,
            vector_source=interp_src,
        )
        yr = int(ed[:4])
        year_primary = _year_level_primary(
            year_vecs, yr, regime_map=regime_map, exclude_regime_ids=exclude_regime_ids
        )
        if year_primary and quad_attach.get("primary_regime_id") != year_primary:
            diverge_quad_vs_year += 1

        ohlcv_u4, ohlcv_src = _ohlcv_state_u4(kospi_csv, ed)
        ohlcv_attach: dict[str, Any] | None = None
        if ohlcv_u4:
            ohlcv_attach = _rank_primary(
                ohlcv_u4,
                regime_map=regime_map,
                exclude_regime_ids=exclude_regime_ids,
                vector_source=ohlcv_src,
            )
            if ohlcv_attach.get("primary_regime_id") != quad_attach.get("primary_regime_id"):
                diverge_ohlcv_vs_quad += 1

        rows.append(
            {
                "eval_date": ed,
                "year_level_primary_regime_id": year_primary,
                "quad_doy_attachment": quad_attach,
                "ohlcv_state_attachment": ohlcv_attach,
                "diverges_quad_from_year_level": bool(
                    year_primary and quad_attach.get("primary_regime_id") != year_primary
                ),
                "diverges_ohlcv_from_quad_doy": bool(
                    ohlcv_attach
                    and ohlcv_attach.get("primary_regime_id") != quad_attach.get("primary_regime_id")
                ),
            }
        )

    primary_counts_quad: dict[str, int] = {}
    primary_counts_ohlcv: dict[str, int] = {}
    for r in rows:
        qid = str((r.get("quad_doy_attachment") or {}).get("primary_regime_id") or "none")
        primary_counts_quad[qid] = primary_counts_quad.get(qid, 0) + 1
        oid = str((r.get("ohlcv_state_attachment") or {}).get("primary_regime_id") or "none")
        primary_counts_ohlcv[oid] = primary_counts_ohlcv.get(oid, 0) + 1

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "non_gating": True,
        "live_regime_attached": False,
        "field_layer": {
            "primary_source": "regime_map.json fingerprints",
            "attachment_methods": ["quad_doy_interp", "ohlcv_state_proxy_kospi"],
            "operator_hint_ko": "일자 부착 PoC — 관측·연구용. 실전 트리거·Track A 자동 합선 금지.",
        },
        "inputs": {
            "regime_map": str(regime_map),
            "quad_json": str(quad_json),
            "kospi_csv": str(kospi_csv),
            "n_eval_dates": len(rows),
        },
        "summary": {
            "diverge_quad_doy_from_year_level_count": diverge_quad_vs_year,
            "diverge_ohlcv_from_quad_doy_count": diverge_ohlcv_vs_quad,
            "primary_regime_counts_quad_doy": primary_counts_quad,
            "primary_regime_counts_ohlcv_state": primary_counts_ohlcv,
        },
        "rows": rows,
        "track_wall": {"auto_bridge_to_a_track": False, "live_trading_trigger": False},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-date regime_map Field attachment PoC.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--regime-map", type=Path, default=DEFAULT_REGIME_MAP)
    ap.add_argument("--quad-json", type=Path, default=DEFAULT_QUAD_JSON)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--exclude-regime-ids", type=str, default="unknown")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _load_json(args.score_json)
    eval_dates = sorted(
        {
            str(r.get("eval_date") or "")[:10]
            for r in doc.get("rows", [])
            if isinstance(r, dict) and str(r.get("eval_date") or "").strip()
        }
    )
    if not eval_dates:
        raise SystemExit("no eval_dates in score json")

    exclude_ids = {x.strip() for x in args.exclude_regime_ids.split(",") if x.strip()}
    out_doc = build_attachment(
        eval_dates=eval_dates,
        regime_map=args.regime_map,
        quad_json=args.quad_json,
        kospi_csv=args.kospi_csv,
        exclude_regime_ids=exclude_ids,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "wrote": str(args.output),
                "n_dates": len(eval_dates),
                "summary": out_doc["summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
