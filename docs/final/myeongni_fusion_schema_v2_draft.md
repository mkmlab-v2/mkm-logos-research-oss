# 명리 융합 결정 JSON 스키마 — 사람이 읽는 초안 (v2 draft)

**SSOT(JSON)**: `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json`  
**코드 스펠링**: 구현·ledger는 **MYEONGRI**; 매니페스트·노트북 표기는 **MYEONGNI_FUSION_DECISION_JSON_SCHEMA** 라벨과 병기.  
**저장 형식**: JSON Lines — 한 줄에 JSON 객체 하나. 경로 예: `projects/bitcoin-trading/memory/v2/ledger/myeongri_decision_ledger_YYYYMMDD.jsonl`

---

## 1. 목적

- **명리·융합** 관련 의사결정을 ledger에 **append-only**로 남긴다.
- 각 줄은 **최소 필수 필드**(`ts_utc`, `fact_lock`)를 만족해야 쓰기기(Writer)가 허용한다.

---

## 2. 필수 필드

| 필드 | 타입 | 의미 |
|------|------|------|
| `ts_utc` | string (date-time) | ISO-8601 UTC. 생략 시 Writer가 기본값 채움. |
| `fact_lock` | object | `build_fact_lock(project_root)` 스냅샷 또는 호출자 제공 객체. 비가용 시 에러 스텁 허용(`additionalProperties: true`). |

---

## 3. 선택 필드

| 필드 | 타입 | 의미 |
|------|------|------|
| `slice_id` | string | 퓨전 슬라이스·레짐 게이트 등 구간 ID. |
| `run_id` | string | 실행 상관 ID. |
| `decision_id` | string | 의사결정 ID(`run_id`와 동일할 수 있음). |
| `ledger_join_key` | string | ledger 조인에 쓰는 필드명(예: `run_id`). |
| `stub` | string 또는 boolean | 실험·스텁 태그. |

루트 객체는 **`additionalProperties: true`** — 확장 필드 허용.

---

## 4. 구현 앵커

- Writer: `append_myeongri_decision_ledger()` — `projects/bitcoin-trading/ops/v2/memory/decision_ledger.py`
- 구현·경로 **팩트**: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §6과 정합 유지.

---

## 5. NotebookLM 사용 시

- B 노트북에는 동명의 **JSON 파일** 또는 본 MD·텍스트로 그라운딩 가능.
- 본 MD는 스키마 **설명층**; 기계 검증은 반드시 **SSOT JSON**을 따른다.

---

**작성일**: 2026-03-29  
**상태**: draft — JSON SSOT 변경 시 본 파일 동기 갱신.
