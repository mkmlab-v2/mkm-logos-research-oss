#!/usr/bin/env python3
"""Legal handoff pack for RQ-019 external copy (INTERNAL — not legal sign-off)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_legal_handoff_pack_latest.json"
PATHS = {
    "status": ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
    "approval": ROOT / "docs/final/artifacts/mkm_inter_agent_health_domain_commander_approval_v1_latest.json",
    "post_approval": ROOT / "docs/final/artifacts/mkm_inter_agent_post_commander_approval_bundle_latest.json",
    "ir_snippet": ROOT / "docs/final/artifacts/mkm_inter_agent_ir_snippet_v1.md",
    "sota_map": ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_sota_map_v1.md",
    "public_facing": ROOT / "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
    "live_http": ROOT / "docs/final/artifacts/mkm_inter_agent_first_message_live_http_v1.json",
    "l1_spike": ROOT / "docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json",
    "submission": ROOT / "docs/final/artifacts/mkm_inter_agent_commander_legal_submission_v1_latest.json",
    "manifest": ROOT / "docs/final/artifacts/mkm_inter_agent_counsel_export_manifest_v1_latest.json",
    "counsel_signoff": ROOT / "docs/final/artifacts/mkm_inter_agent_legal_counsel_signoff_v1_latest.json",
    "closure_readiness": ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_closure_readiness_latest.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def _checklist() -> list[dict[str, Any]]:
    status = _load(PATHS["status"])
    approval = _load(PATHS["approval"])
    post = _load(PATHS["post_approval"])
    milestones = (status or {}).get("milestones") or {}

    def row(n: int, item: str, met: bool, evidence: str) -> dict[str, Any]:
        return {"id": n, "item": item, "met": met, "evidence": evidence}

    return [
        row(
            1,
            "M1 v2 packet-only expand + pytest",
            milestones.get("m1_v2_phase2_packet_only_expand", {}).get("status") == "pass",
            "mkm_inter_agent_encoding_status_latest.json · test_compression_token_api_v2_stub.py",
        ),
        row(
            2,
            "M2 wire profile v0",
            milestones.get("m2_wire_profile_v0", {}).get("status") == "pass",
            "mkm_inter_agent_wire_profile_v0.json",
        ),
        row(
            3,
            "M3 L1 spike documented (research_only)",
            milestones.get("m3_human_decoder_public_copy", {}).get("pass") is True,
            "l1_inverse_decoder_spike_test_summary_latest.json",
        ),
        row(
            4,
            "Commander ops: B-track health routing (not Track A bench)",
            bool(approval and approval.get("commander_approved"))
            and approval.get("track_a_bench_promotion_approved") is False,
            "mkm_inter_agent_health_domain_commander_approval_v1_latest.json",
        ),
        row(
            5,
            "Ops bundle: health A2A dialogue ready",
            bool(post and (post.get("ops_ready") or {}).get("b_track_health_dialogue")),
            "mkm_inter_agent_post_commander_approval_bundle_latest.json",
        ),
        row(
            6,
            "Live HTTP evidence on disk",
            PATHS["live_http"].is_file(),
            PATHS["live_http"].relative_to(ROOT).as_posix(),
        ),
        row(
            7,
            "Legal sign-off on external copy",
            False,
            "PENDING — counsel review of ir_snippet + PUBLIC_FACING v1.7",
        ),
    ]


def _legal_status() -> tuple[str, bool]:
    signoff = _load(PATHS["counsel_signoff"])
    if signoff and signoff.get("counsel_signoff"):
        return str(signoff.get("legal_review_status") or "COUNSEL_SIGNED"), True
    submission = _load(PATHS["submission"])
    if submission and submission.get("commander_authorized_legal_submission"):
        return str(submission.get("legal_review_status") or "SUBMITTED_TO_COUNSEL"), False
    return "PENDING", False


def build() -> dict[str, Any]:
    checklist = _checklist()
    legal_status, item7_met = _legal_status()
    if item7_met:
        for row in checklist:
            if row.get("id") == 7:
                row["met"] = True
                row["evidence"] = PATHS["counsel_signoff"].relative_to(ROOT).as_posix()
    tech_ready = all(c["met"] for c in checklist if c["id"] != 7)
    status = _load(PATHS["status"]) or {}
    doc_paths = [p for p in PATHS.values() if p.is_file()]
    manifest = _load(PATHS["manifest"])
    if manifest:
        for f in manifest.get("files") or []:
            rel = f.get("path") if isinstance(f, dict) else None
            if rel and (ROOT / str(rel)).is_file():
                doc_paths.append(ROOT / str(rel))
    seen: set[str] = set()
    documents_for_counsel: list[str] = []
    for p in sorted(doc_paths, key=lambda x: x.as_posix()):
        rel = p.relative_to(ROOT).as_posix()
        if rel not in seen:
            seen.add(rel)
            documents_for_counsel.append(rel)

    return {
        "schema": "mkm_inter_agent_legal_handoff_pack_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "hypothesis_tier": "B",
        "rq_019_status": "OPEN" if not item7_met else "READY_FOR_COMMANDER_CLOSE",
        "legal_review_status": legal_status,
        "commander_ops_approved": True,
        "commander_legal_submission": (_load(PATHS["submission"]) or {}).get(
            "commander_authorized_legal_submission"
        ),
        "technical_closure_ready": tech_ready,
        "rq_019_milestones_core_ready": status.get("rq_019_milestones_core_ready"),
        "checklist": checklist,
        "documents_for_counsel": documents_for_counsel,
        "counsel_export_manifest": (
            PATHS["manifest"].relative_to(ROOT).as_posix() if PATHS["manifest"].is_file() else None
        ),
        "closure_readiness_pointer": (
            PATHS["closure_readiness"].relative_to(ROOT).as_posix()
            if PATHS["closure_readiness"].is_file()
            else None
        ),
        "forbidden_external_claims": [
            "MKM Language shipped / lingua franca complete",
            "Token cost zero / 100% lossless decode",
            "TCP/IP or industry standard adoption",
            "Beats SOTA papers / production SLA",
            "Track A ~47% bench replaced by health-hangul variant",
        ],
        "approved_external_copy_draft": {
            "ko": (
                "MKM은 측정 가능한 에이전트 간 메시지 레일 초안을 구축 중이며, "
                "v2 Trust Packet(초안)으로 compress/expand 왕복을 재현했습니다. "
                "상용 SLA·무손실 통역·업계 표준 채택은 주장하지 않습니다."
            ),
            "en": (
                "MKM is building a draft measurable agent-to-agent message rail with "
                "reproducible Trust Packet compress/expand roundtrips. "
                "We do not claim production SLA, lossless translation, or industry-standard adoption."
            ),
            "source": "mkm_inter_agent_ir_snippet_v1.md",
            "requires_legal_edit": True,
        },
        "boundary_ack": (
            "This JSON is an internal legal handoff index, not counsel approval. "
            "RQ-019 CLOSED only after item 7 is met and promotion path is agreed."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out_json),
                "technical_closure_ready": doc["technical_closure_ready"],
                "legal_review_status": doc["legal_review_status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
