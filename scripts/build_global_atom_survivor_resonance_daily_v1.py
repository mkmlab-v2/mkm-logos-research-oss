# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.5, M:0.7}
# Balance: 89
# Purpose: Build daily survivor resonance JSONL from sidecar non-price context signals.
# Keywords: global-atom, survivor, resonance, jsonl, btrack
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_KNOWLEDGE_REPORT_JSON = ART / "bible_meaning_knowledge_ip_report_latest.json"
DEFAULT_CANDIDATES_JSON = ART / "bible_meaning_insight_candidates_latest.json"
DEFAULT_SIDECAR_JSON = ART / "btrack_prophecy_score_insight_sidecar_30y_latest.json"
DEFAULT_OUT_JSONL = ART / "global_atom_survivor_resonance_daily_latest.jsonl"


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


def _extract_survivors(knowledge: dict[str, Any], candidates_doc: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = candidates_doc.get("candidates") if isinstance(candidates_doc.get("candidates"), list) else []
    if not candidates:
        return []
    survivor_count = int(((knowledge.get("summary") or {}).get("survivor_count")) or 5)
    explicit_ids = knowledge.get("survivor_ids")
    explicit = knowledge.get("survivors")
    sids: set[str] = set()
    if isinstance(explicit_ids, list):
        sids |= {str(x) for x in explicit_ids if x}
    if isinstance(explicit, list):
        for x in explicit:
            if isinstance(x, dict):
                cid = x.get("candidate_id")
                if cid:
                    sids.add(str(cid))
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


def _flow_to_unit(flow_score: float) -> float:
    # Smoothly map to 0..1 without hard clipping.
    return _clamp01((math.tanh(flow_score / 10000.0) + 1.0) * 0.5)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build survivor resonance daily JSONL from sidecar features.")
    ap.add_argument("--knowledge-report-json", type=Path, default=DEFAULT_KNOWLEDGE_REPORT_JSON)
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES_JSON)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR_JSON)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    args = ap.parse_args()

    knowledge = _read_json(args.knowledge_report_json)
    candidates_doc = _read_json(args.candidates_json)
    sidecar = _read_json(args.sidecar_json)

    survivors = _extract_survivors(knowledge, candidates_doc)
    per_dates = sidecar.get("per_date_features") if isinstance(sidecar.get("per_date_features"), list) else []
    lens_global = sidecar.get("lens_globals_for_sidecar") if isinstance(sidecar.get("lens_globals_for_sidecar"), dict) else {}
    logos = lens_global.get("logos") if isinstance(lens_global.get("logos"), dict) else {}
    logos_pressure = max(0.0, -_safe_float(logos.get("direction_score"), 0.0)) * _safe_float(logos.get("confidence"), 0.0)
    logos_pressure = _clamp01(logos_pressure)

    rows_out: list[dict[str, Any]] = []
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for feat in per_dates:
        if not isinstance(feat, dict):
            continue
        d = str(feat.get("eval_date") or "").strip()
        instrument = str(feat.get("instrument") or "").strip().lower()
        if not d or not instrument:
            continue
        score_ctx = feat.get("score_row_context") if isinstance(feat.get("score_row_context"), dict) else {}
        flow_unit = _flow_to_unit(_safe_float(score_ctx.get("flow_score_for_reversal"), 0.0))
        insight_lines = _safe_float(feat.get("myeongni_insight_lines_cumulative_through_eval_date"), 0.0)
        insight_unit = _clamp01(insight_lines / 50.0)
        # Proxy resonance from non-price context only (B-track observation signal).
        resonance = _clamp01(0.55 * logos_pressure + 0.30 * flow_unit + 0.15 * insight_unit)
        for s in survivors:
            rows_out.append(
                {
                    "schema": "global_atom_survivor_resonance_daily_row_v1",
                    "generated_at_utc": ts,
                    "research_only": True,
                    "signal_mode": "proxy_from_sidecar_non_price_context_v1",
                    "date": d,
                    "instrument": instrument,
                    "candidate_id": s.get("candidate_id"),
                    "symbol_id": s.get("candidate_id"),
                    "source_node_id": s.get("source_node_id"),
                    "resonance_score": round(resonance, 6),
                    "components": {
                        "logos_pressure": round(logos_pressure, 6),
                        "flow_score_unit": round(flow_unit, 6),
                        "myeongni_insight_lines_unit": round(insight_unit, 6),
                    },
                }
            )

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows_out) + ("\n" if rows_out else ""), encoding="utf-8")
    print(f"WROTE: {args.output_jsonl}")
    print(f"survivor_count={len(survivors)} per_date_features={len(per_dates)} rows={len(rows_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
