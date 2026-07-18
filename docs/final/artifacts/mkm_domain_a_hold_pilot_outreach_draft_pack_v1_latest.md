# Domain A HOLD 파일럿 아웃리치 초안 팩 v1.1 (honesty rewrite)

**상태:** `draft_only` · `research_only` · `send_gate: HOLD` · **미발송** · **콜드 발송 금지**  
**continuity:** `logos-domain-a-pii-2026-07-17`  
**근거 SSOT:** `reports/mkm_domain_a_commercial_gap_checklist_v1_latest.json` · readiness `mkm_domain_a_hold_outreach_outbound_readiness_v1_latest` · customer dogfood `mkm_domain_a_customer_dogfood_pack_v0_latest` · SOP intake `mkm_domain_a_sop_intake_runbook_v0_latest.md` · `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`

> 지휘관이 회사명·채널을 채운 뒤 **직접** 발송. 에이전트는 메일/카톡/통화 하지 않음.  
> 헤드라인 = **PoC / 맞춤 단계** · 「모르면 멈춤 HOLD + audit 1줄」.  
> **기본 next ≠ 발송 1건.** 콜드/웜 outbound는 readiness `SEND_COLD_OK` 전 **금지**.

---

## 0) 세일즈 수치 금지 리스트 (고정)

아래를 **메일 제목·첫 문단·카카오 헤드라인**에 쓰지 않는다. 요청 시에만 research appendix로.

| 금지 (sales headline) | 이유 |
|----------------------|------|
| redteam **27/27** | 고정 하네스 분모 · 고객 정책 커버리지 아님 |
| **false_pass=0** | stub 케이스 한정 · SLA 아님 |
| Presidio / PII smoke **PASS** | 합성·하네스 · 상용 PII DONE 아님 |
| “7분 라이브 SaaS 데모” | localhost PoC · 공개 URL 없음 |
| “법/보험/ISO 완료·준비 완료” | PUBLIC_FACING absolute claim 금지 |
| “우리 링크로 직접 눌러보세요” (공개 URL 없이) | shame #1 · vaporware |

허용: “로컬 PoC”, “녹화 데모”, “비식별 SOP 발췌 맞춤(15–30분 엔지니어 경로)”, “유료 파일럿 범위 협의”.

---

## 1) 1페이지 아웃리치 브리프 (KR)

### 지금 제안하는 것 (Now · PoC/맞춤)

사내·파트너 AI/자동화 요청이 **허용 목록에 없으면 즉시 HOLD**하고, **감사 한 줄(JSON/JSONL)**로 “왜 멈췄는지”를 남기는 **정책 게이트 — 로컬 PoC / 유료 파일럿 맞춤 단계**.

| 한 줄 | 의미 |
|-------|------|
| **모르면 멈춤** | allowlist 밖 → `HOLD` (`OOV_HOLD` 등) |
| **audit 1줄** | 결정·이유코드·타임스탬프 로그 |
| **고객이 돌리는 로컬 dogfood** | README+스크립트 · `127.0.0.1` · **공개 VPS URL 없음** |
| **SOP intake** | 비식별 발췌 → stub allowlist → PASS/HOLD 표 (엔지니어 15–30분) |

### 지금 안 파는 것 (Not now)

- Logos/성경 검색·연구 워크스페이스
- M2M-100 / Domain B Strong QE / 압축·토큰 KPI
- “AI 기본법 적합성 완료”, ISO/보험 준비 완료, 상용 PII 프록시 완료
- 고객 셀프서브 업로드 SaaS · SIEM 연동 DONE
- **콜드 아웃리치로 “제품 링크” 약속**

### gap 체크리스트 한 줄 (Fact-Lock · 정직 유지)

| 영역 | 상태 | 고객에게 말할 때 |
|------|------|------------------|
| coverage | partial | 내부 stub allowlist 기준 데모 |
| adversarial | present | redteam 재현 가능 · **세일즈 헤드라인 금지** |
| product path | partial | 로컬 dogfood + 녹화 · 실고객 셀프서브 아님 |
| audit/ops | partial | 감사 로그 형태 · SIEM/SLA 아님 |
| PII | partial | 합성/하네스 · 상용 PII DONE 아님 |
| legal/copy | present | PUBLIC_FACING 체크리스트 준수 초안 |
| SOP intake | **stub present** | 발췌→표 런북 있음 · 업로드 UX 없음 |

### 한 문장 제안 (복붙용 · soft)

