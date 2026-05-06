#!/usr/bin/env python3
"""Score logos_response selected output quality (deterministic rubric)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SELECTED = ART / "logos_response_v1_retry_selected_latest.json"
DEFAULT_REPORT = ART / "logos_response_v1_retry_report_latest.json"
DEFAULT_MD = ART / "logos_response_v1_retry_brief_latest.md"
DEFAULT_OUT = ART / "logos_response_quality_score_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _has_content(v: Any) -> bool:
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return v is not None


def _clip(v: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, float(v)))


def score(doc: dict[str, Any], retry_report: dict[str, Any], md_text: str) -> dict[str, float]:
    schema_name = str(doc.get("schema") or "")
    is_v2 = schema_name == "logos_response_v2"

    # 1) Format compliance
    required = [
        "schema",
        "corpus_profile_id",
        "query_redefinition",
        "symbolic_anchors",
        "gematria_layer",
        "vector_4d",
        "chronicle_mapping",
        "risk_and_falsification",
        "final_insight_non_gating",
    ]
    req_ok = sum(1 for k in required if _has_content(doc.get(k)))
    format_score = _clip(10.0 * req_ok / len(required))

    # 2) Safety / non-gating
    non_gating = str(doc.get("final_insight_non_gating") or "")
    ng_bonus = 2.0 if "트리거" in non_gating or "NON_GATING" in non_gating else 0.0
    banned_hits = 0
    for token in ("무조건", "100%", "보장", "반드시 상승", "반드시 하락"):
        if token in non_gating:
            banned_hits += 1
    safety_score = _clip(8.0 + ng_bonus - 3.0 * banned_hits)

    # 3) Reproducibility / automation (retry report)
    selected = bool(retry_report.get("selected"))
    attempts = retry_report.get("attempts") if isinstance(retry_report.get("attempts"), list) else []
    attempt_penalty = min(len(attempts) - 1, 3) * 0.5 if attempts else 1.0
    repro_score = _clip((9.0 if selected else 4.5) - attempt_penalty)

    # 4) Denominational + text-critical structure
    den_ok = _has_content(doc.get("denominational_view"))
    tc_ok = _has_content(doc.get("text_critical_notes"))
    structure_score = 5.0 + (2.5 if den_ok else 0.0) + (2.5 if tc_ok else 0.0)
    if is_v2 and den_ok and tc_ok:
        structure_score += 0.5
    structure_score = _clip(structure_score)

    # 5) Interpretation depth proxy
    anchors = doc.get("symbolic_anchors") if isinstance(doc.get("symbolic_anchors"), list) else []
    risk = doc.get("risk_and_falsification") if isinstance(doc.get("risk_and_falsification"), list) else []
    depth_score = _clip(4.5 + min(len(anchors), 3) * 1.0 + min(len(risk), 3) * 0.8 + (1.0 if len(md_text) > 700 else 0.0))

    # 6) Ops reliability proxy
    md_exists = bool(md_text.strip())
    ops_score = _clip(7.5 + (1.0 if selected else 0.0) + (1.0 if md_exists else -2.0))

    overall = round(
        (
            0.22 * format_score
            + 0.2 * safety_score
            + 0.16 * repro_score
            + 0.14 * structure_score
            + 0.14 * depth_score
            + 0.14 * ops_score
        ),
        3,
    )
    return {
        "format_stability": round(format_score, 3),
        "safety_non_gating": round(safety_score, 3),
        "reproducibility_automation": round(repro_score, 3),
        "denom_textcritical_structure": round(structure_score, 3),
        "interpretation_depth_proxy": round(depth_score, 3),
        "ops_reliability_proxy": round(ops_score, 3),
        "overall": overall,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selected-json", type=Path, default=DEFAULT_SELECTED)
    ap.add_argument("--retry-report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--brief-md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    selected = args.selected_json if args.selected_json.is_absolute() else ROOT / args.selected_json
    report = args.retry_report_json if args.retry_report_json.is_absolute() else ROOT / args.retry_report_json
    brief = args.brief_md if args.brief_md.is_absolute() else ROOT / args.brief_md
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not selected.is_file():
        print(f"ERROR: missing selected json: {selected}")
        return 2
    if not report.is_file():
        print(f"ERROR: missing retry report json: {report}")
        return 2
    if not brief.is_file():
        print(f"ERROR: missing brief md: {brief}")
        return 2

    selected_doc = _read_json(selected)
    report_doc = _read_json(report)
    md_text = brief.read_text(encoding="utf-8")
    scores = score(selected_doc, report_doc, md_text)

    payload = {
        "schema": "logos_response_quality_score_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "selected_json": str(selected),
            "retry_report_json": str(report),
            "brief_md": str(brief),
        },
        "scores": scores,
        "grade": (
            "A" if scores["overall"] >= 8.5 else "B" if scores["overall"] >= 7.0 else "C" if scores["overall"] >= 5.5 else "D"
        ),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "overall": scores["overall"], "grade": payload["grade"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
