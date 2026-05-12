# LoRA 1팩 v0 — Definition of Done (DoD) v1.2

**상태:** v1.2 — Pack 0-B **스키마·prep CLI·축소 픽스처·pytest·P0·CI** 앵커 완료; **N=1000 / K=100 전량 JSONL**은 bulk 생성 PR로 잔여.  
**Fact-Lock:** 구현·경로·통과 여부는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·호출 가능 스크립트·`pytest` exit code·산출 JSON만 근거로 한다.

---

## 0. PM 고정 결정 (본 문서의 전제)

**v0 학습 타깃(정답 레일) 고정:** **명리 만세력/사주 엔진의 결정론적·구조화 출력(JSON)** — 동일 입력(출생 순간·IANA TZ 등 엔진 계약)에 대해 **재현 가능한 필드 집합**을 `expected`로 둔 JSONL. 자연어 “풀이”만 단독 정답으로 쓰지 않는다.

**v0에서 학습 정답으로 쓰지 않는 것(명시 제외):** M31 호르몬 트렌드·`rag_metabolism`*·게마트리아 감사 꼬리표 등 **비생물학적 메타포·감사 지표** — Track C/감사·연구 레인 입력은 가능하나, **LoRA v0의 supervision 타깃으로는 채택하지 않음**(`track_wall`·Fact-Lock 정합; 임상·뇌·장 단정 회피).

---

## 0.1 Pack 0-B 상수 (v1.1 확정)

| 키 | 값 | 의미 |
|----|-----|------|
| **스키마 파일명 (SSOT)** | `docs/final/schemas/myeongri_deterministic_lora_golden_set_v1.schema.json` | JSONL **한 행(row)** 검증용 스키마 (**디스크 존재**, `verify_p0` 포함). |
| **N** | **1000** | **학습에 사용하는** 결정론적 골든 Input–Output 쌍의 **최소 행 수**(`split=train` 또는 동등 디렉터리 규약). **현재 레포 샘플은 1행(train)만 — bulk 미달**. |
| **K** | **100** | 학습 파이프라인에 **절대 혼입하지 않는** 홀드아웃·`locked_eval` **최소 행 수**. **현재 샘플은 1행(locked_eval)만 — bulk 미달**. |

**split 메모:** `train`(≥N) / `validation`·`test`(prep PR에서 비율·seed 고정) / 홀드아웃(≥K) — 전체 행 수는 prep이 정의하되, **출하 DoD 최소선은 N·K만 채우면 됨**.

---

## 1. “이미 디스크에 있는 LoRA 팩”과의 관계 (착각 방지)

레포에 **이미 고정된 별도 라인**이 있다: **MKM Control-Integrity Golden / LoRA (B-track, instruction eval)**.

| 구분 | 식별명 | SSOT | 비고 |
|------|--------|------|------|
| **Pack 0-A (기존·디스크 팩트)** | Control-Integrity LoRA | `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` **§1.2.1** | Golden 행은 `mkm_control_integrity_golden_set_v1` 스키마(`prompt` / `expected_response` 등). **명리 JSON·M31과 무관한 지시 준수 벤치**. |
| **Pack 0-B (본 DoD의 v0 신규 축)** | Myeongri deterministic LoRA v0 | **본 문서** + `myeongri_deterministic_lora_golden_set_v1.schema.json` | 정답=§0 고정, 상수=§0.1. Prep: `scripts/prep_myeongri_deterministic_lora_golden_v1.py`. |

**Pack 0-A 출하(이미 문서화된 최소 DoD):**

- P0 경로에 스크립트 존재: `scripts/verify_p0_constitution_gate_paths.ps1`가 §1.2.1 표 경로와 정합.
- 회귀: `py -m pytest tests/test_mkm_control_integrity_pipeline_smoke_v1.py` **exit 0**.
- (실학습 호스트) 프로모션: `scripts/check_mkm_control_integrity_promotion_gate_v1.py` 산출 `reports/mkm_control_integrity_promotion_gate_latest.json`에서 **decision=GO** 및 정책 문서화된 임계와 일치.

