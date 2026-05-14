# Research open questions — 심사·토의 큐 (v1)

**역할:** 레포 안에서 **아직 확정·승격 전**인 주제만 모은다. 여기 한 줄이 **구현 완료·테스트 통과·본선 반영**을 뜻하지 않는다. Fact-Lock·경로·게이트는 항상 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`와 호출 가능 스크립트가 우선이다.

**승격 루틴:** 토의로 결론이 나면 (1) `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 또는 `CONSTITUTION` 표·절, (2) 이슈/PR, (3) 스크립트·테스트 중 **해당하는 곳**으로 옮기고, 아래 표에서 **상태를 `CLOSED`로 바꾸거나 행을 삭제**한다.

**상태 태그:** `OPEN` = 심사 중 · `HOLD` = 정보 부족 · `CLOSED` = 이관 완료(행 유지 시에만)

---

## 큐 (표)

| id | 상태 | 주제 (한 줄) | 왜 열려 있는가 | 근거 포인터 (레포 경로만) | 다음 토의 질문 (한 줄) |
|----|------|--------------|----------------|---------------------------|-------------------------|
| RQ-001 | OPEN | B-track → Track A 승격 시 **latency·error 게이트 AND**를 운영에서 어떻게 증명할지 | AGENTS·플레이북에 수치 게이트가 있으나 현장 증빙 루틴이 사람마다 다를 수 있음 | `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 · 루트 `AGENTS.md` A/B 승격 절 | 자동화 산출물 하나로 GO를 찍을지, 분기별 수동 승인을 남길지 |
| RQ-002 | OPEN | **NotebookLM MCP** `add_source` 실패(한국어 UI 등) 시 “웹 수동 업로드” 의존도를 얼마나 허용할지 | CENTRAL에 이미 한계가 기록됨; 재발 시 운영 부담 | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` nl_sync · `docs/NotebookLM_sources_manifest.md` | MCP 패치 우선 vs Vault·웹만 SSOT로 고정할지 |
| RQ-003 | OPEN | **한의** 라벨 코호트 A vs 원전·Proxy B — 자동 파이프라인 경계를 어디까지 코드로 강제할지 | 핸드오프는 명시; 자동 합선 방지를 게이트로 더 쪼갤지 여부는 제품 정책 | `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` | B를 어떤 단계에서 차단하면 UX·연구 속도가 깨지지 않는지 |
| RQ-004 | OPEN | **국방 `GO_RESEARCH`** 레인과 Track C·상용 API 승격의 **이름·문서 상 분리**를 더 촘촘히 할지 | P0 표에 경로 있음; 대외 카피와의 거리는 정책 | `docs/final/P0_COMMERCIALIZATION_TRACKER.md`(국방 행) · `docs/final/artifacts/defense_code_pack_v1.json` | `research_only` 라벨을 어디(리포트·UI·패키지)까지 강제할지 |
| RQ-005 | OPEN | **MKM-Orchestrator** GO+·번인·글로벌 오케스트레이터 산출을 “운영 대시보드”에 얼마나 노출할지 | §1.4 표가 넓음; 노출 범위는 제품·보안 선택 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.4 | 운영자가 봐야 하는 최소 필드 집합은 무엇인지 |
| RQ-006 | OPEN | **Multi-Lens 중간 레이어** 잔여 행(번들 기본 밖)을 주차 단위로 밀 때 **우선순위 키**를 무엇으로 둘지 | 워크리스트에 “번들 DESCRIPTION이 SSOT”라고 이미 있음 | `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 하단 단일 태그 표 | TruthfulQA·Track A 하네스·BGM 중 다음 분기 하나만 고른다면 |
| RQ-007 | OPEN | **압축 투트랙** 마케팅·대외 문구와 `*_latest` 아티팩트의 **동기화 책임** (누가 언제 갱신하는지) | SLA·정책 문서는 있음; 프로세스 소유는 팀 규칙 | `docs/final/COMPRESSION_SLA_POLICY_V1.md` · `docs/final/P0_COMMERCIALIZATION_TRACKER.md` | 릴리즈 태그·주간 거버넌스 중 어디에 “대외 한 줄”을 고정할지 |
| RQ-008 | OPEN | **옵시디언 UNIVERSE** 그래프와 Git SSOT의 **이중 관리**를 줄일지 (인박스만 Git, 그래프는 로컬 유지 등) | CENTRAL에 볼트 격벽 이미 있음 | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` 옵시디언 절 · 로컬 `memory/obsidian_vault/UNIVERSE_MKm/` | 주 1회 동기화 의식으로 충분한지, 끌어올릴 노트 화이트리스트가 필요한지 |
| RQ-009 | OPEN | **실버 테크(시니어 음성·돌봄 UX)** 에 MKM **격벽·조율 상태·Fact-Lock** 패턴을 이식할 때 제품 경계·규제(B2G/B2B2C·보호자 동의·비의료 면책)를 어디까지 SSOT에 동결할지 | **2026-05-15 지휘관 승인:** `TRACK_C` §3.7.2 **(B)** 민감 외부 액션에 **구조적 휴먼 게이트**(자동 단독 실행 불가 전제, 알림·승인·차단·감사 로그) **SSOT 동결**. **파일럿 KPI 수치·마진·최종 면책 문구**는 Git SSOT 본문·동 §3 체크리스트에 **동결 지연** — 내부 R&D·제안 별첨·`silver_tech_cogs_unit_economics_template_v1.md` 등 `[HYPO]`. **(D)** 면책 초안·관할별 문구는 **법무 확정 후** 최종 반영. **2026-05-16:** 내부 면책·경계 **확장 초안 패킷** `docs/final/artifacts/silver_tech_legal_disclaimer_draft_v1.md` 추가(대외 최종 아님). | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.7.2 · `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` §3 **(v1.4)** · `docs/final/schemas/patient_care_bundle_v1.schema.json` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9 표(`patient_care_bundle_v1`) · `scripts/Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1` · `docs/research/silver_tech_cogs_unit_economics_template_v1.md` · `docs/final/artifacts/silver_tech_legal_disclaimer_draft_v1.md` | 법무 (D) 확정문을 `PUBLIC`·Track C에 넣을 일정·파일럿 실측 후 KPI 수치를 SSOT 본문에 승격할지 별첨만 유지할지? |
| RQ-010 | OPEN | **초개인화 에이전트 / B2B 컨텍스트 API**(구조화 MKM·렌즈 프로필 JSON을 타사 앱·에이전트에 공급) 비전을 **IR·제안서 한 줄**로 열어두되, **제품·데이터·규제 SSOT**와 어떻게 분리할지 | 내부 운영(핸드오프·CONSTITUTION)과 **외부 결합**은 동의·TOS·데이터 최소화·의료·지식재산 경계가 다름; 명리·사상·Logos는 **렌즈 계약·격벽** 유지, 임상·실거래·본선 자동 합선 금지 전제와 정합 필요 | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3.3·§9 · `docs/final/P0_COMMERCIALIZATION_TRACKER.md` · `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` · RQ-009 행 | 1차 파일럿 세그먼트(웰니스 코칭 vs 개발자 도구)·**사용자 동의·감사 로그**를 어디에 고정할지; LoRA 대량 개인화 vs **API+동적 컨텍스트** 운영 한도선은 어디로 둘지 |

