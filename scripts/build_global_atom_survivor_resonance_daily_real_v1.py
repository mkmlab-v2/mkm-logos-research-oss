# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.5, M:0.7}
# Balance: 88
# Purpose: Build real-lane survivor resonance daily JSONL from W3 measured batch outputs.
# Keywords: global-atom, survivor, resonance, real, w3, jsonl
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_KNOWLEDGE_REPORT_JSON = ART / "bible_meaning_knowledge_ip_report_latest.json"
DEFAULT_CANDIDATES_JSON = ART / "bible_meaning_insight_candidates_latest.json"
DEFAULT_W3_RESULT_JSON = ART / "W3_RESONANCE_BATCH_RESULT_V4.json"
DEFAULT_SIDECAR_JSON = ART / "btrack_prophecy_score_insight_sidecar_30y_latest.json"
DEFAULT_MAPPING_JSON = ART / "global_atom_survivor_w3_direct_mapping_latest.json"
DEFAULT_OUT_JSONL = ART / "global_atom_survivor_resonance_daily_real_latest.jsonl"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_float(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _resolve_effective_weights(
    w_candidate: float,
    w_flow: float,
    w_temporal: float,
    flow_unit: float,
    adaptive: bool,
) -> tuple[float, float, float, str]:
    if not adaptive:
        return w_candidate, w_flow, w_temporal, "static"
    if flow_unit >= 0.7:
        # In high-flow/unstable regimes, emphasize flow-reactive signals.
        return w_candidate * 0.75, w_flow * 1.6, w_temporal * 0.9, "high_volatility"
    if flow_unit <= 0.3:
        # In calmer regimes, favor candidate consistency.
        return w_candidate * 1.2, w_flow * 0.7, w_temporal * 1.1, "low_volatility"
    return w_candidate, w_flow, w_temporal, "mid_volatility"


def _extract_survivors(knowledge: dict[str, Any], candidates_doc: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = candidates_doc.get("candidates") if isinstance(candidates_doc.get("candidates"), list) else []
    if not candidates:
        return []
    survivor_count = int(((knowledge.get("summary") or {}).get("survivor_count")) or 5)
    sids: set[str] = set()
    explicit_ids = knowledge.get("survivor_ids")
    explicit = knowledge.get("survivors")
    if isinstance(explicit_ids, list):
        sids |= {str(x) for x in explicit_ids if x}
    if isinstance(explicit, list):
        for x in explicit:
            if isinstance(x, dict) and x.get("candidate_id"):
                sids.add(str(x.get("candidate_id")))
            elif x:
                sids.add(str(x))
    if sids:
        matched = [c for c in candidates if str(c.get("candidate_id")) in sids]
        if matched:
            return matched[:survivor_count]
    ranked = sorted(
        [c for c in candidates if isinstance(c, dict)],
        key=lambda c: (_safe_float(c.get("hub_score")), _safe_float(c.get("path_score")), _safe_float(c.get("cluster_size"))),
        reverse=True,
    )
    return ranked[:survivor_count]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build real survivor resonance daily JSONL from W3 measured batch.")
    ap.add_argument("--knowledge-report-json", type=Path, default=DEFAULT_KNOWLEDGE_REPORT_JSON)
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES_JSON)
    ap.add_argument("--w3-result-json", type=Path, default=DEFAULT_W3_RESULT_JSON)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR_JSON)
    ap.add_argument("--mapping-json", type=Path, default=DEFAULT_MAPPING_JSON)
    ap.add_argument("--w-candidate", type=float, default=0.6)
    ap.add_argument("--w-flow", type=float, default=0.3)
    ap.add_argument("--w-temporal", type=float, default=0.1)
    ap.add_argument("--w-market-shock", type=float, default=0.0)
    ap.add_argument("--regime-adaptive-weighting", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    args = ap.parse_args()

    knowledge = _read_json(args.knowledge_report_json)
    candidates_doc = _read_json(args.candidates_json)
    w3 = _read_json(args.w3_result_json)
    sidecar = _read_json(args.sidecar_json)
    mapping_doc = _read_json(args.mapping_json)

    survivors = _extract_survivors(knowledge, candidates_doc)
    per_dates = sidecar.get("per_date_features") if isinstance(sidecar.get("per_date_features"), list) else []

    top_n = w3.get("top_n_results") if isinstance(w3.get("top_n_results"), list) else []
    measured_scores = [_safe_float(x.get("resonance_score")) for x in top_n if isinstance(x, dict)]
    measured_scores = [x for x in measured_scores if x > 0.0]
    measured_global = _clamp01(sum(measured_scores) / len(measured_scores)) if measured_scores else 0.5
    trace_rows = w3.get("scoring_trace") if isinstance(w3.get("scoring_trace"), list) else []
    trace_map: dict[str, dict[str, float]] = {}
    for tr in trace_rows:
        if not isinstance(tr, dict):
            continue
        sid = str(tr.get("sample_id") or "").strip()
        comp = tr.get("score_components") if isinstance(tr.get("score_components"), dict) else {}
        aux = comp.get("aux_non_gating") if isinstance(comp.get("aux_non_gating"), dict) else {}
        if sid:
            trace_map[sid] = {
                "transition_pressure": _safe_float(aux.get("transition_pressure"), 0.0),
                "geumhwa_aux_score": _safe_float(aux.get("geumhwa_aux_score"), 0.0),
            }
    sample_score_map = {
        str(x.get("sample_id")): _clamp01(
            0.5 * _safe_float(x.get("resonance_score"), measured_global)
            + 0.3 * _safe_float((trace_map.get(str(x.get("sample_id")) or {}) or {}).get("geumhwa_aux_score"), 0.0)
            + 0.2 * _safe_float((trace_map.get(str(x.get("sample_id")) or {}) or {}).get("transition_pressure"), 0.0)
        )
        for x in top_n
        if isinstance(x, dict) and x.get("sample_id")
    }
    mapping_rows = mapping_doc.get("rows") if isinstance(mapping_doc.get("rows"), list) else []
    candidate_to_samples: dict[str, list[str]] = {}
    for row in mapping_rows:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("candidate_id") or "").strip()
        sample_ids = row.get("assigned_sample_ids") if isinstance(row.get("assigned_sample_ids"), list) else []
        sample_ids = [str(x).strip() for x in sample_ids if str(x).strip()]
        if cid and sample_ids:
            candidate_to_samples[cid] = sample_ids

    rows_out: list[dict[str, Any]] = []
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for feat in per_dates:
        if not isinstance(feat, dict):
            continue
        d = str(feat.get("eval_date") or "").strip()
        instrument = str(feat.get("instrument") or "").strip().lower()
        if not d or not instrument:
            continue
        # Keep the measured global score dominant; tiny temporal modulation from non-price context.
        lines = _safe_float(feat.get("myeongni_insight_lines_cumulative_through_eval_date"), 0.0)
        temporal_mod = _clamp01(lines / 200.0)
        score_ctx = feat.get("score_row_context") if isinstance(feat.get("score_row_context"), dict) else {}
        flow_score = _safe_float(score_ctx.get("flow_score_for_reversal"), 0.0)
        flow_unit = _clamp01((flow_score + 10000.0) / 20000.0)
        daily_return_abs = abs(_safe_float(score_ctx.get("daily_return"), 0.0))
        market_shock_unit = _clamp01(daily_return_abs / 0.05)
        eff_wc, eff_wf, eff_wt, regime_bucket = _resolve_effective_weights(
            float(args.w_candidate),
            float(args.w_flow),
            float(args.w_temporal),
            flow_unit,
            bool(args.regime_adaptive_weighting),
        )
        eff_wm = max(0.0, float(args.w_market_shock))
        w_sum = max(1e-9, float(eff_wc + eff_wf + eff_wt + eff_wm))
        for s in survivors:
            cid = str(s.get("candidate_id") or "")
            mapped_samples = candidate_to_samples.get(cid, [])
            mapped_scores = [sample_score_map.get(sid) for sid in mapped_samples if sample_score_map.get(sid) is not None]
            candidate_real = _clamp01(sum(mapped_scores) / len(mapped_scores)) if mapped_scores else measured_global
            mapping_quality = "direct_mapping_seeded_v1" if mapped_scores else "weak_mapping"
            rows_out.append(
                {
                    "schema": "global_atom_survivor_resonance_daily_row_v1",
                    "generated_at_utc": ts,
                    "research_only": True,
                    "signal_mode": "real_from_w3_batch_topn_v1",
                    "mapping_quality": mapping_quality,
                    "date": d,
                    "instrument": instrument,
                    "candidate_id": cid,
                    "symbol_id": cid,
                    "source_node_id": s.get("source_node_id"),
                    "resonance_score": round(
                        _clamp01(
                            (
                                eff_wc * candidate_real
                                + eff_wf * flow_unit
                                + eff_wt * temporal_mod
                                + eff_wm * market_shock_unit
                            )
                            / w_sum
                        ),
                        6,
                    ),
                    "components": {
                        "measured_w3_global_topn_score": round(measured_global, 6),
                        "candidate_mapped_w3_score": round(candidate_real, 6),
                        "mapped_sample_ids": mapped_samples,
                        "flow_score_unit": round(flow_unit, 6),
                        "temporal_modulator_from_myeongni_lines": round(temporal_mod, 6),
                        "market_shock_unit_from_abs_daily_return": round(market_shock_unit, 6),
                        "effective_weights": {
                            "w_candidate": round(eff_wc, 6),
                            "w_flow": round(eff_wf, 6),
                            "w_temporal": round(eff_wt, 6),
                            "w_market_shock": round(eff_wm, 6),
                            "mode": "regime_adaptive_v1" if args.regime_adaptive_weighting else "static_v1",
                            "regime_bucket": regime_bucket,
                        },
                    },
                }
            )

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows_out) + ("\n" if rows_out else ""), encoding="utf-8")
    print(f"WROTE: {args.output_jsonl}")
    print(f"survivor_count={len(survivors)} per_date_features={len(per_dates)} rows={len(rows_out)} measured_global={measured_global:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