**Pack 0-B(v0 명리 축)**는 위 파이프라인을 **복제·병합하지 않고**, 별도 JSONL 스키마·prep·pytest를 추가하는 것이 DoD다.

---

## 2. Pack 0-B — LoRA v0 (명리 결정론 JSON) DoD 체크리스트

### 2.1 데이터 (Data)

- [x] **입력 계약**이 한 줄로 고정됨: `birth_instant_utc` + `iana_tz` (+ 선택 `is_male`) — 스키마·`prep_myeongri_deterministic_lora_golden_v1.py`·`run_saju_global_birth_v1.py`와 동일 계열.
- [x] **정답 계약**이 JSON Schema로 고정됨: **`docs/final/schemas/myeongri_deterministic_lora_golden_set_v1.schema.json`**.
- [x] **JSONL** 생성 파이프라인이 스크립트로 재현됨: **`scripts/prep_myeongri_deterministic_lora_golden_v1.py`** (`full_saju`에서 `calculated_at` 제거).
- [ ] **split**이 결정론적이며 **전 split**이 bulk로 기록됨 — 샘플 픽스처만 존재; seed·버전 필드는 bulk PR에서 필수.
- [ ] **규모 DoD:** `train` **≥ 1000**행, 홀드아웃·`locked_eval` **≥ 100**행 — §0.1 (**현재 미달**).

### 2.2 게이트 (Gate / pytest)

- [x] **스키마 검증**: `py -m pytest tests/test_myeongri_deterministic_lora_golden_set_schema_v1.py` — 픽스처 +`build_golden_row_dict` 정합.
- [x] **엔진 정합**: 픽스처 1행과 `build_golden_row_dict` 재계산의 `expected_result` 동일.
- [x] **합선 금지 테스트**: 픽스처에 M31류 키워드 부재(`test_forbidden_supervision_keys_absent`).

### 2.3 학습·산출 (Train / Artifacts)

- [ ] **프로파일**: Pack 0-B 전용 profile 키 또는 별도 profiles JSON 존재 (**Pack 0-A JSON을 복제해 키만 바꾸는 것은 금지** — 합선 위험).
- [ ] **어댑터 경로·이름**이 한 줄 SSOT로 기록됨 (실제 경로는 PR에서 확정).
- [ ] **평가 리포트** JSON이 `reports/` 규약에 남고, **K 세트**에 대한 스키마·필드 정합 지표가 재현 가능.

### 2.4 서술·대외 (Copy / risk)

- [ ] 대외·내부 브리프에 **“뇌신경·장내미생물·호르몬 치료 효능”** 단정 없음 — `docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md`·`PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` 정렬.

---

## 3. “언제 끝나나”에 대한 유일한 답 (일정이 아니라 DoD)

**캘린더 날짜는 SSOT가 아니다.** 진도는 **§2 체크박스가 true가 되는 순서**로만 측정한다.  
우선순위: **Pack 0-A 회귀가 항상 녹색** → **Pack 0-B 스키마+prep+pytest 최소 세트** → **N/K bulk** → 학습·평가·(선택) 프로모션 게이트.

---

## 4. 다음 액션 (v1.2 이후)

1. Architect: **seed 고정 bulk JSONL** 생성( train≥1000 · locked_eval≥100 ) + `split`·`dataset_version` 메타.  
2. Sentinel: 대용량 JSONL은 `.gitignore` 또는 Vault 규약에 맞추고, 레포에는 **생성 스크립트·소표본·해시 매니페스트**만 유지할지 정책 확정.  
3. 지휘관: N/K 변경 시 **§0.1만** 개정 후 커밋.

---

## 5. 근거 경로 (Librarian 스냅샷)

```json
{
  "evidence_path": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §1.2.1·Pack 0-B 보강; docs/final/LORA_PACK_V0_DOD_V1.md; docs/final/schemas/myeongri_deterministic_lora_golden_set_v1.schema.json; scripts/prep_myeongri_deterministic_lora_golden_v1.py; tests/test_myeongri_deterministic_lora_golden_set_schema_v1.py",
  "validated_at": "2026-05-13",
  "confidence_level": "A",
  "note": "N/K bulk 미달 — 샘플·게이트만 충족."
}
```
