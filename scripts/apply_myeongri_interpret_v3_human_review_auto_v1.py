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
    if auto_note == "check_narrative_diversity" and skeleton_unique <= 1:
        return "needs_edit", "v3_template_skeleton_only_format_ok"
    if sample.get("parse_ok") and sample.get("envelope_match_normalized"):
        return "pass", "format_contract_only"
    return "fail", "parse_or_envelope_mismatch"


def _patch_pipeline(pipeline_path: Path, diversity_path: Path, sample_path: Path) -> None:
    if not pipeline_path.is_file():
        return
    doc = json.loads(pipeline_path.read_text(encoding="utf-8"))
    div = json.loads(diversity_path.read_text(encoding="utf-8"))
    lora = doc.setdefault("interpret_lora_v3", {})
    lora["narrative_diversity_audit"] = {
        "report": str(diversity_path.relative_to(ROOT)).replace("\\", "/"),
        "template_skeleton_unique_count": div.get("template_skeleton_unique_count"),
        "narrative_diversity_gate_pass": div.get("narrative_diversity_gate_pass"),
    }
    lora["human_review_sample"] = {
        "report": str(sample_path.relative_to(ROOT)).replace("\\", "/"),
        "auto_verdict_applied": True,
        "auto_verdict_source": "apply_myeongri_interpret_v3_human_review_auto_v1.py",
    }
    doc["generated_at_utc"] = _utc_now()
    pipeline_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--diversity-json", type=Path, default=DEFAULT_DIVERSITY)
    ap.add_argument("--pipeline-json", type=Path, default=DEFAULT_PIPELINE)
    ap.add_argument("--skip-pipeline-patch", action="store_true")
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
    sample_doc["diversity_audit_pointer"] = str(
        args.diversity_json.relative_to(ROOT)
    ).replace("\\", "/")

    args.sample_json.write_text(
        json.dumps(sample_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not args.skip_pipeline_patch:
        _patch_pipeline(args.pipeline_json, args.diversity_json, args.sample_json)

    print(json.dumps({"ok": True, "counts": counts, "sample": str(args.sample_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
