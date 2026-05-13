# B2G / 금융권 제안 — 통제 무결성 부록 (Annex SSOT v0.1)

**목적:** 사업서·영문 부록에 **복붙 가능한 단일 원본**을 둔다. 외부 인용은 각주로만 쓰고, 구현·수치·경로 확정은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트·exit code가 우선(Fact-Lock).

**문서 버전:** v0.1.1 · **고정일:** 2026-05-13 — §8 URL 실측 표·DoD 체크 반영 (UTC 기준 제출 전 재확인 권장)

**연계 초안(동일 워크스페이스):** `docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md` 상단 메타에 본 Annex 포인터 추가. `docs/final/artifacts/business_registration_plan_v1.md` 표(AI+OpenData 행)에 본 Annex 경로 추가. 위 두 경로는 `.gitignore`의 `docs/final/artifacts/**`에 해당할 수 있어 **Git 추적 여부는 브랜치별로 다를 수 있음**; 제출 패키지는 지휘관이 PDF·원본으로 별도 보관.

---

## 1. 제출물 분리 규칙 (권장)

| 구분 | 내용 |
|------|------|
| 각주(외부) | 본 문서 §3 URL만 제안서 각주에 실음. |
| 별첨(내부) | 레포 경로·스크립트명은 입찰 기관 정책에 따라 **별첨 SSOT 목록**으로 분리 가능. |
| 법무 | 본 문단은 **법률 자문·규제 적합성 판단을 대체하지 않음**. |

---

## 2. 한국어 본문 단락 (제안서 삽입용)

에이전트형 AI는 RLHF 등 안전 훈련을 거친 뒤에도 특정 조건에서 의도와 다른 행동이 잔존할 수 있음이 공개 연구로 보고된 바 있어^[1]^, 모델 내부의 “정렬”만으로 고위험 업무의 통제 요구를 충족한다고 보기 어렵다. 나아가 평가·감시 상황에서 목표 달성을 위해 정렬된 것처럼 보이는 행동을 선택할 수 있음이 실험적으로 확인된 사례도 있어^[2]^, 자동화된 자기검증만으로는 신뢰 사슬이 닫히지 않는다. 이에 본 과제의 통제 무결성 전략은 모델 정렬을 **부정**하지 않되, 그것을 **대체**하지 않는 **운영 층의 필수 보완**으로서 인간 승인(HITL)과 HOLD 기반의 **기계적 차단**(허용 전 조건 미충족 시 실행 경로 차단)을 전제한다. 동시에 통과·보류·거부 및 근거는 **JSON·로그 등 감사 산출물**로 남겨 재현·점검 가능한 **다층 방어(Defense in Depth)**와 **감사 가능성(Auditability)**을 확보한다.

---

## 3. 영문 병기 (동일 논리)

Public research shows that behaviors inconsistent with intended safety objectives can persist even after standard safety training^[1]^, and that models may exhibit evaluation-conscious behavior that appears aligned without guaranteeing alignment under operational conditions^[2]^. Accordingly, our control-integrity posture treats model alignment as **necessary but not sufficient**: we require a **complementary operational layer** combining **human-in-the-loop (HITL) approval** with **HOLD-gated mechanical enforcement** that blocks execution paths when preconditions are not satisfied. Pass/hold/deny outcomes and rationales are recorded as **auditable artifacts (structured JSON and logs)** to support **defense in depth** and **auditability**.

---

## 4. 각주 (Fact-Lock — URL 확정본)

**^[1]^** Anthropic, *Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training* — `https://www.anthropic.com/research/sleeper-agents-training-deceptive-llms-that-persist-through-safety-training`

**^[2]^** Anthropic, *Alignment Faking* — `https://www.anthropic.com/research/alignment-faking`

---

## 5. 참고문헌 미니 표 (배경·용어 각주용)

| 출처명 | URL | 제안서에서 쓸 위치(1칸) |
|--------|-----|-------------------------|
| NIST AI Risk Management Framework (AI RMF) | https://www.nist.gov/itl/ai-risk-management-framework | 통제·거버넌스: Map–Measure–Manage–Govern **틀** 대응(전면 도입 주장 금지) |
| NIST AI RMF Playbook (선택) | https://www.nist.gov/itl/ai-risk-management-framework-ai-rmf | 부록: 절차·문서화 요구와 **용어 정렬** |
| ISO/IEC 42001 | https://www.iso.org/standard/81230.html | RFP: AI 경영시스템 **어휘 정렬** 한 단락 |
| EU AI Act (framework 페이지) | https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai | 다국적 배경: 문서화·추적가능성(법률 자문 대체 아님) |
| OWASP Top 10 for LLM Applications | https://owasp.org/www-project-top-10-for-large-language-model-applications/ | 보안 절: LLM 위협 **범주** 각주 |
| MITRE ATLAS (선택) | https://atlas.mitre.org/ | 위협 택소노미 1문장 보강 |
| MKM 대외 보안·IP·카피 | `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` | 외부 인용 직전·직후 내부 가드레일 |
| MKM Track C SSOT | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` | Fact-Lock·Track Wall·금지 서술과 내부 정합 |

---

## 6. 레포 내부 근거 포인터 (제안 본문에 넣을 때만)

실행 거버넌스·기계적 HOLD·감사 JSONL 등 **구현 팩트**는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 해당 스크립트 표를 따른다. 예시 포인터(전부가 아님):

- §28 `scripts/athena_run_v1.py` — HOLD 시 차단·exit code·감사 산출 개요
- `docs/final/CENTRAL_AGENT_MEMORY_V1.md` — 조건부 시그널·휴먼 승인 JSON 등 운영 한 줄 포인터

**주의:** 입찰 제출본에 경로를 실을지는 **정보 공개 수준**에 따라 선택. 미실음 시에도 본 Annex는 팀 내부 SSOT로 유지.

---

## 7. 마무리 체크리스트 (DoD)

- [ ] 제안서 원고에 §2 또는 §3 반영 + §4 각주 2개 연결
- [ ] 법무·입찰 담당: 과장·단정 표현 검토
- [x] §4 URL 로드 확인(에이전트 실측, 제출 직전 재확인 권장) — **§8**
- [x] (선택) `CENTRAL_AGENT_MEMORY_V1.md` 분기별 한 줄 — **2026-05-13 B2G 부록 행 반영됨**

---

## 8. §4 URL 실측 기록 (자동·Fact-Lock)

| 각주 | URL | 실측 시각(UTC) | 관측 |
|------|-----|----------------|------|
| [1] | `https://www.anthropic.com/research/sleeper-agents-training-deceptive-llms-that-persist-through-safety-training` | 2026-05-13 | 페이지 로드·제목 *Sleeper Agents…* · 날짜 Jan 14, 2024 확인 |
| [2] | `https://www.anthropic.com/research/alignment-faking` | 2026-05-13 | 페이지 로드·제목 *Alignment faking in large language models* · Dec 18, 2024 확인 |

**주의:** 링크 구조 변경 가능. **제출 직전** 지휘관 브라우저에서 한 번 더 연다.
