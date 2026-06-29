#!/usr/bin/env python3
"""NEWS-EVO-BENCH — offline 4-axis loss aggregate from disk artifacts [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_news_evo_bench_result_v1_latest.json"
CONTRACT_FIXTURE = ART / "fixtures/news_evo_bench_contract_v1.example.json"

DEFAULT_PATHS = {
    "price_eval": ART / "prophecy_hit_rate_eval_latest.json",
    "general_brier": ART / "general_prophecy_brier_eval_latest.json",
    "news_rt": ART / "saving_the_news_news_rt_bench_result_v1_latest.json",
    "news_hp_rt": ART / "saving_the_news_news_hp_rt_bench_result_v1_latest.json",
    "calibration_join": ART / "news_observation_direction_join_walkforward_v1_latest.json",
}

DEFAULT_WEIGHTS = {
    "w1_price": 0.35,
    "w2_general": 0.25,
    "w3_compression_raw": 0.25,
    "w4_calibration": 0.15,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _axis_price(doc: dict[str, Any], source: Path) -> dict[str, Any]:
    metrics = doc.get("metrics") or {}
    hit = metrics.get("price_directional_hit_rate")
    n = metrics.get("n_evaluated")
    if hit is None:
        return {
            "axis_id": "NEWS-EVO-PRICE",
            "measurement_status": "NOT_MEASURED",
            "source_path": _rel(source),
            "metrics": None,
            "loss_scalar_hypo": None,
        }
    brier_proxy = max(0.0, min(1.0, 1.0 - float(hit)))
    return {
        "axis_id": "NEWS-EVO-PRICE",
        "measurement_status": "COMPLETE",
        "source_path": _rel(source),
        "metrics": {
            "direction_hit_rate": hit,
            "brier_proxy": round(brier_proxy, 6),
            "n_evaluated": n,
        },
        "loss_scalar_hypo": round(brier_proxy, 6),
        "label": "B-track price; not live order trigger",
    }


def _axis_general(doc: dict[str, Any], source: Path) -> dict[str, Any]:
    metrics = doc.get("metrics") or {}
    brier = metrics.get("mean_brier_score")
    n = metrics.get("n_evaluated")
    ece = (metrics.get("ece_binary") or {}).get("weighted_ece")
    if brier is None:
        return {
            "axis_id": "NEWS-EVO-GENERAL",
            "measurement_status": "NOT_MEASURED",
            "source_path": _rel(source),
            "metrics": None,
            "loss_scalar_hypo": None,
        }
    loss = max(0.0, min(1.0, float(brier)))
    return {
        "axis_id": "NEWS-EVO-GENERAL",
        "measurement_status": "COMPLETE",
        "source_path": _rel(source),
        "metrics": {
            "brier_score": brier,
            "n_evaluated": n,
            "ece_binary_weighted": ece,
        },
        "loss_scalar_hypo": round(loss, 6),
        "label": "general_prophecy; separate from price leg",
    }


def _axis_compression_raw(rt: dict[str, Any], hp: dict[str, Any], rt_path: Path, hp_path: Path) -> dict[str, Any]:
    rt_kpi = rt.get("kpi") or {}
    saving = rt_kpi.get("token_saving_ratio")
    jaccard = rt_kpi.get("jaccard_fidelity_proxy")
    rt_ok = rt.get("measurement_status") == "COMPLETE" and saving is not None
    hp_kpi = hp.get("kpi") or {}
    hp_saving = hp_kpi.get("token_saving_ratio_hp_weighted")
    hp_delta = (hp.get("delta_vs_news_rt_baseline") or {}).get(
        "token_saving_ratio_delta_hp_minus_baseline"
    )
    if not rt_ok:
        return {
            "axis_id": "NEWS-RT-RAW",
            "measurement_status": "NOT_MEASURED",
            "source_path": _rel(rt_path),
            "metrics": None,
            "loss_scalar_hypo": None,
            "operational_hp_ref": _rel(hp_path) if hp_path.is_file() else None,
        }
    fidelity_loss = max(0.0, min(1.0, 1.0 - float(jaccard or 0.0)))
    compression_loss = max(0.0, min(1.0, 1.0 - float(saving)))
    loss_scalar = round(0.6 * compression_loss + 0.4 * fidelity_loss, 6)
    return {
        "axis_id": "NEWS-RT-RAW",
        "measurement_status": "COMPLETE",
        "source_path": _rel(rt_path),
        "metrics": {
            "token_saving_ratio_raw": saving,
            "jaccard_fidelity_proxy_raw": jaccard,
            "promotion_gate_candidate": "raw_only",
        },
        "loss_scalar_hypo": loss_scalar,
        "operational_post_processor": {
            "source_path": _rel(hp_path),
            "token_saving_ratio_hp_weighted": hp_saving,
            "delta_hp_minus_baseline": hp_delta,
            "interpretation": "research_only; not promotion proof",
        },
        "label": "raw vs operational(HP) reported separately",
    }


def _axis_calibration(join_doc: dict[str, Any], general_doc: dict[str, Any], join_path: Path, general_path: Path) -> dict[str, Any]:
    if join_doc:
        ece = join_doc.get("ece") or join_doc.get("weighted_ece")
        rows = join_doc.get("joined_row_count") or join_doc.get("n_joined")
        if ece is not None:
            loss = max(0.0, min(1.0, float(ece)))
            return {
                "axis_id": "NEWS-EVO-CAL",
                "measurement_status": "COMPLETE",
                "source_path": _rel(join_path),
                "metrics": {"weighted_ece": ece, "joined_row_count": rows},
                "loss_scalar_hypo": round(loss, 6),
                "label": "walkforward join artifact",
            }
    ece_block = (general_doc.get("metrics") or {}).get("ece_binary") or {}
    ece = ece_block.get("weighted_ece")
    if ece is not None:
        loss = max(0.0, min(1.0, float(ece)))
        return {
            "axis_id": "NEWS-EVO-CAL",
            "measurement_status": "COMPLETE_PROXY",
            "source_path": _rel(general_path),
            "metrics": {
                "weighted_ece": ece,
                "ece_bins": ece_block.get("n_bins"),
                "proxy_from": "general_prophecy_brier_eval",
            },
            "loss_scalar_hypo": round(loss, 6),
            "label": "proxy until walkforward join artifact exists",
        }
    return {
        "axis_id": "NEWS-EVO-CAL",
        "measurement_status": "NOT_MEASURED",
        "source_path": _rel(join_path),
        "metrics": None,
        "loss_scalar_hypo": None,
    }


def run_bench(
    *,
    price_path: Path = DEFAULT_PATHS["price_eval"],
    general_path: Path = DEFAULT_PATHS["general_brier"],
    news_rt_path: Path = DEFAULT_PATHS["news_rt"],
    news_hp_path: Path = DEFAULT_PATHS["news_hp_rt"],
    calibration_path: Path = DEFAULT_PATHS["calibration_join"],
    weights: dict[str, float] | None = None,
    contract_path: Path = CONTRACT_FIXTURE,
) -> dict[str, Any]:
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    contract = _read(contract_path)
    contract_weights = (contract.get("loss_axes") or {}).get("weights_hypo") or {}
    if contract_weights and not weights:
        w["w1_price"] = float(contract_weights.get("w1_price", w["w1_price"]))
        w["w2_general"] = float(contract_weights.get("w2_general", w["w2_general"]))
        w["w3_compression_raw"] = float(contract_weights.get("w3_compression_raw", w["w3_compression_raw"]))
        w["w4_calibration"] = float(contract_weights.get("w4_calibration", w["w4_calibration"]))

    price_doc = _read(price_path)
    general_doc = _read(general_path)
    rt_doc = _read(news_rt_path)
    hp_doc = _read(news_hp_path)
    join_doc = _read(calibration_path)

    axes = {
        "L_price": _axis_price(price_doc, price_path),
        "L_general": _axis_general(general_doc, general_path),
        "L_compression_raw": _axis_compression_raw(rt_doc, hp_doc, news_rt_path, news_hp_path),
        "L_calibration": _axis_calibration(join_doc, general_doc, calibration_path, general_path),
    }

    measured = [a for a in axes.values() if a.get("measurement_status", "").startswith("COMPLETE")]
    partial = any(a.get("measurement_status") == "COMPLETE_PROXY" for a in axes.values())
    contrib: dict[str, float | None] = {}
    total = 0.0
    weight_sum = 0.0
    key_map = {
        "L_price": "w1_price",
        "L_general": "w2_general",
        "L_compression_raw": "w3_compression_raw",
        "L_calibration": "w4_calibration",
    }
    for name, axis in axes.items():
        loss = axis.get("loss_scalar_hypo")
        wk = key_map[name]
        weight = w[wk]
        if loss is not None:
            contrib[name] = round(float(loss) * weight, 6)
            total += float(loss) * weight
            weight_sum += weight
        else:
            contrib[name] = None

    if len(measured) == 4 and not partial:
        bench_status = "COMPLETE"
    elif measured:
        bench_status = "COMPLETE_PARTIAL"
    else:
        bench_status = "NOT_MEASURED"

    l_total = round(total / weight_sum, 6) if weight_sum > 0 else None

    return {
        "schema": "saving_the_news_news_evo_bench_result_v1",
        "axis_id": "NEWS-EVO-BENCH",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "generated_at_utc": _utc_now(),
        "measurement_status": bench_status,
        "ready_for_external_send": False,
        "contract_ref": _rel(contract_path),
        "regime_id": "regime_saving_the_news_dual_architecture_hypo",
        "weights_hypo": w,
        "loss_axes": axes,
        "composite_hypo": {
            "formula": "L_total = w1*L_price + w2*L_general + w3*L_compression_raw + w4*L_calibration",
            "L_total_hypo": l_total,
            "weighted_contributions": contrib,
            "forbidden": "Not single-scalar Track A or CMS promotion gate",
        },
        "raw_repair_dual_report": {
            "raw": {
                "news_rt_token_saving": (rt_doc.get("kpi") or {}).get("token_saving_ratio"),
                "news_rt_jaccard": (rt_doc.get("kpi") or {}).get("jaccard_fidelity_proxy"),
            },
            "operational_post_processor": {
                "news_hp_rt_token_saving": (hp_doc.get("kpi") or {}).get("token_saving_ratio_hp_weighted"),
                "news_hp_rt_jaccard": (hp_doc.get("kpi") or {}).get("jaccard_fidelity_proxy_hp_weighted"),
                "delta_token_saving_hp_minus_raw": (hp_doc.get("delta_vs_news_rt_baseline") or {}).get(
                    "token_saving_ratio_delta_hp_minus_baseline"
                ),
            },
            "delta_note": "operational(HP) is research_only; never collapse with raw for promotion",
        },
        "forbidden_interpretation": [
            "Not Track A promotion or live trading GO.",
            "Not CMS publish approval.",
            "L_total_hypo is offline aggregate only — not model solved.",
            "DSPy/GEPA evolution not executed by this runner.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--price-eval", type=Path, default=DEFAULT_PATHS["price_eval"])
    ap.add_argument("--general-brier", type=Path, default=DEFAULT_PATHS["general_brier"])
    ap.add_argument("--news-rt", type=Path, default=DEFAULT_PATHS["news_rt"])
    ap.add_argument("--news-hp-rt", type=Path, default=DEFAULT_PATHS["news_hp_rt"])
    ap.add_argument("--calibration-join", type=Path, default=DEFAULT_PATHS["calibration_join"])
    ap.add_argument("--contract", type=Path, default=CONTRACT_FIXTURE)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    doc = run_bench(
        price_path=args.price_eval,
        general_path=args.general_brier,
        news_rt_path=args.news_rt,
        news_hp_path=args.news_hp_rt,
        calibration_path=args.calibration_join,
        contract_path=args.contract,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.out_json} status={doc['measurement_status']} "
        f"L_total_hypo={doc['composite_hypo'].get('L_total_hypo')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
