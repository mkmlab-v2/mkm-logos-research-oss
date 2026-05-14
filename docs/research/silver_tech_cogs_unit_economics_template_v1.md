# Silver Tech — COGS / unit economics (v1, `[HYPO]`)

**역할:** 내부 단가·부하 **가정만** 담는 표. `TRACK_C`·`PUBLIC_FACING` 본문에 **숫자 올리기 전** 여기서 채우고, 출처·실측 붙으면 승격. 대외·조달에는 **견적·로그·계약 인용 없이** 단가 문구 금지.

**연계:** `RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-009** · `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.7.2.

---

## Fact-Lock 순서

1. 아래 **COGS 표** 채움 + **근거·출처** 열 (벤더 콘솔·견적·자체 벤치).
2. **하이브리드 STT:** 로컬/온디바이스 1차 → 게이트 통과 시만 상용 API.
3. 소규모 실측 → 월 COGS **구간** → 그다음에만 대외·Track C 본문 수치 검토.

**체크리스트:** [x] COGS 출처 URL(공개 가격표만; 단가·월액 미기재) — 아래 표 **근거·출처** 열에 링크·경로 고정 · [x] STT 감사 로그 **jsonschema v1** (`stt_routing_audit_log_v1`·예시·pytest) · [x] 월 합계 시나리오 **S-CONS / S-BASE / S-STRESS** 이름·정의 고정(수치는 실측·견적 후 같은 표 복제 권장).

