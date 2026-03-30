#!/usr/bin/env python3
"""Evaluate multi-lens performance dimensions from a fixed input spec."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V1.json"


def _tokens(text: str) -> int:
    # Simple portable token proxy (word-ish and symbol chunks).
    return len(re.findall(r"[A-Za-z0-9_]+|[가-힣]+|[^\s]", text))


def _norm_words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z0-9_가-힣]+", text)}


def _jaccard(a: str, b: str) -> float:
    sa = _norm_words(a)
    sb = _norm_words(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _axis_hit(answer: str, axis: str) -> bool:
    a = answer.lower()
    axis_map = {
        "myeongri": ["명리", "state", "state_id", "myeongri"],
        "bible": ["성경", "시편", "logos", "bible"],
        "sasang": ["사상의학", "체질", "sasang"],
    }
    return any(k in a for k in axis_map.get(axis, [axis]))


def main() -> int:
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    comp_cases = doc.get("compression_cases", [])
    fus_cases = doc.get("fusion_answer_cases", [])

    comp_rows = []
    total_raw = total_comp = 0
    total_fidelity = 0.0
    for c in comp_cases:
        raw = str(c.get("raw_text", ""))
        comp = str(c.get("compressed_text", ""))
        rec = str(c.get("reconstructed_text", ""))
        raw_t = _tokens(raw)
        comp_t = _tokens(comp)
        ratio = (comp_t / raw_t) if raw_t else 1.0
        saving = 1.0 - ratio
        fidelity = _jaccard(raw, rec)
        comp_rows.append(
            {
                "id": c.get("id"),
                "raw_tokens": raw_t,
                "compressed_tokens": comp_t,
                "token_saving_rate": saving,
                "compression_ratio": ratio,
                "reconstruction_fidelity_jaccard": fidelity,
            }
        )
        total_raw += raw_t
        total_comp += comp_t
        total_fidelity += fidelity

    fus_rows = []
    axis_sum = pers_sum = 0.0
    for c in fus_cases:
        ans = str(c.get("answer", ""))
        req_axes = [str(x) for x in c.get("required_axes", [])]
        pers_signals = [str(x).lower() for x in c.get("personalization_signals", [])]
        axis_hits = sum(1 for ax in req_axes if _axis_hit(ans, ax))
        axis_cov = (axis_hits / len(req_axes)) if req_axes else 1.0
        ans_l = ans.lower()
        pers_hits = sum(1 for s in pers_signals if s in ans_l)
        pers_cov = (pers_hits / len(pers_signals)) if pers_signals else 1.0
        fus_rows.append(
            {
                "id": c.get("id"),
                "axis_coverage": axis_cov,
                "personalization_coverage": pers_cov,
                "fusion_answer_possible": axis_cov >= 1.0,
            }
        )
        axis_sum += axis_cov
        pers_sum += pers_cov

    avg_fidelity = (total_fidelity / len(comp_rows)) if comp_rows else 0.0
    avg_axis = (axis_sum / len(fus_rows)) if fus_rows else 0.0
    avg_pers = (pers_sum / len(fus_rows)) if fus_rows else 0.0
    global_saving = (1.0 - (total_comp / total_raw)) if total_raw else 0.0

    report = {
        "schema": "multilens_performance_eval_report_v1",
        "source_input": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "compression_metrics": {
            "case_count": len(comp_rows),
            "global_token_saving_rate": global_saving,
            "avg_reconstruction_fidelity_jaccard": avg_fidelity,
            "cases": comp_rows,
        },
        "fusion_metrics": {
            "case_count": len(fus_rows),
            "avg_axis_coverage": avg_axis,
            "avg_personalization_coverage": avg_pers,
            "all_cases_fusion_possible": all(r["fusion_answer_possible"] for r in fus_rows),
            "cases": fus_rows,
        },
        "quality_gate": {
            "compression_ok": global_saving >= 0.15 and avg_fidelity >= 0.5,
            "fusion_ok": avg_axis >= 0.8 and avg_pers >= 0.5,
            "note": "Heuristic B-track gate; not an A-track trading performance metric.",
        },
    }

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
