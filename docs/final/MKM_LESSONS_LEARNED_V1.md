# MKM 교훈 인덱스 v1 (반복 시 NO_GO 클래스)

**역할:** 에이전트·지휘관이 **같은 계열의 실수를 반복하지 않기 위한** 짧은 금지령 모음이다.  
**성격:** 구현 경로·수치의 단일 진실(SSOT)이 **아니다**. 팩트·경로·게이트 판정은 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`, `docs/final/artifacts/*.json`, 호출 가능 스크립트가 우선한다.

**갱신:** 새 반복 장애 클래스가 SSOT로 고정되면 행을 추가하고, 만료된 금지는 삭제하거나 `[DEPRECATED]`로 표시한다.

---

## 스키마

| 필드 | 의미 |
|------|------|
| **사건 ID** | 고정 식별자 (`FAIL-*`). |
| **실패 좌표** | 레이어·도메인 (Rail / SSOT / Regime / Compression / Git / Medical-corpus 등). |
| **금지령** | 같은 패턴이 보이면 **즉시 중단·재검증**할 행위. |
| **근거 SSOT** | 레포 문서·규칙·산출물 포인터. |

---

## 5건 — 반복 시 사실상 NO_GO (운영·브리핑 공통)

| 사건 ID | 실패 좌표 | 금지령 | 근거 SSOT |
|---------|-----------|--------|-----------|
| **FAIL-SSOT-001** | SSOT / 브리핑 | 기획서·NotebookLM·헌법 문서만 보고 **「코드에 이미 구현」「이미 통과」**를 단정한다. | `AGENTS.md` (구현 팩트), `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.1·목적 |
| **FAIL-RAIL-002** | Rail / 승격 | B-track·연구·Hub B·스왐 메트릭 결과를 **승인·체크리스트 없이** 실매매·본선 OOF·올그린·프로덕션 게이트에 **자동 합선**한다. | `AGENTS.md` (B-track 금지·격벽), 동 CONSTITUTION §13.1·연구 레인 |
| **FAIL-REGIME-003** | Regime / Field | **2차 성경 레짐**을 실전 시그널·트리거에 쓰거나, 레짐을 **안정/주의/위험 3단만**으로 끝낸다. | `.cursor/rules/regime-field-constitution.mdc` (NEVER), 1차 `regime_map`·코드북 분리 원칙 |
| **FAIL-COMP-004** | Compression / 측정 | **일반 레일** 9케이스·KPI·도메인 가드 스윕과 **V2 극복원(ultra-literal 등)** 산출을 **한 그릇으로 섞어** “상용 GO”를 말하거나, **`docs/final/artifacts` 갱신 없이** 압축 성과를 단정한다. | `docs/final/CURRENT_OPS_SNAPSHOT.md` (압축 이원), `docs/final/COMPRESSION_SLA_POLICY_V1.md`, `realistic_quality_sweep_v1.json` 등 NO_GO 실측 |
| **FAIL-GIT-005** | Git / 추적 | `.git/info/exclude`에 `scripts/`·`tools/` 등을 **무방지(`!` 예외 없이)** 넓게 막아 **추적 파일이 조용히 제외**되게 한다. | `AGENTS.md` (Git 로컬 exclude 경고), `scripts/Verify-GitWorkspaceSanity.ps1` |

---

## 선택 교훈 (도메인 특화)

| 사건 ID | 실패 좌표 | 금지령 | 근거 SSOT |
|---------|-----------|--------|-----------|
| **FAIL-MED-006** | Corpus / 한의 | 라벨 코호트 **A**와 원전·Proxy 말뭉치 **B**를 **본선 분류·204 OOF**와 자동 합선한다. | `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` |

*(v1에서는 상단 5건을 우선 숙지한다.)*

---

## SSOT 교차 링크 (얇은 인덱스)

| 사건 ID | 관련 문서·산출 (추가 조회) |
|---------|---------------------------|
| FAIL-SSOT-001 | `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 목차·§1.1 |
| FAIL-RAIL-002 | 동 문서 §13.1, `AGENTS.md` B-track |
| FAIL-REGIME-003 | `data/regimes/regime_map.json`(존재 시), `regime-field-constitution.mdc` |
| FAIL-COMP-004 | `COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1.md`, `CURRENT_OPS_SNAPSHOT.md` 압축 절, `realistic_quality_sweep_v1.json` 등 artifacts |
| FAIL-GIT-005 | `Verify-GitWorkspaceSanity.ps1` |
| FAIL-MED-006 | `KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` |

---

## 에이전트 기동 시 권장

1. 작업 전: `@docs/final/CURRENT_OPS_SNAPSHOT.md` + (필요 시) 본 파일 5행 스캔.  
2. 구현·게이트: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` + 해당 `artifacts/*.json`.  
3. 본 인덱스와 CONSTITUTION이 충돌하면 **CONSTITUTION·산출물**이 이긴다.
