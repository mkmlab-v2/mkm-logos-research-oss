# Silver Tech — COGS / unit economics template (v1, `[HYPO]`)

**역할:** 내부 단가·부하 가정용 **빈 표**. `TRACK_C`·`PUBLIC_FACING` SSOT에 **숫자를 올리기 전**에 여기서만 채운 뒤, 출처·실측이 붙으면 승격한다. 대외·조달에는 **견적·로그·계약** 인용 없이 단가를 쓰지 않는다.

**연계:** `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-009** · `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.7.2.

---

## 실행 순서 (세션 합의, Fact-Lock)

1. 아래 표 **채움 + 출처 열** (벤더 콘솔·견적·자체 벤치).
2. **하이브리드 STT** 프로토타입: 로컬/온디바이스 1차 → 신뢰도·이벤트 게이트 시만 상용 API.
3. **소규모 실측** → 월 COGS **구간** → 그다음에만 대외·Track C 본문에 수치 문장 검토.

### 진행 체크리스트 (내부)

- [~] COGS 표 **근거·출처** 열 — 아래 표에 **공개 벤더 가격표·문서 URL** 1건 이상(단가·월액은 미기재; 실견적·발주서 확보 시 해당 행만 교체).
- [x] 하이브리드 STT **감사 로그 계약 v1** — `docs/final/schemas/stt_routing_audit_log_v1.schema.json` + 예시 + `tests/test_stt_routing_audit_log_schema_v1.py` (COGS 수치 비포함).
- [ ] 월 합계 **시나리오 2~3개**(보수/기준/스트레스) 이름 붙여 저장

### 참고 링크 (공개 문서만 · `[HYPO]`)

- Google Cloud **Speech-toText** 가격·SKU: https://cloud.google.com/speech-to-text/pricing (지역·모델별 과금; 본 레포 비용 아님).
- Vertex **Gemini** 가격 개요(요약·토큰 과금): https://cloud.google.com/vertex-ai/generative-ai/pricing (제품 선택 시 재확인).

---

## COGS 라인 아이템 (빈칸 표)

| 라인 아이템 | 단가 / 월 상한 (가정) | 단위 (예: 분·GB·건) | 월 사용량 (가정) | 월 소계 (가정) | **근거·출처** (URL·파일·날짜) | 비고 |
|-------------|----------------------|----------------------|------------------|----------------|------------------------------|------|
| STT — 로컬/자체 호스팅 | | | | | | GPU·VPS 고정비·전력 포함 |
| STT — 상용 API (업그레이드 경로만) | | | | | 공개 가격표: https://cloud.google.com/speech-to-text/pricing (견적·발주서로 교체) | 트리거 비율 % 별도 |
| LLM / 요약 | | | | | | |
| 푸시 / SMS / 통화 연동 | | | | | | |
| 스토리지·백업 | | | | | | |
| 서버·대역 | | | | | | |
| 운영·지원 (FTE 환산 가능 시) | | | | | | |
| 법무·감사 로그 보관 | | | | | | |
| **합계 (월)** | — | — | — | | | 시나리오 이름: |

### 시나리오 라벨 (같은 표를 2~3벌 복제해 쓸 때)

| 시나리오 ID | 가정 요약 (한 줄) | 비고 |
|-------------|-------------------|------|
| S-CONS | | 보수 (낮은 사용량·높은 단가) |
| S-BASE | | 기준 |
| S-STRESS | | 피크 부하 |

---

## 하이브리드 STT — 이벤트 로그 (계약 v1, Fact-Lock)

**공식 필드(jsonschema):** `docs/final/schemas/stt_routing_audit_log_v1.schema.json` · 최소 예시 `docs/final/schemas/stt_routing_audit_log_v1.minimal.example.json` · 회귀 `tests/test_stt_routing_audit_log_schema_v1.py`. 아래 표는 **읽기용 요약**이며, 필드명·필수 여부·열거형은 **스키마가 우선**한다. COGS 금액·견적 수치는 이 로그에 넣지 않는다.

| 필드 (요약) | 비고 |
|-------------|------|
| `event_id`, `occurred_at_utc`, `route`, `audio_duration_ms`, `pii_redaction` | 필수 |
| `session_id`, `provider`, `latency_ms`, `error_code`, `confidence`, `chars_out`, `billing_unit`, `hypothesis_tag` | 선택(emit 단계에서 채움) |
| `route` | `local` · `vendor` · `rejected` |
| `pii_redaction` | `redacted_full` · `redacted_partial` · `not_applicable` · `unknown` |

집계 쿼리 예(의도만): 월별 `count(*) where route='vendor'`, `sum(audio_duration_ms) where route='vendor'`, `p95(latency_ms)`.

---

## 하이브리드 STT — 파일럿 KPI (빈칸)

| 지표 | 목표/구간 (가정) | 측정 방법 | **근거** |
|------|------------------|-----------|----------|
| 상용 STT 호출 비율 (%) | | 로그 카운트 | |
| 평균 인식 지연 (ms) | | | |
| 사투리·저신호 구간 WER / 주관 평가 | | | |

---

## 메타

- **schema:** `silver_tech_cogs_unit_economics_template_v1`
- **last_updated_utc:** 2026-05-15 — STT 라우팅 감사 로그 **jsonschema v1** 레포 고정(본 문서 표는 스키마 요약).