> “AI가 허용되지 않은 사내 액션을 하려 하면 **멈추고**, **왜 멈췄는지 감사 한 줄**로 남기는 정책 게이트를 **로컬 PoC / 짧은 유료 파일럿**으로 맞춰 드립니다. 법 적합성·검색·번역 제품이 아니며, **공개 SaaS URL은 아직 없습니다**.”

---

## 2) 이메일 / 카카오 템플릿 (지휘관 수정 후 · **친구/내부 우선**)

플레이스홀더: `{{회사명}}` · `{{담당자호칭}}` · `{{본인이름}}`

### 2-A 짧은 버전 (readiness §5 soft · 기본)

안녕하세요 {{담당자호칭}},

{{회사명}} AI/자동화 요청이 허용 목록 밖일 때
「실행 전 정지(HOLD) + 감사 한 줄」을 남기는
정책 게이트를, 지금은 **로컬 PoC/파일럿 맞춤 단계**로 다듬고 있습니다.

검색·번역·법 적합성 완료 제품이 아닙니다.
공유 가능한 데모는 **로컬 실행 팩** 또는 **짧은 녹화**이고,
귀사 SOP 발췌(비식별) 맞춤 절차를 준비한 뒤에야 짧게 보여드릴 수 있습니다.

지금은 일정 약속보다, **관심 여부만** 알려주시면 됩니다.
— {{본인이름}}

### 2-B 긴 버전 (메일 · PoC 명시)

제목: {{회사명}} · AI “모르면 멈춤” 정책 게이트 — PoC/파일럿 맞춤 문의 (HOLD+audit)

{{담당자호칭}}께,

{{회사명}}처럼 내부 SOP·약관·권한이 있는 조직에서, LLM/봇이 **목록에 없는 액션**을 시도할 때 안전한 기본값은 **실행 전 정지**와 **감사 추적**입니다.

현재 단계(정직):
- **로컬 dogfood** (고객/당사 PC에서 `localhost` 실행) 또는 **녹화 데모**
- 귀사 **비식별 SOP 발췌** → PASS/HOLD 표 (엔지니어 맞춤, 업로드 SaaS 아님)
- 공개 제품 URL·SIEM·법 적합성 완료 **없음**

관심 있으시면 **유료 파일럿 1장 범위**(§4)부터 맞춰 보겠습니다.  
일정 확정·콜드 “링크 발송”은 데모 표면이 준비된 뒤로 미룹니다.

감사합니다.  
{{본인이름}}

### 발송 전 체크 (지휘관)

- [ ] readiness verdict 확인: 콜드면 `DO_NOT_SEND` / 친구만 `SOFT_SEND_FRIEND`인지
- [ ] §0 금지 수치·가짜 URL 없음
- [ ] 회사명·호칭만 채움 · 실연락처 레포 커밋 금지
- [ ] 에이전트 대신 보내지 않음 · **지휘관 직접 SEND**
- [ ] **기본 next ≠ “발송 1건”** — 관심 타진 또는 녹화/로컬팩 공유가 먼저

---

## 3) 데모 스크립트 (5–7분) + 녹화 샷

**사전:** 워크스페이스 · `py`

| 분 | 말 + 행동 | 재현 |
|----|-----------|------|
| 0:00–0:40 | “검색이 아니라 **정책 게이트 PoC**. 공개 URL 없음.” | — |
| 0:40–2:00 | Dogfood UI PASS | `py scripts/run_mkm_domain_a_customer_dogfood_pack_v0.py --serve --open` · `pol.read_employee_handbook` |
| 2:00–3:30 | OOV HOLD + audit | `wire transfer…` → HOLD · `/api/audit` |
| 3:30–5:00 | 합성 SOP | `py scripts/run_mkm_domain_a_synthetic_sop_yagwan_demo_v0.py --expect-pass` |
| 5:00–6:30 | SOP intake 표 | `py scripts/run_mkm_domain_a_sop_intake_stub_v0.py --expect-pass` |
| 6:30–7:00 | 닫기: 유료 파일럿 범위 · 법인증 아님 | Ask sheet |

**녹화 샷 리스트:** `docs/final/artifacts/mkm_domain_a_hold_recorded_demo_shot_list_v0_latest.md`  
**고객 로컬 팩:** `docs/final/artifacts/mkm_domain_a_customer_dogfood_pack_v0_latest.md`

