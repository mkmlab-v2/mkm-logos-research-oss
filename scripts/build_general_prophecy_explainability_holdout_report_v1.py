#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_explainability_quality_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_explainability_holdout_report_v1_latest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _cohort_for_question(question_id: str) -> str:
    if question_id.startswith("gp_2026_"):
        return "macro_h2_2026"
    if question_id.startswith("seed."):
        return "external_seed"
    if question_id.startswith("ci.brier_"):
        return "brier_sanity"
    if question_id.startswith("demo."):
        return "demo_control"
    return "other"


def _rates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {
            "n_questions": 0,
            "direct_match_rate": None,
            "fallback_match_rate": None,
            "reproducible_evidence_rate": None,
            "avg_biblical_keyword_coverage": None,
        }
    direct = sum(1 for r in rows if str(r.get("evidence_match_type")) == "direct")
    fallback = sum(1 for r in rows if str(r.get("evidence_match_type")) == "fallback")
    repro = sum(1 for r in rows if bool(r.get("reproducible_evidence_ok")))
    cov = sum(float(r.get("biblical_keyword_coverage", 0.0) or 0.0) for r in rows)
    return {
        "n_questions": n,
        "direct_match_rate": round(direct / n, 6),
        "fallback_match_rate": round(fallback / n, 6),
        "reproducible_evidence_rate": round(repro / n, 6),
        "avg_biblical_keyword_coverage": round(cov / n, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build holdout-focused explainability quality report.")
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    in_path = args.input if args.input.is_absolute() else ROOT / args.input
    if not in_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing_input:{in_path}"}, ensure_ascii=False))
        return 2

    doc = load_json(in_path)
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    normalized: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        qid = str(r.get("question_id", ""))
        # Backward-compat: quality rows historically did not emit evidence_match_type.
        # In that case we treat coverage_ok=True as a direct match proxy.
        raw_match_type = str(r.get("evidence_match_type", "")).strip().lower()
        coverage_ok = bool(r.get("coverage_ok"))
        if raw_match_type in {"direct", "fallback"}:
            match_type = raw_match_type
        elif coverage_ok:
            match_type = "direct"
        else:
            match_type = "none"
        normalized.append(
            {
                "question_id": qid,
                "cohort": _cohort_for_question(qid),
                "evidence_match_type": match_type,
                "reproducible_evidence_ok": bool(r.get("reproducible_evidence_ok")),
                "biblical_keyword_coverage": float(r.get("biblical_keyword_coverage", 0.0) or 0.0),
            }
        )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in normalized:
        grouped.setdefault(r["cohort"], []).append(r)

    cohorts = {
        name: _rates(subrows)
        for name, subrows in sorted(grouped.items(), key=lambda kv: kv[0])
    }
    overall = _rates(normalized)
    holdout_rows = [r for r in normalized if r["cohort"] != "demo_control"]
    holdout = _rates(holdout_rows)

    out = {
        "schema": "general_prophecy_explainability_holdout_report_v1",
        "generated_at_utc": utc_now(),
        "source_quality_artifact": str(in_path),
        "overall": overall,
        "holdout_core": holdout,
        "cohorts": cohorts,
        "notes": [
            "holdout_core excludes demo_control questions",
            "used for drift/overfit monitoring; B-track research-only",
        ],
    }

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "n_rows": len(normalized)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
