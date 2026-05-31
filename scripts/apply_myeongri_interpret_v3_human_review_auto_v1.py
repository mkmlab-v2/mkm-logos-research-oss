#!/usr/bin/env python3
"""Apply heuristic reviewer_verdict to interpret v3 human review sample (B-track auto triage)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SAMPLE = ROOT / "reports/myeongri_interpret_v3_human_review_sample_latest.json"
DEFAULT_DIVERSITY = ROOT / "reports/myeongri_interpret_narrative_diversity_audit_latest.json"
DEFAULT_PIPELINE = ROOT / "reports/myeongri_interpret_harness_v3_pipeline_status_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _auto_verdict(sample: dict, skeleton_unique: int) -> tuple[str, str]:
    insight = (sample.get("mkm_advanced_insight") or "").strip()
    auto_note = str(sample.get("auto_note") or "")
    if not insight:
        return "fail", "empty_mkm_advanced_insight"
    if auto_note == "template_pattern_likely":
        return "needs_edit", "template_pattern_likely"
    if auto_note == "empty_insight_after_parse":
        return "fail", "empty_insight_after_parse"
    if skeleton_unique > 10:
        if sample.get("parse_ok"):
            if sample.get("envelope_match_normalized"):
                return "pass", "v4_format_and_oracle_match"
            if sample.get("envelope_coerced_from_template"):
                return "pass", "v4_parse_coerced_governance_ok"
        return "fail", "parse_or_envelope_mismatch"
    if auto_note == "check_narrative_diversity" and skeleton_unique <= 1:
        return "needs_edit", "v3_template_skeleton_only_format_ok"
    if auto_note == "narrative_variant_ok" and sample.get("parse_ok"):
        return "pass", "narrative_variant_ok"
    if sample.get("parse_ok") and sample.get("envelope_match_normalized"):
        return "pass", "format_contract_only"
    return "fail", "parse_or_envelope_mismatch"


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _patch_v3_v4_status(
    status_path: Path,
    diversity_path: Path,
    sample_path: Path,
    counts: dict[str, int],
) -> None:
    doc = json.loads(status_path.read_text(encoding="utf-8"))
    div = json.loads(diversity_path.read_text(encoding="utf-8"))
    v4 = doc.setdefault("v4_variant_sft", {})
    v4["locked100_eval"] = v4.get("locked100_eval") or {}
    v4["locked100_eval"]["diversity_audit"] = _rel(diversity_path)
    v4["human_review_sample"] = {
        "report": _rel(sample_path),
        "auto_verdict_applied": True,
        "auto_verdict_counts": counts,
        "auto_verdict_source": "apply_myeongri_interpret_v3_human_review_auto_v1.py",
    }
    v4["narrative_diversity_locked100"] = {
        "unique_insight_rate": div.get("unique_insight_rate"),
        "v3_fixed_prefix_rate": div.get("v3_fixed_prefix_rate"),
        "empty_insight_row_count": div.get("empty_insight_row_count"),
        "narrative_diversity_gate_pass": div.get("narrative_diversity_gate_pass"),
    }
    doc["generated_at_utc"] = _utc_now()
    status_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _patch_pipeline(pipeline_path: Path, diversity_path: Path, sample_path: Path) -> None:
    if not pipeline_path.is_file():
        return
    doc = json.loads(pipeline_path.read_text(encoding="utf-8"))
    div = json.loads(diversity_path.read_text(encoding="utf-8"))
    rel_div = _rel(diversity_path)
    rel_sample = _rel(sample_path)
    audit_block = {
        "report": rel_div,
        "template_skeleton_unique_count": div.get("template_skeleton_unique_count"),
        "narrative_diversity_gate_pass": div.get("narrative_diversity_gate_pass"),
        "v3_fixed_prefix_rate": div.get("v3_fixed_prefix_rate"),
        "empty_insight_row_count": div.get("empty_insight_row_count"),
    }
    review_block = {
        "report": rel_sample,
        "auto_verdict_applied": True,
        "auto_verdict_source": "apply_myeongri_interpret_v3_human_review_auto_v1.py",
    }
    if "v4" in rel_sample or "interpret_v4" in rel_sample:
        lora = doc.setdefault("interpret_lora_v4", {})
    else:
        lora = doc.setdefault("interpret_lora_v3", {})
    lora["narrative_diversity_audit"] = audit_block
    lora["human_review_sample"] = review_block
    doc["generated_at_utc"] = _utc_now()
    pipeline_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--diversity-json", type=Path, default=DEFAULT_DIVERSITY)
    ap.add_argument("--pipeline-json", type=Path, default=DEFAULT_PIPELINE)
    ap.add_argument("--skip-pipeline-patch", action="store_true")
    ap.add_argument(
        "--status-json",
        type=Path,
        default=None,
        help="Optional v3/v4 status JSON to patch human_review + diversity pointers.",
    )
    args = ap.parse_args()

    if not args.sample_json.is_file():
        print(f"missing sample: {args.sample_json}", file=sys.stderr)
        return 2
    if not args.diversity_json.is_file():
        print(f"missing diversity audit: {args.diversity_json}", file=sys.stderr)
        return 2

    sample_doc = json.loads(args.sample_json.read_text(encoding="utf-8"))
    div_doc = json.loads(args.diversity_json.read_text(encoding="utf-8"))
    skeleton_unique = int(div_doc.get("template_skeleton_unique_count") or 0)

    counts = {"pass": 0, "fail": 0, "needs_edit": 0}
    for row in sample_doc.get("samples") or []:
        verdict, reason = _auto_verdict(row, skeleton_unique)
        row["reviewer_verdict"] = verdict
        row["reviewer_verdict_source"] = "auto_v1"
        row["reviewer_verdict_reason"] = reason
        counts[verdict] = counts.get(verdict, 0) + 1

    sample_doc["auto_verdict_applied_at_utc"] = _utc_now()
    sample_doc["auto_verdict_source"] = "apply_myeongri_interpret_v3_human_review_auto_v1.py"
    sample_doc["auto_verdict_counts"] = counts
    sample_doc["diversity_audit_pointer"] = _rel(args.diversity_json)

    args.sample_json.write_text(
        json.dumps(sample_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not args.skip_pipeline_patch:
        _patch_pipeline(args.pipeline_json, args.diversity_json, args.sample_json)
    if args.status_json and args.status_json.is_file():
        _patch_v3_v4_status(args.status_json, args.diversity_json, args.sample_json, counts)

    print(json.dumps({"ok": True, "counts": counts, "sample": str(args.sample_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