## IR·제안서 한 줄 초안 ([HYPO] · RQ-010)

대외 최종 아님. 법무·동의 UX·제품 경계 확정 후 `docs/final/P0_COMMERCIALIZATION_TRACKER.md` / `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` / `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`로만 승격.

- **KO:** 동의·감사·데이터 최소화 전제의 MKM 구조화 프로필 API로, 파트너 AI가 사용자 톤·우선순위를 잃지 않게 돕습니다. (의료 진단·투자·실거래 신호 아님.)
- **EN:** With consent, auditability, and data minimization, MKM’s structured profile API helps partner AIs stay aligned to each user’s tone and priorities—without claiming medical diagnosis, investment advice, or live trading signals.

---

## 메타

- **schema:** `research_open_questions_v1`
- **last_reviewed_utc:** 2026-05-14 — 자동 권장 번들 재실행(STT append+summarize·`verify_p0`·pytest·예언 클로저 `closure_ok`); **2026-05-16** RQ-009 내부 패킷 `docs/final/artifacts/silver_tech_legal_disclaimer_draft_v1.md` 추가(KR/EN 초안·법무 인테이크 체크리스트). **2026-05-15** 지휘관 승인(동결 지연·구조 Lock) 본문 유지. RQ-009 **`OPEN` 유지**(법무 (D) 확정·실측 KPI·COGS 월소계 잔여). **2026-05-17** RQ-010 추가(B2B 컨텍스트 API·초개인화 에이전트 비전 큐; IR/연구 전용, Fact-Lock 본문 이관 전). **세션** RQ-010 하단 IR·제안서 한 줄 초안(KO/EN, `[HYPO]`) 블록 추가.
- **mirror (optional):** 로컬 그래프용 `memory/obsidian_vault/UNIVERSE_MKm/INBOX_연구_토의큐.md` — Git과 자동 동기화하지 않는다.
