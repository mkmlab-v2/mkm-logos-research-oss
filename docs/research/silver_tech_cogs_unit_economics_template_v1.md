# Silver Tech — COGS / unit economics (v1, `[HYPO]`)

**역할:** 내부 단가·부하 **가정만** 담는 표. `TRACK_C`·`PUBLIC_FACING` 본문에 **숫자 올리기 전** 여기서 채우고, 출처·실측 붙으면 승격. 대외·조달에는 **견적·로그·계약 인용 없이** 단가 문구 금지.

**연계:** `RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-009** · `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.7.2.

---

## Fact-Lock 순서

1. 아래 **COGS 표** 채움 + **근거·출처** 열 (벤더 콘솔·견적·자체 벤치).
2. **하이브리드 STT:** 로컬/온디바이스 1차 → 게이트 통과 시만 상용 API.
3. 소규모 실측 → 월 COGS **구간** → 그다음에만 대외·Track C 본문 수치 검토.

**체크리스트:** [~] COGS 출처 URL(공개 가격표만; 단가·월액 미기재) · [x] STT 감사 로그 **jsonschema v1** (`stt_routing_audit_log_v1`·예시·pytest) · [ ] 월 합계 시나리오 **S-CONS / S-BASE / S-STRESS** 이름으로 2~3벌 저장.

**공개 참고 링크:** [Speech-to-Text pricing](https://cloud.google.com/speech-to-text/pricing) · [Vertex Gemini pricing 개요](https://cloud.google.com/vertex-ai/generative-ai/pricing) (본 레포 비용 아님).

---

## COGS 라인 (가정)

| 라인 | 단가/월상한 | 단위 | 월사용량 | 월소계 | 근거·출처 | 비고 |
|------|-------------|------|----------|--------|-----------|------|
| STT 로컬/자체 | | | | | | GPU·VPS·전력 |
| STT 상용(업그레이드 경로) | | | | | 위 공개 링크(견적·발주로 교체) | 트리거 % 별도 |
| LLM·요약 | | | | | | |
| 푸시/SMS/통화 | | | | | | |
| 스토리지·백업 | | | | | | |
| 서버·대역 | | | | | | |
| 운영(FTE 환산) | | | | | | |
| 법무·감사 보관 | | | | | | |
| **합계** | — | — | — | | | 시나리오 라벨: |

**시나리오:** `S-CONS`(보수) · `S-BASE`(기준) · `S-STRESS`(피크) — 동일 표 복제 2~3벌.

---

## 하이브리드 STT — 감사 로그 (SSOT)

**Normative:** `docs/final/schemas/stt_routing_audit_log_v1.schema.json` · `docs/final/schemas/stt_routing_audit_log_v1.minimal.example.json` · `tests/test_stt_routing_audit_log_schema_v1.py`. **금액·견적은 로그에 넣지 않음.**

요약: 필수 `schema_version`, `event_id`, `occurred_at_utc`, `route`(`local`|`vendor`|`rejected`), `audio_duration_ms`, `pii_redaction`. 선택 `session_id`, `provider`, `latency_ms`, `error_code`, `confidence`, `chars_out`, `billing_unit`, `hypothesis_tag`.

**집계 의도(예):** 월별 `route='vendor'` 건수·`sum(audio_duration_ms)`·`p95(latency_ms)`.

---

## 파일럿 KPI (가정)

| 지표 | 목표/구간 | 측정 | 근거 |
|------|-----------|------|------|
| 상용 STT 비율 % | | 로그 카운트 | |
| 평균 지연 ms | | | |
| 저신호·사투리 품질 | | WER 또는 주관 | |

---

## 메타

- **schema:** `silver_tech_cogs_unit_economics_template_v1`
- **last_updated_utc:** 2026-05-15 — 본문 슬림; STT 필드는 **스키마**가 단일 진실.
