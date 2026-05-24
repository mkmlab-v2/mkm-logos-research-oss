#!/usr/bin/env python3
"""Aggregate Logos single-anchor 4D gematria promotion blockers for B2B / audit defense.

Records what we intentionally do NOT claim or auto-promote (Fact-Lock). Does not enable
Track A, external send, or live trading.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--go-no-go-json",
        type=Path,
        default=ART / "logos_single_anchor_go_no_go_v1_latest.json",
    )
    ap.add_argument(
        "--shadow-status-json",
        type=Path,
        default=ART / "logos_shadow_promotion_status_latest.json",
    )
    ap.add_argument(
        "--b2b-readiness-json",
        type=Path,
        default=REPORTS / "track_c_b2b_meeting_pack_readiness_v1_latest.json",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=ART / "logos_single_anchor_promotion_blockers_v1_latest.json",
    )
    args = ap.parse_args()

    go_path = args.go_no_go_json if args.go_no_go_json.is_absolute() else ROOT / args.go_no_go_json
    go = _load(go_path)

    shadow_path = (
        args.shadow_status_json if args.shadow_status_json.is_absolute() else ROOT / args.shadow_status_json
    )
    shadow = _load(shadow_path)

    b2b_path = args.b2b_readiness_json if args.b2b_readiness_json.is_absolute() else ROOT / args.b2b_readiness_json
    b2b = _load(b2b_path)

    nt_gap_path = REPORTS / "logos_nt_lexical_gap_manifest_v1_latest.json"
    nt_gap = _load(nt_gap_path)

    ops = go.get("single_anchor_operational") or {}
    lexical = go.get("lexical_decode_blocker") or {}
    track_wall_shadow = shadow.get("track_wall") or {}

    blockers: list[dict[str, Any]] = [
        {
            "id": "external_send_blocked_legal",
            "tier": "commercial",
            "severity": "high",
            "reason_ko": "법무 Sign-off 전 대외 발송 금지",
            "observed": {
                "ready_for_external_send": bool(go.get("ready_for_external_send", False)),
                "b2b_ready_for_external_send": bool(b2b.get("ready_for_external_send", False)),
            },
            "required_for_lift": "legal_sign_off + PUBLIC_FACING v1.7 review",
        },
        {
            "id": "track_a_auto_promotion_forbidden",
            "tier": "track_wall",
            "severity": "high",
            "reason_ko": "B-track Logos 단일 앵커는 Track A·실매매 자동 승격 금지",
            "observed": {
                "track_a_auto_promotion": bool(go.get("track_a_auto_promotion", False)),
                "promotion_to_a_track_allowed": bool(track_wall_shadow.get("promotion_to_a_track_allowed", False)),
                "live_trigger_auto_enabled": bool(track_wall_shadow.get("live_trigger_auto_enabled", False)),
            },
            "required_for_lift": "human_sign_off + separate A-track evidence chain (not this artifact alone)",
        },
        {
            "id": "mt_only_textual_variant_stubs",
            "tier": "corpus",
            "severity": "medium",
            "reason_ko": "MT-only 15절은 textual_variant_omission 정책 스텁 — 완전 원어 100% 주장 불가",
            "observed": {
                "gap_pipeline_stub_rows": ops.get("gap_pipeline_stub_rows"),
                "mt_only_residual_taxonomy": ops.get("mt_only_residual_taxonomy"),
                "coverage_diff_complete_gap": ops.get("coverage_diff_complete_gap"),
                "missing_nt_count": nt_gap.get("missing_nt_count"),
                "nt_gap_manifest": _rel(nt_gap_path) if nt_gap else None,
                "missing_nt_verse_ids_sample": (nt_gap.get("missing_nt_verse_ids") or [])[:5],
            },
            "forbidden_claim": str(lexical.get("forbidden_external_claim") or ""),
        },
        {
            "id": "hypothesis_tier_b_only",
            "tier": "research",
            "severity": "medium",
            "reason_ko": "4D·게마트리아·그래프는 [HYPO] 분포 관측 — 신학·시장·무손실 단정 금지",
            "observed": {"hypothesis_tier": go.get("hypothesis_tier"), "research_only": True},
        },
        {
            "id": "merge_satellite_into_complete_forbidden",
            "tier": "corpus",
            "severity": "medium",
            "reason_ko": "TR/DSS/외경 위성 레인을 complete jsonl에 병합 금지",
            "observed": {
                "merge_tr_into_complete_forbidden": bool(
                    (ops.get("multi_orbit_b_track") or {}).get("merge_tr_into_complete_forbidden")
                )
            },
        },
        {
            "id": "forbidden_marketing_claims",
            "tier": "copy",
            "severity": "high",
            "reason_ko": "우주 OS 완성·무조건 예측·실매매 트리거·신경과학/장내미생물 증명 금지",
            "forbidden_patterns_ko": [
                "완벽 100% 원어/무손실 압축",
                "우주 OS 완성·신학적 정답 단정",
                "실매매·Track A 자동 트리거",
                "신경과학·장내미생물로 성과·치유 증명",
            ],
            "policy_pointer": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md §3",
        },
    ]

    allowed_internal: list[dict[str, Any]] = [
        {
            "id": "btrack_single_anchor_operational",
            "note_ko": "31,102 단일 앵커 코퍼스·게마트리아 브리지·회귀·쇼룸 B-track 운영",
            "observed": {
                "union_rows": ops.get("union_rows"),
                "lexical_in_complete_jsonl": ops.get("lexical_in_complete_jsonl"),
                "regression_49_passed": ops.get("regression_49_passed"),
            },
        },
        {
            "id": "s1_shadow_kpi_ready_for_review",
            "note_ko": "S1_SHADOW KPI 검토 대기(Track A 승격 아님)",
            "pointer": _rel(ART / "logos_shadow_promotion_kpi_progress_latest.json"),
        },
        {
            "id": "b2b_internal_meeting_pack",
            "note_ko": "내부 B2B 미팅 팩·부록(법무 전 대외 발송 금지)",
            "observed": {"ready_for_internal_meeting": bool(b2b.get("ready_for_internal_meeting", False))},
        },
    ]

    payload = {
        "schema": "logos_single_anchor_promotion_blockers_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": go.get("hypothesis_tier", "B"),
        "research_only": True,
        "purpose_ko": "Track C B2B·내부 실사에서 의도적 차단·비주장 항목을 아티팩트로 고정 (LG 화요일 미팅 일정 없음)",
        "inputs": {
            "go_no_go_json": _rel(go_path),
            "shadow_status_json": _rel(shadow_path),
            "b2b_readiness_json": _rel(b2b_path),
        },
        "promotion_tiers_blocked": {
            "external_send": True,
            "track_a_live_trading": True,
            "a_track_auto_promotion": True,
        },
        "blockers": blockers,
        "allowed_internal_only": allowed_internal,
        "decision": {
            "status": "PROMOTION_TIERS_BLOCKED_BY_POLICY",
            "blocker_count": len(blockers),
            "internal_b2b_ok": bool(b2b.get("ready_for_internal_meeting", False)),
            "s1_shadow_seal_candidate": True,
        },
        "disclaimer_ko": (
            "본 JSON은 승격 불가·비주장 목록이며, 코퍼스 품질 통과 증명이나 법무 승인을 대체하지 않습니다."
        ),
    }

    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"STATUS={payload['decision']['status']} blockers={len(blockers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
