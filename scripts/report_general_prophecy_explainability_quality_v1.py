# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.83, L:0.9, K:0.47, M:0.62}
# Balance: 91
# Purpose: Evaluate quality metrics for explainable general prophecy artifact.
# Keywords: explainability, quality, coverage, conflict, reproducibility, metrics
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_explainable_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_explainability_quality_v1_latest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Report explainability quality metrics for general prophecy.")
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    in_path = args.input if args.input.is_absolute() else ROOT / args.input
    if not in_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing_input:{in_path}"}, ensure_ascii=False))
        return 2

    doc = load_json(in_path)
    rows = doc.get("questions") or []
    n = len(rows) if isinstance(rows, list) else 0
    if n == 0:
        out_doc = {
            "schema": "general_prophecy_explainability_quality_v1",
            "generated_at_utc": utc_now(),
            "source_artifact": str(in_path),
            "summary": {"n_questions": 0},
        }
        out_path = args.output if args.output.is_absolute() else ROOT / args.output
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "out": str(out_path), "n_questions": 0}, ensure_ascii=False))
        return 0

    coverage_hits = 0
    conflict_hits = 0
    reproducible_hits = 0
    biblical_cov_sum = 0.0
    evidence_len_sum = 0
    per_question: list[dict[str, Any]] = []

    for q in rows:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("question_id", "unknown"))
        expl = q.get("explanation") if isinstance(q.get("explanation"), dict) else {}
        bib = expl.get("biblical") if isinstance(expl.get("biblical"), dict) else {}
        top = expl.get("top_evidence") if isinstance(expl.get("top_evidence"), list) else []
        conflict = str(expl.get("conflict_resolution", "")).strip()
        has_coverage = len(top) >= 3 and bool(expl.get("why_summary"))
        has_conflict = len(conflict) >= 12
        has_repro = bool(bib.get("gematria")) and bool(bib.get("verse_matches"))
        b_cov = float(bib.get("keyword_coverage", 0.0) or 0.0)

        coverage_hits += 1 if has_coverage else 0
        conflict_hits += 1 if has_conflict else 0
        reproducible_hits += 1 if has_repro else 0
        biblical_cov_sum += b_cov
        evidence_len_sum += len(top)

        per_question.append(
            {
                "question_id": qid,
                "coverage_ok": has_coverage,
                "conflict_resolution_ok": has_conflict,
                "reproducible_evidence_ok": has_repro,
                "biblical_keyword_coverage": round(b_cov, 6),
                "top_evidence_count": len(top),
            }
        )

    out_doc = {
        "schema": "general_prophecy_explainability_quality_v1",
        "generated_at_utc": utc_now(),
        "source_artifact": str(in_path),
        "summary": {
            "n_questions": n,
            "coverage_rate": round(coverage_hits / n, 6),
            "conflict_resolution_rate": round(conflict_hits / n, 6),
            "reproducible_evidence_rate": round(reproducible_hits / n, 6),
            "avg_biblical_keyword_coverage": round(biblical_cov_sum / n, 6),
            "avg_top_evidence_count": round(evidence_len_sum / n, 6),
        },
        "rows": per_question,
    }

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "n_questions": n}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
