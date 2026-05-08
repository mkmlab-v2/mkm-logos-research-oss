#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_LOGOS_RESPONSE = ART / "mkm_logos_response_v2_latest.json"
DEFAULT_DRIFT = ART / "logos_semantic_drift_monitor_latest.json"
DEFAULT_QUERY_SMOKE = ART / "logos_vector_ann_lite_query_smoke_latest.json"
DEFAULT_QUERY_SUITE = ART / "logos_semantic_query_smoke_suite_latest.json"
DEFAULT_WEEKLY_GATE = ART / "logos_shadow_weekly_gate_latest.json"
DEFAULT_DEEP_FUSION_DISTILL = ART / "logos_deep_research_distill_track_b_chain_v1_latest.json"
DEFAULT_DEEP_FUSION_JOB = ART / "logos_track_b_deep_fusion_job_v1_latest.json"
DEFAULT_OUT_JSON = ART / "logos_shadow_insight_latest.json"
DEFAULT_OUT_MD = ART / "logos_shadow_insight_latest.md"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build [SHADOW_INSIGHT] report for MacroDailyFusion.")
    ap.add_argument("--logos-response-json", type=Path, default=DEFAULT_LOGOS_RESPONSE)
    ap.add_argument("--drift-json", type=Path, default=DEFAULT_DRIFT)
    ap.add_argument("--query-smoke-json", type=Path, default=DEFAULT_QUERY_SMOKE)
    ap.add_argument("--query-suite-json", type=Path, default=DEFAULT_QUERY_SUITE)
    ap.add_argument("--weekly-gate-json", type=Path, default=DEFAULT_WEEKLY_GATE)
    ap.add_argument("--deep-fusion-distill-json", type=Path, default=DEFAULT_DEEP_FUSION_DISTILL)
    ap.add_argument("--deep-fusion-job-json", type=Path, default=DEFAULT_DEEP_FUSION_JOB)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    response_path = args.logos_response_json if args.logos_response_json.is_absolute() else ROOT / args.logos_response_json
    drift_path = args.drift_json if args.drift_json.is_absolute() else ROOT / args.drift_json
    query_path = args.query_smoke_json if args.query_smoke_json.is_absolute() else ROOT / args.query_smoke_json
    query_suite_path = args.query_suite_json if args.query_suite_json.is_absolute() else ROOT / args.query_suite_json
    weekly_gate_path = args.weekly_gate_json if args.weekly_gate_json.is_absolute() else ROOT / args.weekly_gate_json
    deep_fusion_distill_path = args.deep_fusion_distill_json if args.deep_fusion_distill_json.is_absolute() else ROOT / args.deep_fusion_distill_json
    deep_fusion_job_path = args.deep_fusion_job_json if args.deep_fusion_job_json.is_absolute() else ROOT / args.deep_fusion_job_json

    if not response_path.is_file():
        raise SystemExit(f"Missing logos response json: {response_path}")
    if not drift_path.is_file():
        raise SystemExit(f"Missing drift json: {drift_path}")
    if not query_path.is_file():
        raise SystemExit(f"Missing query smoke json: {query_path}")
    if not query_suite_path.is_file():
        raise SystemExit(f"Missing query suite json: {query_suite_path}")

    response = _read_json(response_path)
    drift = _read_json(drift_path)
    query = _read_json(query_path)
    query_suite = _read_json(query_suite_path)
    weekly_gate = _read_json(weekly_gate_path) if weekly_gate_path.is_file() else {}
    deep_fusion_distill = _read_json(deep_fusion_distill_path) if deep_fusion_distill_path.is_file() else {}
    deep_fusion_job = _read_json(deep_fusion_job_path) if deep_fusion_job_path.is_file() else {}

    final_action = response.get("final_action") if isinstance(response.get("final_action"), dict) else {}
    coordinator = response.get("coordinator_layer") if isinstance(response.get("coordinator_layer"), dict) else {}
    top_k = query.get("top_k") if isinstance(query.get("top_k"), list) else []
    top1 = top_k[0] if top_k and isinstance(top_k[0], dict) else {}
    suite_summary = query_suite.get("summary") if isinstance(query_suite.get("summary"), dict) else {}
    distill_review = deep_fusion_distill.get("review_gate") if isinstance(deep_fusion_distill.get("review_gate"), dict) else {}
    distill_veto = deep_fusion_distill.get("veto_flags") if isinstance(deep_fusion_distill.get("veto_flags"), dict) else {}
    deep_fusion_exec = deep_fusion_job.get("execution") if isinstance(deep_fusion_job.get("execution"), dict) else {}
    deep_fusion_ready = deep_fusion_job.get("readiness") if isinstance(deep_fusion_job.get("readiness"), dict) else {}
    deep_fusion_line_1 = (
        f"review_gate={distill_review.get('status')} "
        f"(reason={distill_review.get('reason_code')}); "
        f"epistemic_uncertainty={deep_fusion_distill.get('epistemic_uncertainty')}"
    )
    deep_fusion_line_2 = (
        f"readiness_ok={deep_fusion_ready.get('overall_ok')} "
        f"execution_status={deep_fusion_exec.get('status')}; "
        f"veto_insufficient_evidence={distill_veto.get('insufficient_evidence')}"
    )

    insight = {
        "schema": "logos_shadow_insight_v1",
        "generated_at_utc": _now(),
        "banner": "[SHADOW_INSIGHT]",
        "shadow_grade": "S1_SHADOW",
        "summary": {
            "decision": final_action.get("decision"),
            "reason": final_action.get("reason"),
            "low_confidence": ((drift.get("guard") or {}).get("low_confidence") is True),
            "top_match_verse_id": top1.get("verse_id"),
            "top_match_cosine": top1.get("score"),
            "mean_top1_cosine": suite_summary.get("mean_top1_cosine"),
            "queries_ok": suite_summary.get("queries_ok"),
            "queries_error": suite_summary.get("queries_error"),
            "weekly_gate_decision": weekly_gate.get("decision"),
            "deep_fusion_evidence_line_1": deep_fusion_line_1,
            "deep_fusion_evidence_line_2": deep_fusion_line_2,
        },
        "core_observation": {
            "signal_core": ((response.get("core_layer") or {}).get("signal_core")),
            "confidence_adjusted": coordinator.get("confidence_adjusted"),
            "failed_check_keys": (response.get("response_layer") or {}).get("failed_check_keys"),
        },
        "guardrail": {
            "policy": "SHADOW_ONLY_NON_GATING",
            "auto_trade_enable": False,
            "requires_human_signoff": True,
        },
        "evidence_paths": {
            "logos_response_json": str(response_path.resolve()),
            "semantic_drift_json": str(drift_path.resolve()),
            "query_smoke_json": str(query_path.resolve()),
            "query_suite_json": str(query_suite_path.resolve()),
            "weekly_gate_json": str(weekly_gate_path.resolve()) if weekly_gate_path.is_file() else None,
            "deep_fusion_distill_json": str(deep_fusion_distill_path.resolve()) if deep_fusion_distill_path.is_file() else None,
            "deep_fusion_job_json": str(deep_fusion_job_path.resolve()) if deep_fusion_job_path.is_file() else None,
        },
    }

    out_json = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_md = args.output_md if args.output_md.is_absolute() else ROOT / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(insight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "## [SHADOW_INSIGHT]",
        f"- `shadow_grade`: `{insight['shadow_grade']}`",
        f"- `decision`: `{insight['summary']['decision']}`",
        f"- `reason`: `{insight['summary']['reason']}`",
        f"- `low_confidence`: `{insight['summary']['low_confidence']}`",
        f"- `top_match_verse_id`: `{insight['summary']['top_match_verse_id']}`",
        f"- `top_match_cosine`: `{insight['summary']['top_match_cosine']}`",
        f"- `mean_top1_cosine`: `{insight['summary']['mean_top1_cosine']}`",
        f"- `queries_ok`: `{insight['summary']['queries_ok']}`",
        f"- `queries_error`: `{insight['summary']['queries_error']}`",
        f"- `weekly_gate_decision`: `{insight['summary']['weekly_gate_decision']}`",
        f"- `deep_fusion_evidence_1`: `{insight['summary']['deep_fusion_evidence_line_1']}`",
        f"- `deep_fusion_evidence_2`: `{insight['summary']['deep_fusion_evidence_line_2']}`",
        "- `policy`: `SHADOW_ONLY_NON_GATING`",
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

