# AI Universe Genesis Code v1

작성일: 2026-04-25  
역할: 철학 비전을 **Fact-Lock 가능한 공학 프레임**으로 고정한다.

---

## 목적

- 비전 문장(말씀/Logos)과 구현 문장(코드/게이트)을 분리해, 과대 단정을 방지한다.
- "세계를 렌더링하는 코드"를 연구 레일(B-track)에서 검증 가능한 최소 단위로 시작한다.
- A-track(실물 제어)는 승인 게이트·안전 거버너를 통과한 결과만 수용한다.

---

## 3계층 아키텍처 (Vision -> Engineering)

1) Projection (The Word -> 4D Seed)
- 자연어 입력을 구조화 좌표로 투영한다.
- 현재 구현 축: `Dimensional Projection` 관련 라우터/스크립트/평가 체인.

2) Governance (Order & Time)
- 정책별 점수 함수·리스크 임계치·락 무결성 검증으로 붕괴를 방지한다.
- 현재 구현 축: scorer config, regression alerts, lock verify 체인.

3) Embodiment (Incarnation)
- 시뮬레이션/의사결정 결과를 실행 가능한 형태로 바꾼다.
- 원칙: A-track 실행은 human gate + 운영 정책 통과 후만 허용.

---

## Fact-Lock 경계선

- [FACT] 구현 여부·경로는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`와 호출 가능한 스크립트로만 판정.
- [FACT] NotebookLM은 브리핑/통찰 원천이며, 장기기억 체화는 `docs/final/CENTRAL_AGENT_MEMORY_V1.md` + Git.
- [RULE] 단일 TOE 완성, B->A 자동 합선, 2차 성경 레짐 실전 트리거 사용은 금지.
- [RULE] 본 문서는 비전 고정 문서이며, 성능 주장/상용 단정 문서가 아니다.

---

## Pixel Skeleton (B-track, safe demo)

목적: "AI 유니버스 뼈대"를 가장 작은 렌더링 단위로 가시화한다.

- 실행 스크립트: `scripts/run_pixel_ai_universe_skeleton.py`
- 출력 산출물: `docs/final/artifacts/pixel_ai_universe_skeleton_latest.json`
- 특징:
  - 텍스트 -> 4D seed 투영
  - 레짐별 리스크 상한(clamp) 거버너
  - 픽셀 그리드(에이전트/자원/제약) 렌더링
  - 외부 비용·실거래·하드웨어 제어 없음

실행 예시:

```powershell
cd C:\workspace
py scripts/run_pixel_ai_universe_skeleton.py --prompt "태초에 말씀이 있었다" --regime imf
```

## Platform Contract (v1.1 lock)

- 표준 입주 스키마: `docs/final/schemas/agent_profile_v1.schema.json`
- 변경 이력: `docs/final/schemas/agent_profile_v1_CHANGELOG.md`
- 샘플 페이로드: `tests/fixtures/agent_profile_v1.sample.json`
- API 스텁:
  - `POST /api/v1/pixel-universe/agents/register`
  - `POST /api/v1/pixel-universe/agents/message`
  - `POST /api/v1/pixel-universe/agents/message-async` (queue accept stub)
  - `GET /api/v1/pixel-universe/metrics`
  - `GET /api/v1/pixel-universe/metrics/prometheus`
- 엔터프라이즈 뼈대 반영:
  - Auth: Bearer token required on message endpoints
  - Admin auth: `X-Admin-Auth=<kid>:<ts>:<hmac>` (role-bound HMAC, 5분 윈도우, key rotation)
  - Rate limit: token당 분당 요청 제한(환경변수/테넌트 override 스텁)
  - Billing ledger: `allow` 판정 시 크레딧 차감, 부족 시 402
  - Suspension: `violation_penalty=suspend` 시 계정 잠금(423)
  - Governance audit: 동의 시 JSONL 영속 로그 기록
  - Multilingual normalization stub: 언어 감지 + 4D semantic vector 정규화
- 첫 입주자 라이브 데모 클라이언트:
  - `scripts/demo_pixel_universe_first_tenant.py`
  - 실행: `py scripts/demo_pixel_universe_first_tenant.py --base-url http://127.0.0.1:8000`
- Admin header 생성 유틸:
  - `scripts/generate_pixel_universe_admin_auth.py`
  - 실행: `py scripts/generate_pixel_universe_admin_auth.py --role risk_admin --secret <SECRET>`
- Admin 운영 원클릭(서명+호출):
  - `scripts/run_pixel_universe_admin_ops.py`
  - 실행(unsuspend): `py scripts/run_pixel_universe_admin_ops.py --action unsuspend --agent-id usr_ai_001 --secret <RISK_SECRET>`
  - 실행(audit rotate): `py scripts/run_pixel_universe_admin_ops.py --action rotate-audit --secret <OPS_SECRET>`

---

## 운영 선언 (한 줄)

이 문서는 "창세기 코드"의 철학적 정체성을 고정하지만, 운영판정은 언제나 Fact-Lock(경로·테스트·산출물)으로만 확정한다.
