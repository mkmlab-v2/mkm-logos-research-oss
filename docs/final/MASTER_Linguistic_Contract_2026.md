# MASTER Linguistic Contract 2026

**작성일**: 2026-03-31  
**목적**: 어휘·아톰·외부 사전·코퍼스 범위를 FACT-LOCK으로 고정한다. 비유·내러티브·목표 수치를 산출물(FACT)로 혼동하지 않는다.  
**상태**: 초안(활성). 외부 어휘 파일이 확보되기 전까지 **파일명·해시·행 수는 `TBD`**.

---

## 1. SSOT 우선순위 (읽는 순서)

1. **공유 드라이브(1순위)**: `G:\공유 드라이브\MKM_DATA_VAULT\vault\btrack_artifacts_verified` — 현행 B-track 실측 아티팩트(마스터 아톰 요약·게이트 등).
2. **공유 드라이브(외부 어휘, 1순위 확장)**: `G:\공유 드라이브\MKM_DATA_VAULT\vault\external_lexicon` — 승격된 외부 사전 스냅샷·라이선스·매니페스트(아래 §5).
3. **로컬 작업 루트**: `C:/workspace` — 개발·재생성·테스트. 로컬 단독으로 “전역 최신 확정”을 선언하지 않는다.

승격 스크립트:

- B-track 산출물: `scripts/push_local_artifacts_to_vault.ps1`
- 외부 어휘 스테이징 → G:: `scripts/push_external_lexicon_to_vault.ps1`

---

## 2. 용어 정의 (Definition Lock)

| 용어 | 정의 | 비고 |
|------|------|------|
| **Atom (내부)** | `scripts/core/build_original_language_master_atoms.py`가 생성하는 고유 단위. 현행 규칙은 요약의 `lemma_method` 필드(예: `normalized_form_v1`, `heuristic_lemma_v2`)로 식별한다. | “의미 원자 완성”이 아님. pseudo-lemma / 정규화 한계는 요약 JSON `note`를 따른다. |
| **Lemma (외부 참조)** | OpenScriptures / STEP / 기타 **확정 스냅샷**의 레마·형태 정보. 내부 `atom_id`에 **부가되는 참조 레일**이다. | 내부 SSOT 키를 Strong 등으로 대체하지 않는다. |
| **Corpus scope (운영)** | **Enriched DSS+**를 기본 전제로 한다: 정경 디코드·사해·외경 등 빌드 입력에 명시된 파일 집합(마스터 아톰 요약 `inputs` 배열이 사실상의 코퍼스 지문). | “66권만” 벤치가 필요하면 별도 `corpus_tag=canon_only` 실험으로 분리한다. |

**금지**: 실제 파일·해시 없이 문서에 **가짜 SHA-256, 가짜 경로, 가짜 행 수**를 FACT처럼 적는 것.

---

## 3. 이중 레일 (Dual-Rail) 원칙

- **내부 레일**: `atom_id` 및 마스터 아톰 카탈로그 — 외부 사전이 없어도 파이프라인이 동작해야 한다.
- **외부 레일 A (정렬·형태소)**: 확정된 오픈/라이선스 스냅샷으로 lemma·형태 매핑 테이블을 유지한다. (후보: OpenScriptures/STEP 계열 — **확정 시 본 문서 §6 테이블 갱신**)
- **외부 레일 B (감사·호환)**: Strong 등 전통 번호 체계 — 외부 문헌·레거시 스크립트와의 교차검증용. 단독 진실(SSOT)로 고정하지 않는다.

---

## 4. 현계 FACT (2026-03-31 기준)

- **실측 카탈로그**: 마스터 아톰 요약 `stats.unique_master_atoms` — 로컬 최신 재생성(`original_language_master_atoms_summary_latest.json`) 기준 **41,769** (예: 2026-03-30 UTC). **41,751**은 이전 스냅샷·문서 초안에 기재된 값이며, **동일 파이프라인을 재실행한 현재 워크스페이스 SSOT는 요약 JSON의 수치를 따른다.** 공유 vault 승격본과 불일치 시 **vault(§1) 우선**으로 재확인한다.
- **앵커 매트릭스 스케일**: `btrack_anchor_matrix_latest.json`의 `rows`는 **14** — “14만 앵커” 등 **다른 스케일 주장은 별도 아티팩트 정의가 없으면 FACT가 아님**.
- **14,197**: 저장소/승격 아티팩트에 **삼출 근거 없음** — 설계·기억·외부 체계 유사치는 **[HOLD]**만 허용.

