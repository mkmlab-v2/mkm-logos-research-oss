#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "news_benchmark_readiness_latest.json"
OUT_MD = ART / "news_benchmark_readiness_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            pass
    return None


def _check(path: Path) -> dict[str, Any]:
    doc = _read(path)
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "exists": path.exists(),
        "generated_at_utc": (doc or {}).get("generated_at_utc"),
        "doc": doc,
    }


def main() -> int:
    lb = _check(ART / "btrack_compression_leaderboard_latest.json")
    gate_r2 = _check(ART / "btrack_gate_r2_phase_sweep_latest.json")
    stress = _check(ART / "trackb_stress_benchmark_summary_latest.json")
    ops_snapshot = _check(ART / "btrack_rollup_ops_snapshot_latest.json")
    external_comp = _check(ART / "external_bible_crossref_overlap_comparison_latest.json")
    external_health = _check(ART / "external_bible_crossref_health_check_latest.json")
    external_alert = _check(ART / "external_bible_crossref_health_alert_latest.json")
    claim_pack = _check(ART / "news_claim_pack_latest.json")
    claim_sep = _check(ART / "external_baseline_claim_separation_latest.json")
    repro_bundle = _check(ART / "news_third_party_repro_bundle_latest.json")

    lb_best = (lb["doc"] or {}).get("best_overall") or {}
    gate_best = (gate_r2["doc"] or {}).get("best_row") or {}
    stress_doc = stress["doc"] or {}
    external_doc = external_comp["doc"] or {}
    ext_health_doc = external_health["doc"] or {}
    ext_alert_doc = external_alert["doc"] or {}
    claim_pack_doc = claim_pack["doc"] or {}
    claim_sep_doc = claim_sep["doc"] or {}
    repro_doc = repro_bundle["doc"] or {}

    checks = {
        "internal_benchmark_artifacts_ready": bool(lb["exists"] and gate_r2["exists"] and stress["exists"]),
        "integrity_locked_1_0": float(lb_best.get("integrity", 0.0) or 0.0) >= 1.0 and float(gate_best.get("integrity", 0.0) or 0.0) >= 1.0,
        "stress_research_lane_pass": str(stress_doc.get("recommendation", "")) == "PASS_RESEARCH_LANE",
        "ops_watch_ok": bool(((ops_snapshot["doc"] or {}).get("summary") or {}).get("ops_watch_ok", False)),
        "external_baseline_chain_healthy": bool(ext_health_doc.get("all_healthy", False)) and not bool(ext_alert_doc.get("active", True)),
        # News-grade hard blockers:
        "third_party_repro_evidence_present": bool(repro_doc.get("third_party_repro_evidence_present", False)),
        "third_party_repro_placeholder_detected": bool(repro_doc.get("placeholder_detected", False)),
        "third_party_repro_status_valid": str(repro_doc.get("status", "")) in {"EVIDENCE_ATTACHED_AWAITING_REVIEW", "EVIDENCE_VERIFIED"},
        "public_claim_pack_ready": str(claim_pack_doc.get("status", "")) == "APPROVED_FOR_EXTERNAL_DRAFT",
        "external_baseline_narrative_separated": str(claim_sep_doc.get("status", "")) == "ENFORCED_FOR_PUBLIC_COPY",
        "algorithmic_ground_truth_for_external_baseline": bool(external_doc.get("algorithmic_ground_truth", False)),
    }

    blockers: list[str] = []
    if not checks["third_party_repro_evidence_present"]:
        blockers.append("Missing third-party reproducibility evidence bundle.")
    elif checks["third_party_repro_placeholder_detected"] or (not checks["third_party_repro_status_valid"]):
        blockers.append("Third-party reproducibility bundle contains template/invalid status.")
    if not checks["public_claim_pack_ready"]:
        blockers.append("Missing public claim pack with approved wording and confidence intervals.")
    if not checks["external_baseline_narrative_separated"]:
        blockers.append("Missing external baseline narrative separation guard artifact.")
    if not checks["internal_benchmark_artifacts_ready"]:
        blockers.append("Internal benchmark artifacts incomplete.")
    if not checks["integrity_locked_1_0"]:
        blockers.append("Integrity 1.0 lock not consistently confirmed.")

    news_grade_ready = (
        checks["internal_benchmark_artifacts_ready"]
        and checks["integrity_locked_1_0"]
        and checks["stress_research_lane_pass"]
        and checks["ops_watch_ok"]
        and checks["external_baseline_chain_healthy"]
        and checks["third_party_repro_evidence_present"]
        and checks["third_party_repro_status_valid"]
        and (not checks["third_party_repro_placeholder_detected"])
        and checks["public_claim_pack_ready"]
        and checks["external_baseline_narrative_separated"]
    )

    status = "READY_FOR_NEWS_CLAIMS" if news_grade_ready else "NOT_READY_FOR_NEWS_CLAIMS"
    if (
        not news_grade_ready
        and checks["internal_benchmark_artifacts_ready"]
        and checks["integrity_locked_1_0"]
        and checks["stress_research_lane_pass"]
        and checks["ops_watch_ok"]
        and checks["external_baseline_chain_healthy"]
        and checks["public_claim_pack_ready"]
        and checks["external_baseline_narrative_separated"]
        and not checks["third_party_repro_evidence_present"]
    ):
        status = "READY_PENDING_THIRD_PARTY_REPRO"

    payload: dict[str, Any] = {
        "schema": "news_benchmark_readiness_v1",
        "generated_at_utc": _utc_now(),
        "lane": "research_only",
        "summary": {
            "news_grade_ready": news_grade_ready,
            "status": status,
            "blocker_count": len(blockers),
        },
        "observed_metrics": {
            "best_saving_internal": lb_best.get("saving"),
            "best_jaccard_internal": lb_best.get("jaccard"),
            "best_integrity_internal": lb_best.get("integrity"),
            "best_saving_gate_r2": gate_best.get("saving"),
            "best_jaccard_gate_r2": gate_best.get("jaccard"),
            "stress_recommendation": stress_doc.get("recommendation"),
        },
        "checks": checks,
        "blockers": blockers,
        "required_next_actions": [
            "Create third-party reproducibility runbook and external execution evidence.",
            "Produce public claim pack with conservative wording, confidence interval, and failure cases.",
            "Separate external baseline narrative from algorithmic ground-truth claims.",
        ],
        "artifact_refs": {
            "compression_leaderboard": lb["path"],
            "gate_r2_sweep": gate_r2["path"],
            "stress_summary": stress["path"],
            "ops_snapshot": ops_snapshot["path"],
            "external_overlap_comparison": external_comp["path"],
            "external_health_check": external_health["path"],
            "news_claim_pack": claim_pack["path"],
            "external_baseline_claim_separation": claim_sep["path"],
            "third_party_repro_bundle": repro_bundle["path"],
        },
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# News Benchmark Readiness (Latest)",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{payload['summary']['status']}`",
        f"- news_grade_ready: `{payload['summary']['news_grade_ready']}`",
        f"- blocker_count: `{payload['summary']['blocker_count']}`",
        "",
        "## Observed Internal Metrics",
        f"- best_saving_internal: `{payload['observed_metrics']['best_saving_internal']}`",
        f"- best_jaccard_internal: `{payload['observed_metrics']['best_jaccard_internal']}`",
        f"- best_integrity_internal: `{payload['observed_metrics']['best_integrity_internal']}`",
        f"- stress_recommendation: `{payload['observed_metrics']['stress_recommendation']}`",
        "",
        "## Blocking Items",
    ]
    if blockers:
        md.extend([f"- {b}" for b in blockers])
    else:
        md.append("- none")
    md.extend(
        [
            "",
            "## Required Next Actions",
            *[f"- {x}" for x in payload["required_next_actions"]],
            "",
            "## Note",
            "- This readiness report is for commercialization governance; production/news claims require explicit approval gates.",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

