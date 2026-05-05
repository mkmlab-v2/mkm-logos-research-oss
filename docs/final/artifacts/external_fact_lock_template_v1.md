[문서명] MKM AI 상태 브리프 (External, Fact-Lock)
[버전] v1.0
[작성시각 UTC] {{generated_at_utc}}
[근거 기준] docs/final/artifacts/* 최신 산출물 + 실행 가능한 스크립트 + SSOT 문서
[공개 등급] External-Safe

### 1. 회사/시스템 정의 (확정 문구)
MKM AI는 파운데이션 모델 자체 개발 시스템이 아니라, 멀티모델 거버넌스 및 리스크 통제 시스템입니다.
모델 선택·교체·운영은 사전 정의된 게이트, 정책, 감사 가능한 아티팩트에 의해 통제됩니다.

### 2. 현재 운영 상태 (팩트만)
- System Label: {{system_label}}  <!-- 예: MKM AI v2.0 (Final) -->
- Status: {{status}}              <!-- 예: APPROVED_FINAL_V2 -->
- Promotion Decision: {{promotion_decision}}  <!-- 예: GO_FINAL_V2 -->
- Weekly Pass Rate: {{weekly_pass_rate_percent}}%
- Weekly Sample Count: {{weekly_sample_count}}
- Track A Stage: {{track_a_recommended_stage}} <!-- 예: S4_LIMITED_LIVE -->
- Track C Decision State: {{trackc_decision_state}} <!-- 예: WATCH -->

### 3. 보수적 공시 문구
본 시스템은 연구 레인과 운영 레인을 분리하며, 외부 성능 주장 및 시장 관련 판단은
내부 검증 산출물과 운영 게이트를 충족한 범위에서만 제한적으로 사용됩니다.

### 4. 비주장(Non-Claim) 고지
- 본 문서는 특정 파운데이션 모델의 우월성 또는 외부 벤치마크 결과를 보증하지 않습니다.
- 외부 기사/브리핑 기반 정보는 내부 검증 완료 전까지 가설(Hypothesis)로 분류됩니다.
- 본 문서는 투자·매매·법률 자문을 구성하지 않습니다.
- Shadow PnL(내부 복기/거버넌스 지표) 수치와 상세 코멘트는 외부 문서에 포함하지 않습니다.

### 4.1 채널 정책 (External)
- audience: `external`
- shadow_pnl_disclosure: `DISABLED`
- policy_note: Shadow PnL는 내부 운영 품질 관리용 텔레메트리이며 외부 공시 대상이 아닙니다.

### 5. 증적 경로 (필수)
- `docs/final/artifacts/mkm_ai_status_pointer_latest.json`
- `docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json`
- `docs/final/artifacts/mkm_ai_final_ops_bundle_latest.json`
- `docs/final/artifacts/a_track_go_nogo_status_latest.json`
- `docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json`

### 6. 승인
- Owner: {{owner}}
- Reviewer (Ops): {{ops_reviewer}}
- Reviewer (Legal/Policy): {{legal_reviewer}}
- Final Sign-off: {{signoff}}
