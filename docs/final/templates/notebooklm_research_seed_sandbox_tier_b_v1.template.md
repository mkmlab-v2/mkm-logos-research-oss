# NotebookLM Research Seed — NL_RESEARCH_SANDBOX · Tier B Dynamic (v1)

**schema:** `notebooklm_research_seed_v1`  
**target_notebook:** `NL_RESEARCH_SANDBOX` · uuid `47ffa7da-9bd1-460b-8cac-48361715e48d` · MCP `14-universal-lexicon-dr`  
**tier:** `B_dynamic`  
**research_mode:** `sandbox_only`  
**export_allowed:** `draft_only`  
**ingest_gate:** `external_source_review`  
**data_lane:** `external_web_sandbox`  
**promotion_status:** `draft` · `research_only` · `[HYPO]`

**목적:** Google NL 2026-06 자율 웹검색·Antigravity 산출의 **유일한 오염 격리 구**. Core 5·Track A·실매매 레인으로 **자동 이관 금지**.

---

## 메타

| 필드 | 값 |
|------|-----|
| `seed_id` | `sandbox_YYYYMMDD_<topic_slug>` |
| `promotion_target` | `EVENT_<slug>` / `TRACKC_BIZ` / `06_스마트팜_*` / *(없음=아카이브만)* |
| `event_ttl_days` | 30 (기본) |

---

## 샌드박스 규칙 (하드)

1. 이 노트에 **레포 SSOT 원본 전체**를 올리지 않는다 — 시드 1파일·질문만으로 시작 가능(Google 신기능).
2. NL이 제안한 웹 소스는 **전량 자동 add 금지** — 운영자가 행별 승인.
3. 승인 소스를 Tier A 노트(`MKM_CORE_FACT`·`OPS_COMMAND`·`COMPRESSION_BTRACK`)로 **복사 add 금지**.
4. 예언·가격·적중률·BTC/KOSPI 방향 **단정 금지** — 예언 전용 시드는 Phase 2.
5. Antigravity 코드 = 탐색·초안; `scripts/*.py`·pytest = 최종 판정.

---

## [RESEARCH]

**시드 질문 (주제를 한 줄로):**

> _(예: OpenData 327 과제① 경쟁사·유사 과제 사례 5건 — 방법론·일정만, 성과 수치 단정 금지)_

**NL 자율 검색 요청 문구 (복붙):**

```
다음 주제에 대해 Google Search로 고품질 1차·2차 자료를 찾아 제안하라.
각 후보에 (1) 제목 (2) URL (3) 관련 이유 (4) 한계를 적어라.
나는 승인한 소스만 노트에 추가한다.
가격 예측·의료 효능·압축률·실매매 수익 주장은 금지.
```

**승인 로그 (표):**

| approve? | title | url | lane_tag | note |
|----------|-------|-----|----------|------|
| | | | `external_web` | |

저장: `reports/nl_research_traces/sandbox_<seed_id>.md`

---

## [ANALYZE]

- 승인 소스 + (선택) 레포 **포인터 1파일**만 `add_source`.
- 출력: 요약 · 갈등점 · `unverified` 목록 · **이관 후보 노트 1개** (`promotion_target`).

---

## [PRODUCE]

- 허용: md 초안 · 비교 표 초안 — **pptx/xlsx는 promotion_target 노트에서 재생성 권장**.
- 저장: `reports/nl_exports/NL_RESEARCH_SANDBOX/<seed_id>/`

---

## [INGEST] — Tier B 이관 게이트

이관 전 **전부** 확인:

- [ ] `promotion_target`이 Tier A Core 5가 **아님**
- [ ] 이관 소스 ≤ 5건·동일 `data_lane`
- [ ] `PUBLIC_FACING`·Track A·FAIL-COMP-004 충돌 없음
- [ ] 이관 후 샌드박스 소스 **prune** (선택·권장)

이관 완료 시: `py scripts/athena_checkpoint.py "NL sandbox → <target> 이관 <n>소스 research_only"` (선택)

---

## inherit 템플릿

Track C·스마트팜·EVENT 시드는 본 샌드박스 규칙 **상속** + 각 템플릿 금지어 추가.