---

## 5. 외부 어휘 스테이징 및 승격 규약

**로컬 스테이징**: `C:\workspace\vault\external_lexicon\`

필수 동봉(파일이 생기면):

- `MANIFEST.json` — `source_url`, `retrieved_at_utc`, `license_spdx_or_note`, `files[]` 각각에 대한 **`sha256`**, 상대 경로.
- `LICENSE` 또는 `NOTICE` — 재배포 조건 준수.

**공유 승격 경로**: `G:\공유 드라이브\MKM_DATA_VAULT\vault\external_lexicon\`

- 스크립트: `scripts/push_external_lexicon_to_vault.ps1` (스테이징 전체 트리 복사 + `_push_summary_lexicon_latest.json` 기록).
- 자동 보급: `scripts/setup/fetch_external_lexicons.ps1` — 원격 3종 클론/갱신, `MANIFEST.json`(SHA-256) 생성, 끝에서 위 승격 스크립트 호출. `STEPBible/STEPBible-Data`는 Windows 초장경로 실패를 피하려 `core.longpaths=true` + **sparse-checkout**으로 `Lexicons`, `Morphology codes`, `Versification`, `Proper Nouns`, `Translators Amalgamated OT+NT`만 작업 트리에 둔다(루트 메타는 `_extracted_repo_root/`에 `git show`로 추출).

`MANIFEST.json`이 없으면 승격을 **실패**시키는 것이 바람직하나, 초기 도입 단계에서는 스크립트가 경고만 하고 복사할 수 있다. **CI 도입 시 실패로 승격**한다.

---

## 6. 외부 테이블 확정 테이블 (TBD — 확보 후 기입)

| 항목 | Primary (후보) | Audit (후보) | 확정 파일 | SHA-256 | 확정일(UTC) |
|------|----------------|-------------|------------|---------|-------------|
| Lemma / Morph | OpenScriptures/STEP (TBD) | Strong’s compatible table (TBD) | TBD | TBD | TBD |

---

## 7. 검증 계약 (Validation)

- 모든 신규 아티팩트는 **입력 파일 목록 + 버전 + 해시**를 요약 JSON에 포함한다.
- **Coverage metric (예시)**: 내부 아톰 중 외부 lemma 레일에 성공 매핑된 비율 — 임계값은 별도 스크립트·PR에서 정한다.
- **예측·복원율·특정 구절 마진**: 재현 가능한 리포트가 없으면 **[HOLD]**로만 기록한다.

### 7.1 Lexicon coverage rails (IDs and scope)

레포트·요약 JSON에서 **동일 rail id**로 누적·병합한다. 각 레일의 “성공 매칭” 정의는 해당 매퍼 산출물의 필드 의미로 고정하고, 요약에서는 **`by_rail.<rail_id>`**만 참고한다.

| Rail id | 입력·범위 | 성공 매칭(요약) | DSS·비정경 |
|---------|-----------|------------------|------------|
| **`rail_strongs_seed`** | OpenScriptures Strong’s Greek/Hebrew XML (`map_master_atoms_lexicon_seed.py` 등) | 인덱스에서 **후보 1개 이상**이 붙은 아톰(다중 후보는 `ambiguous_*`로 분리 가능) | 코퍼스는 마스터 아톰 `inputs`와 동일; Strong 자체는 언어 사전이다. |
| **`rail_morphhb`** | OpenScriptures **morphhb** `wlc/*.xml`(OSIS `w`의 `lemma`, `morph`, 표면) — **MT/WLC 계열 정경 본문 정렬** | 히브레우 아톰에 대해 WLC 기반 **lemma/Strong 후보**가 연결된 경우(세부 필드는 매퍼 스키마) | **DSS 전용 복원·별 코퍼스 비포함** — 브리핑·계약에서 반드시 구분한다. |
| **`rail_step_audit`** | STEP Bible 데이터 스냅샷(§5 sparse-checkout 전제) | **감사용** 교차검증 필드가 채워진 경우(옵션 필드 허용) | §3·§3 유지: 내부 SSOT 키(`atom_id` 등) **대체·폐기 금지**. |

**전제**: 그리스 쪽 morphhb 부재 시 2차 레일은 **히브레우 우선**; 그리스는 별 코퍼스·STEP 확장 시 후속 레일로 분리한다.

### 7.2 Coverage summary JSON v2 (schema contract)

다중 레일 요약·게이트용 **선택적** 상위 스키마. 생성 스크립트는 도입 시 이 계약을 따르고, 소비자는 **알 수 없는 최상위 키를 무시**할 수 있다.

**필수 최상위 키**

| 키 | 타입 | 의미 |
|----|------|------|
| **`schema`** | string | 리터럴 `"master_atoms_lexicon_coverage_summary_v2"`. |
| **`generated_at_utc`** | string | ISO-8601 UTC. |
| **`inputs`** | object | 재현용 입력 지문. **최소 포함**: `atoms`(마스터 아톰 JSONL 경로 또는 SSOT 포인터), `external_lexicon_manifest`(§5 `MANIFEST.json`의 **경로 + `sha256`** 또는 동등한 헤드 요약 객체). **선택**: `morphhb_wlc_path` 또는 `morphhb_wlc_glob`(WLC XML 루트·글롭), 기존 Strong 전용 필드는 `inputs.strongs_*` 등으로 중첩 가능. |
| **`precedence`** | array of string | 여러 레일이 동시에 메타데이터를 붙일 때 **해석 순서·우선권**(앞이 우선 등 정책은 리포트 `note`에 명시). 권장 순서 예: `rail_strongs_seed` → `rail_morphhb` → `rail_step_audit`. |
| **`by_rail`** | object | 키 = §7.1 **rail id**. 값은 최소 **`rail_id`**(string), **`coverage`**(언어별·통합 카운트; v1 시드 요약의 `coverage`와 동일한 의미 계열: `fraction_of_greek_atoms` 등), 선택 **`notes`**, **`match_method`**(매퍼별 세분화). |
| **`corpus_buckets_ref`** | string | 코퍼스 분해 리포트(예: `master_atoms_corpus_split_summary_*.json`) 경로·SSOT 링크 — 미매칭·다중후보가 **어느 입력 코퍼스 버킷**에서 오는지 연결한다. |

**성공 매칭 집계**: `by_rail.*.coverage`는 해당 레일 정의에 맞는 분모·분자를 명시하고, 전 레일 합성 지표가 필요하면 **`precedence`**와 별도 `note`로만 서술한다(서로 다른 레일 간 단순 합산 금지 unless 정의됨).

---

## 8. 변경 이력

- 2026-03-31: 초안 작성. FACT-LOCK 경계(rows=14, 14,197 HOLD; unique_atoms 수는 §4 및 `original_language_master_atoms_summary_latest.json` 재확인) 및 이중 레일·스테이징 규약 반영.
- 2026-03-31: §7.1–§7.2 — lexicon coverage **rail id** 3종(`rail_strongs_seed`, `rail_morphhb`, `rail_step_audit`) 및 **`master_atoms_lexicon_coverage_summary_v2`** 요약 스키마 계약 추가.
- 2026-03-31: §4 — `unique_master_atoms` **41,769** vs 과거 **41,751** 병기·SSOT 우선 규칙; 코퍼스 버킷 분해 리포트 `scripts/report_master_atoms_corpus_split.py` → `master_atoms_corpus_split_summary_latest.json`.
- 2026-03-31: §7.1 **rail_morphhb** 구현 — `scripts/build_morphhb_form_to_lemma_index.py` → `morphhb_norm_to_lemma_index_latest.json`; `scripts/map_master_atoms_morphhb_seed.py` → `master_atoms_morphhb_seed_latest.jsonl` / `_summary_latest.json` (WLC `wlc/*.xml`, DSS 비포함). `audit_atoms_step_lexicon`·`report_lexicon_coverage_v2` 동일 주에 정합.
