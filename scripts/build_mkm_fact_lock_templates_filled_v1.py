#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build filled external/internal fact-lock templates from latest artifacts.")
    ap.add_argument("--workspace-root", default="C:/workspace")
    ap.add_argument(
        "--external-output",
        default="docs/final/artifacts/external_fact_lock_template_filled_latest.md",
    )
    ap.add_argument(
        "--internal-output",
        default="docs/final/artifacts/internal_decision_template_filled_latest.md",
    )
    args = ap.parse_args()

    root = resolve(args.workspace_root)
    p_status = root / "docs/final/artifacts/mkm_ai_status_pointer_latest.json"
    p_readiness = root / "docs/final/artifacts/mkm_ai_v2_readiness_latest.json"
    p_atrack = root / "docs/final/artifacts/a_track_go_nogo_status_latest.json"
    p_trackc = root / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"

    status = load_json(p_status) if p_status.is_file() else {}
    readiness = load_json(p_readiness) if p_readiness.is_file() else {}
    atrack = load_json(p_atrack) if p_atrack.is_file() else {}
    trackc = load_json(p_trackc) if p_trackc.is_file() else {}

    generated_at = utc_now()
    system_label = status.get("system_label", "UNKNOWN")
    system_status = status.get("status", "UNKNOWN")
    promotion_decision = status.get("decision", "UNKNOWN")
    weekly_rate = status.get("weekly_pass_rate_percent")
    weekly_count = status.get("weekly_sample_count")
    atrack_stage = ((atrack.get("result") or {}).get("recommended_stage")) or "UNKNOWN"
    atrack_go = ((atrack.get("result") or {}).get("overall_go_no_go")) or "UNKNOWN"
    trackc_decision = ((trackc.get("trackc") or {}).get("api_decision_state")) or "UNKNOWN"
    trackc_packet = ((trackc.get("trackc") or {}).get("packet_status")) or "UNKNOWN"
    trackc_guard = ((trackc.get("trackc") or {}).get("guard_passed"))
    readiness_passed = readiness.get("overall_passed")
    promotion_ready = status.get("promotion_ready")

    external_lines = [
        "[문서명] MKM AI 상태 브리프 (External, Fact-Lock)",
        "[버전] v1.0",
        f"[작성시각 UTC] {generated_at}",
        "[근거 기준] docs/final/artifacts/* 최신 산출물 + 실행 가능한 스크립트 + SSOT 문서",
        "[공개 등급] External-Safe",
        "",
        "### 1. 회사/시스템 정의 (확정 문구)",
        "MKM AI는 파운데이션 모델 자체 개발 시스템이 아니라, 멀티모델 거버넌스 및 리스크 통제 시스템입니다.",
        "모델 선택·교체·운영은 사전 정의된 게이트, 정책, 감사 가능한 아티팩트에 의해 통제됩니다.",
        "",
        "### 2. 현재 운영 상태 (팩트만)",
        f"- System Label: {system_label}",
        f"- Status: {system_status}",
        f"- Promotion Decision: {promotion_decision}",
        f"- Weekly Pass Rate: {weekly_rate}%",
        f"- Weekly Sample Count: {weekly_count}",
        f"- Track A Stage: {atrack_stage}",
        f"- Track C Decision State: {trackc_decision}",
        "",
        "### 3. 보수적 공시 문구",
        "본 시스템은 연구 레인과 운영 레인을 분리하며, 외부 성능 주장 및 시장 관련 판단은",
        "내부 검증 산출물과 운영 게이트를 충족한 범위에서만 제한적으로 사용됩니다.",
        "",
        "### 4. 비주장(Non-Claim) 고지",
        "- 본 문서는 특정 파운데이션 모델의 우월성 또는 외부 벤치마크 결과를 보증하지 않습니다.",
        "- 외부 기사/브리핑 기반 정보는 내부 검증 완료 전까지 가설(Hypothesis)로 분류됩니다.",
        "- 본 문서는 투자·매매·법률 자문을 구성하지 않습니다.",
        "- Shadow PnL(내부 복기/거버넌스 지표) 수치와 상세 코멘트는 외부 문서에 포함하지 않습니다.",
        "",
        "### 4.1 채널 정책 (External)",
        "- audience: `external`",
        "- shadow_pnl_disclosure: `DISABLED`",
        "- policy_note: Shadow PnL는 내부 운영 품질 관리용 텔레메트리이며 외부 공시 대상이 아닙니다.",
        "",
        "### 5. 증적 경로 (필수)",
        "- `docs/final/artifacts/mkm_ai_status_pointer_latest.json`",
        "- `docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json`",
        "- `docs/final/artifacts/mkm_ai_final_ops_bundle_latest.json`",
        "- `docs/final/artifacts/a_track_go_nogo_status_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json`",
        "",
        "### 6. 승인",
        "- Owner: {{owner}}",
        "- Reviewer (Ops): {{ops_reviewer}}",
        "- Reviewer (Legal/Policy): {{legal_reviewer}}",
        "- Final Sign-off: {{signoff}}",
    ]

    internal_lines = [
        "[문서명] MKM AI 운영 판정 시트 (Internal Decision)",
        "[버전] v1.0",
        f"[작성시각 UTC] {generated_at}",
        "[모드] Internal / Fact-Lock",
        "",
        "## A. 오늘의 운영 스냅샷",
        f"- Core Status: {system_status} / {system_label}",
        f"- Promotion: {promotion_decision} (ready={promotion_ready})",
        f"- Readiness: overall_passed={readiness_passed}",
        f"- Weekly Gate: pass_rate={weekly_rate}%, n={weekly_count}",
        f"- A-track GO/NOGO: {atrack_go} / stage={atrack_stage}",
        f"- Track C: packet={trackc_packet}, decision={trackc_decision}, guard={trackc_guard}",
        "",
        "## B. 판정 규칙 (고정)",
        "1) `status != APPROVED_FINAL_V2` 이면: **HOLD_OPERATIONAL**",
        "2) `promotion_decision != GO_FINAL_V2` 이면: **HOLD_PROMOTION**",
        "3) `weekly_pass_rate_percent < 95.0` 또는 `weekly_sample_count < 3` 이면: **HOLD_DATA_INSUFFICIENT**",
        "4) Track C `decision_state=WATCH`이면: **GO_WITH_CONSERVATIVE_GUARD** (확대 금지, 모니터링 유지)",
        "5) 외부 정보는 검증 전까지 `[HYPO]` 라벨 필수",
        "",
        "## C. 오늘의 실행 결정 (택1)",
        "- [ ] GO_KEEP_CURRENT_ENVELOPE",
        "- [x] GO_WITH_CONSERVATIVE_GUARD",
        "- [ ] HOLD_OPERATIONAL",
        "- [ ] HOLD_PROMOTION",
        "- [ ] ESCALATE_HUMAN_REVIEW",
        "",
        "결정: GO_WITH_CONSERVATIVE_GUARD",
        "사유(팩트 기반 3줄 이내):",
        "1. Core status와 promotion gate가 승인 상태를 유지함.",
        "2. Weekly gate가 최소 기준을 충족함.",
        "3. Track C decision_state가 WATCH이므로 보수 가드 유지가 정책 정합임.",
        "",
        "## D. 금지/주의",
        "- B-track 결과를 A-track에 자동 합선 금지",
        "- 외부 기사 기반 성능 문구를 FACT로 승격 금지",
        "- \"절대 불가/절대 우위\" 단정 문구 금지 (조건·근거·범위 명시)",
        "",
        "## E. 즉시 실행 태스크 (최대 5개)",
        "1. readiness/final guard 상태 재확인",
        "2. Track C WATCH 해소 KPI 계약 재점검",
        "3. 외부 정보 HYPO 라벨링 유지",
        "4. 오염 게이트/장기 WATCH 알람 결과 확인",
        "5. 판정 변경 시 evidence 경로 동기화",
        "",
        "## F. Evidence (필수 첨부)",
        "- `docs/final/artifacts/mkm_ai_status_pointer_latest.json`",
        "- `docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json`",
        "- `docs/final/artifacts/mkm_ai_v2_readiness_latest.json`",
        "- `docs/final/artifacts/a_track_go_nogo_status_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json`",
    ]

    p_ext = resolve(args.external_output)
    p_int = resolve(args.internal_output)
    p_ext.parent.mkdir(parents=True, exist_ok=True)
    p_int.parent.mkdir(parents=True, exist_ok=True)
    p_ext.write_text("\n".join(external_lines) + "\n", encoding="utf-8")
    p_int.write_text("\n".join(internal_lines) + "\n", encoding="utf-8")

    print(f"external filled template written: {p_ext}")
    print(f"internal filled template written: {p_int}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