**공개 참고 링크:** [Speech-to-Text pricing](https://cloud.google.com/speech-to-text/pricing) · [Vertex Gemini pricing 개요](https://cloud.google.com/vertex-ai/generative-ai/pricing) (본 레포 비용 아님).

---

## COGS 라인 (가정)

| 라인 | 단가/월상한 | 단위 | 월사용량 | 월소계 | 근거·출처 | 비고 |
|------|-------------|------|----------|--------|-----------|------|
| STT 로컬/자체 | — | — | — | — | `docs/final/schemas/stt_routing_audit_log_v1.schema.json` (`route=local`); 호스트 단가·전력은 비추적 `docs/final/LOCAL_MACHINE_POINTER_V1.md`·`docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`(VPS 역할) | GPU·VPS·전력은 **실측·청구서**로만 채움 |
| STT 상용(업그레이드 경로) | — | — | — | — | [Google Speech-to-Text pricing](https://cloud.google.com/speech-to-text/pricing); 감사 집계 의도는 본 문서 §하이브리드 STT | 견적·발주서로 교체 시 URL 대체 |
| LLM·요약 | — | — | — | — | `docs/final/P0_COMMERCIALIZATION_TRACKER.md`(Track A·계량)·`CLAUDE.md` 「Gemini 멀티모달: MCP vs 배치 CLI」; 배치 `scripts/gemini_multimodal_batch.py` | 키·단가는 `.env`/벤더 콘솔; 레포에 비밀 미기재 |
| 푸시/SMS/통화 | — | — | — | — | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`(웹훅·알람 행 검색)·루트 `.env.example` 변수명만 | 실제 과금은 공급사 계약 |
| 스토리지·백업 | — | — | — | — | `scripts/bootstrap_agent_search_datastore_gcs_v1.py`(문서·CONSTITUTION GCS/Agent Search 절); Vault 경로는 `AGENTS.md`·`docs/NotebookLM_sources_manifest.md` | G: Vault 마운트 시에만 공유 SSOT |
| 서버·대역 | — | — | — | — | `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` · `projects/bitcoin-trading/AGENTS.md`(PM2·cwd) | 대역·트래픽은 호스트 모니터링 |
| 운영(FTE 환산) | — | — | — | — | 내부 인건비; 레포 SSOT 아님 | 제안서·조달에는 **FTE 단가 미기재** 권장 |
| 법무·감사 보관 | — | — | — | — | `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` §3 · `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.7.2 · `RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-009** | **(D)** 법무 확정 전 본문 수치·면책 동결 금지 |
| **합계** | — | — | — | — | 아래 **시나리오** 라벨 붙여 동일 표 2~3벌 복제 후 월소계만 채움 | 시나리오 라벨: |

**시나리오:** `S-CONS`(보수) · `S-BASE`(기준) · `S-STRESS`(피크) — 동일 표 복제 2~3벌.

### 시나리오 정의 (v0 · 수치 TBD)

| 라벨 | 정의 (한 줄) | COGS에 반영할 가정 축 |
|------|----------------|------------------------|
| **S-CONS** | 상용 STT·클라우드 LLM 호출을 **최소**로 두었을 때 | `route=local` 비중↑, 벤더 분·토큰 상한 보수값 |
| **S-BASE** | 제품 기본 경로·현재 게이트를 그대로 탔을 때 | 실측 30일 평균(또는 파일럿) 기준 |
| **S-STRESS** | 피크일·장애 시 백업 라우트까지 켰을 때 | `route=vendor`·재시도·대용량 오디오 피크 |

---

## Stream 2 — 로컬 실측 루프 (감사 JSONL, 비커밋)

산출 기본 경로는 루트 **`reports/`** (`.gitignore`의 `reports/**` — 로컬·재현용; 본선 동결 아티팩트와 혼동 금지).

**운영(프로덕션) 적재:** 호스트별 JSONL 경로·월 롤업은 **레포 밖** 운영 규약으로 둔다(`docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`·`AGENTS.md`). 이 문서의 **COGS 월소계**는 벤더 청구서·운영 집계가 확보된 뒤 같은 표를 S-CONS/BASE/STRESS 복제본에만 숫자로 채운다.

```text
py scripts/append_stt_routing_audit_log_v1.py --route local --audio-ms 1200 --pii-redaction not_applicable --hypothesis-tag "[HYPO]"
py scripts/append_stt_routing_audit_log_v1.py --route vendor --audio-ms 3400 --provider google_stt --latency-ms 420 --pii-redaction redacted_full --hypothesis-tag "[HYPO]"
py scripts/summarize_stt_routing_audit_log_v1.py
```

스키마만 확인할 때는 각 행 앞에 `--dry-run`으로 stdout 한 줄 JSON 검증. **COGS 표의 월소계·금액**은 여전히 청구서·실측 후에만 채움(위 루프는 **감사 필드·집계 파이프** 검증용).

---

## 하이브리드 STT — 감사 로그 (SSOT)

**Normative:** `docs/final/schemas/stt_routing_audit_log_v1.schema.json` · `docs/final/schemas/stt_routing_audit_log_v1.minimal.example.json` · `tests/test_stt_routing_audit_log_schema_v1.py`. **금액·견적은 로그에 넣지 않음.**

요약: 필수 `schema_version`, `event_id`, `occurred_at_utc`, `route`(`local`|`vendor`|`rejected`), `audio_duration_ms`, `pii_redaction`. 선택 `session_id`, `provider`, `latency_ms`, `error_code`, `confidence`, `chars_out`, `billing_unit`, `hypothesis_tag`.

**집계 의도(예):** `py scripts/summarize_stt_routing_audit_log_v1.py` → `reports/stt_routing_audit_log_v1_summary_latest.json` — `vendor_share_by_event_pct`, `vendor_latency_ms_avg`, `vendor_latency_ms_p95`, `route_counts`, `audio_duration_ms_sum` / `audio_duration_ms_by_route`, `occurred_at_utc_earliest`·`latest`. 월별 창은 요약 JSON을 주기적으로 덮어쓰거나(전체 JSONL 롤업) 별도 월 필터 스크립트로 확장.

---

## 파일럿 KPI (가정)

| 지표 | 목표/구간 | 측정 | 근거 |
|------|-----------|------|------|
| 상용 STT 비율 % | — (법무·제품 합의 후) | 월별 `stt_routing_audit_log`에서 `route=vendor` / 전체 건수; 집계 스크립트는 레포 미고정 시 수동 CSV | §하이브리드 STT 집계 의도 · `TRACK_C` §3.7.2 **파일럿 KPI 동결 지연** |
| 평균 지연 ms | — | 동일 로그 `latency_ms` 평균·p95 | `stt_routing_audit_log_v1.schema.json` 필드명 고정 |
| 저신호·사투리 품질 | — | WER 벤치 또는 휴먼 샘플링; **대외 단정 금지** | `[HYPO]`; `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` §3 경계 |

---

## 메타

- **schema:** `silver_tech_cogs_unit_economics_template_v1`
- **last_updated_utc:** 2026-05-14 — §Stream 2 로컬 append×2 + summarize 재실행; **운영 JSONL**은 레포 밖·COGS 숫자는 청구서 후 동일 표 복제본에만; COGS·KPI **금액·목표 수치**는 실측·법무(RQ-009) 후.