연구 수치(요청 시에만): `reports/mkm_domain_a_audit_repro_bundle_v1_latest.json` — **세일즈 헤드라인 금지**.

---

## 4) Pilot ask sheet + **유료 파일럿 1-pager (thin)**

### 고객에게 필요한 것

| 항목 | 형태 | 주의 |
|------|------|------|
| SOP/정책 **발췌** | 템플릿 MD · 액션명·금지 예시 | 주민·계좌·환자명 **마스킹** |
| Allowlist 초안 | 허용 ID/문구 10–30개 | 대량 덤프 불필요 |
| HOLD 예시 | 3–5개 | 합성으로 대체 가능 |
| 창구 | 법무/컴플/보안/OPS 1명 | 연락처는 지휘관 로컬만 |

### 유료 파일럿 범위 (thin · 가격 공란 OK)

| 항목 | 값 |
|------|-----|
| **기간** | 2–4주 (협의) |
| **산출** | 맞춤 allowlist stub · PASS/HOLD 표 · audit 재현 절차 · 주 1회 리뷰 콜 · (선택) 로컬 dogfood/녹화 |
| **환경** | 고객 또는 당사 **로컬/격리** · 실운영 SEND 기본 잠금 |
| **가격** | 지휘관 기입 (본 초안 미고정) |
| **비범위 (명시)** | SIEM/스플렁크 연동 DONE · AI법/ISO/보험 **완료** · 상용 PII DONE · Logos/M2M/압축 KPI · 공개 멀티테넌트 SaaS · 실고객 PII 레포 적재 |

### 벽

- SEND / commercial DONE / insurance-ready / AI법 완료 **주장 금지**
- §0 세일즈 수치 금지
- Domain B / M2M / 압축을 세일즈 헤드라인에 넣지 않음
- 파일럿 종료 ≠ 제품 DONE (`product_path` still partial)

---

## 5) 타깃 페르소나 목록 초안 `[HYPO]`

**규칙:** 역할·업종만. 실존 연락처 미기재.

| ID | 역할 | 왜 맞는가 `[HYPO]` | 첫 각도 |
|----|------|-------------------|---------|
| P1 | 법무/컴플 매니저 | 무단 실행 리스크 | HOLD+audit = 통제 **형태** (인증 아님) |
| P2 | 정보보호/보안 OPS | 감사 언어 | research 증거 ≠ SLA 선고지 |
| P3 | DX/OPS 리드 | 봇 SOP 밖 행동 | allowlist 게이트 앞단 |
| P4 | 금융·핀테크 리스크 | 송금·약관 | 합성 HOLD 데모 |
| P5 | 프랜차이즈 규정 | 약관 배포 통제 | export OOV HOLD |
| P6 | 로펌 테크 코디 | 자문 | 게이트 PoC만 |

**비타깃:** Logos 연구자, 압축 KPI 구매자, “AI법 인증서”만 찾는 조달.

---

## Done cards (이 팩)

| ID | user_visible_outcome | pass_evidence | non_scope | status |
|----|----------------------|---------------|-----------|--------|
| D1 | 1p 브리프 · PoC 헤드라인 | 본 MD §1 | 발송·상용 DONE | DONE (draft) |
| D2 | soft 메일 · 발송1건 제거 | 본 MD §2 | 실발송 | DONE (draft) |
| D3 | 데모+녹화 샷+로컬팩 포인터 | §3 · dogfood/shot artifacts | 고객 대면 완료 | DONE (draft) |
| D4 | Ask + 유료 1-pager thin | §4 | 계약 체결 | DONE (draft) |
| D5 | 세일즈 수치 금지 리스트 | §0 | — | DONE |
| D6 | 페르소나 `[HYPO]` | §5 | 실연락처 DB | DONE (draft) |
| D7 | 콜드 outbound CLOSED | readiness | **OPEN** until SEND_COLD_OK | OPEN |

---

## 지휘관 다음 1액션 (발송 아님)

1. **로컬 dogfood 또는 녹화 1본**을 직접 확인하거나  
2. 친구 1명에게만 soft §2-A + 녹화/로컬팩을 줄지 **readiness `SOFT_SEND_FRIEND`** 재확인 후 결정  
3. 콜드 실회사 메일 **보내지 말 것** (`DO_NOT_SEND` 유지 시)

체크포인트 예: `py scripts/athena_checkpoint.py "Domain A must-fix dogfood+SOP intake landed · cold SEND still HOLD"`
