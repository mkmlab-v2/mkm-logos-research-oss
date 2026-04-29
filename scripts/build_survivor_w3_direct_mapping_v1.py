# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.6}
# Balance: 87
# Purpose: Build direct survivor-to-W3 sample mapping table for real resonance builder.
# Keywords: mapping, survivor, w3, direct, btrack
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
DEFAULT_OUTPUT_JSON = ART / "global_atom_survivor_w3_direct_mapping_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_float(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _survivor_rank_score(row: dict[str, Any]) -> float:
    return (
        1.5 * _safe_float(row.get("fusion_candidate_score"), 0.0)
        + 1.0 * _safe_float(row.get("hub_score"), 0.0)
        + 0.5 * _safe_float(row.get("path_score"), 0.0)
        + 0.1 * _safe_float(row.get("cluster_size"), 0.0)
    )


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
    ap = argparse.ArgumentParser(description="Build survivor->W3 sample direct mapping seed.")
    ap.add_argument("--knowledge-report-json", type=Path, default=DEFAULT_KNOWLEDGE_REPORT_JSON)
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES_JSON)
    ap.add_argument("--w3-result-json", type=Path, default=DEFAULT_W3_RESULT_JSON)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    ap.add_argument("--samples-per-survivor", type=int, default=1)
    args = ap.parse_args()

    knowledge = _read_json(args.knowledge_report_json)
    candidates_doc = _read_json(args.candidates_json)
    w3 = _read_json(args.w3_result_json)
    survivors = _extract_survivors(knowledge, candidates_doc)
    top_n = w3.get("top_n_results") if isinstance(w3.get("top_n_results"), list) else []
    top_n_ranked = sorted(
        [x for x in top_n if isinstance(x, dict) and x.get("sample_id")],
        key=lambda x: _safe_float(x.get("resonance_score"), 0.0),
        reverse=True,
    )
    sample_ids = [str(x.get("sample_id")) for x in top_n_ranked if x.get("sample_id")]
    samples_per_survivor = max(1, int(args.samples_per_survivor))
    survivors_ranked = sorted(
        [s for s in survivors if isinstance(s, dict)],
        key=_survivor_rank_score,
        reverse=True,
    )

    mapping_rows: list[dict[str, Any]] = []
    for i, s in enumerate(survivors_ranked):
        cid = str(s.get("candidate_id") or "")
        if not cid:
            continue
        assigned: list[str] = []
        if sample_ids:
            start = i * samples_per_survivor
            for j in range(samples_per_survivor):
                assigned.append(sample_ids[(start + j) % len(sample_ids)])
        mapping_rows.append(
            {
                "candidate_id": cid,
                "source_node_id": s.get("source_node_id"),
                "assigned_sample_ids": assigned,
                "mapping_method": "rank_aligned_topk_window_v2",
            }
        )

    out = {
        "schema": "global_atom_survivor_w3_direct_mapping_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "w3_result_json": str(args.w3_result_json),
        "mapping_strategy": "rank_aligned_topk_window_v2",
        "samples_per_survivor": samples_per_survivor,
        "rows": mapping_rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output_json}")
    print(f"mapped_survivors={len(mapping_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
