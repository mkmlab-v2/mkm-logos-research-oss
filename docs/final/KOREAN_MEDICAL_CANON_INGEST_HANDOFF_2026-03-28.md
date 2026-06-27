# 한의 원전(동의수세보원·이제마 등) 인제스트 핸드오프 (2026-03-28)

## 문서 메타

- 갱신: 2026-03-29 (Proxy 트랙 명시) · 최초 2026-03-28
- Fact-Lock: [FACT]는 SSOT·스키마·경로만; [STRAT]는 코호트·RAG 분기 운영 규칙.

## 목적

원전 텍스트가 확보되었을 때 **저장소에 바로 넣을 수 있는 규격**과 **추론 경계([FACT]/[STRAT])**를 고정한다. 원본 파일 유무와 무관하게 선행 가능.

---

## [FACT] — SSOT와의 관계

- 체질 분류 **본선**은 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 기준 **영문 KJV 프록시 + MPNet·센트로이드·(선택)4D**다. 한의 원전 문장을 그대로 본선 분류기에 넣었다고 **자동 정합**되지 않는다.
- 한국어 검증 코호트 JSONL 스키마: `data/constitution/korean_cohort/SCHEMA.json` (`text`, `expected_parent` 필수; `additionalProperties: true`).
- 로더: `tools/core/constitution_korean_cohort_io.py` — `expected_parent`는 `TY|SY|TE|SE` 또는 한글 부모명(내부 정규화).

---

## [STRAT] — 두 갈래 (혼동 금지)

| 갈래 | 용도 | `expected_parent` | 저장 위치(권장) |
|------|------|-------------------|-----------------|
| **A. 라벨 코호트** | `evaluate_constitution_korean_cohort.py` 등 T2·게이트 | **필수** (전문가·규칙으로 부모 체질 부여된 절만) | `data/constitution/korean_cohort/` 아래 승인된 `.jsonl` |
| **B. 원전 말뭉치** | RAG·NotebookLM·프롬프트 컨텍스트·향후 라벨링 원천 | 없음 또는 별도 스키마 | `data/constitution/korean_cohort/sources/sasang_canon/raw/` — **2026-03-29:** 정본 복사·섹션 분할·`metadata.yaml` (`scripts/export_ijeoma_sasang_canon_raw.py`) |

원전 **전체**는 보통 단일 `expected_parent`가 없으므로, **B로만 두고 A에 넣지 말 것**. A로 쓰려면 **절 단위 라벨**이 붙은 뒤에만 JSONL에 합류.

### [STRAT] 원전 전문이 없을 때 — 검증된 2차·통찰을 Proxy로

- **용도:** 특정 전권(예: 격치고) **합법 입수 전**에도 RAG·NotebookLM·프롬프트 설계를 이어가기 위한 **참고층**이다. **원전 텍스트의 무손실 대체가 아니다.**
- **메타 권장:** `metadata.yaml` 또는 문서 헤더에 `source_tier: secondary` · `proxy_for: (작품명)` · `license_note` · 출처(백과·논문 인용 등)를 명시.
- **경계:** 2차 요약·통찰 유닛은 **코호트 A의 `expected_parent` 근거로 자동 승격되지 않는다** ([FACT] 동일). 영문 KJV·MPNet 본선과의 **자동 합선**은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS` 기준 금지.
- **Track B 예시:** `docs/final/IJEOMA_GEUKCHIGO_YUGO_SECONDARY_INSIGHT_2026-03-29.md` — 격치고·유고 **2차** 통찰(원전 SSOT 아님).
- **논문·SciSpace만 있는 경우:** `docs/final/IJEOMA_GEUKCHI_CHEONYU_PAPER_PROXY_LAYER_2026-03-29.md` — 격치고·천유초 **`[PAPER_PROXY]`** (백과·DOI·Deep Review; 원전 무손실 대체 아님). SciSpace 큐레이션: `docs/final/SCISPACE_SASANG_LITERATURE_HELPFUL_ITEMS_2026-03-29.md`.

---

## 인제스트 체크리스트 (원본 도착 시)

1. **인코딩**: UTF-8 (BOM 없음 권장).
2. **형식**: 코호트면 **JSONL** 한 줄당 한 객체; 원문 전권은 `raw/`에 `.txt` 또는 `.md` + **메타 YAML** 병행 가능. 템플릿: `data/constitution/korean_cohort/sources/sasang_canon/raw/metadata.example.yaml` → 복사 후 `metadata.yaml`로 채움.
3. **필수 메타 (감사·재현)**  
   - `source_work`: 예 `동의수세보원`, `동의수세보원(판본명)`  
   - `edition_or_url`: 판본·출판사·URL 중 확보 가능한 것  
   - `license_note`: 공개·인용 허용 범위(내부 연구만 등)
4. **`sample_id` 규칙 (코호트行)**: `SASANG_CANON|<work_slug>|<ref>` 예: `SASANG_CANON|dongui|juan3-p12`.

---

## 코호트 JSONL 예시 (라벨이 붙은 절만)

`SCHEMA.json` 선택 필드: `cohort`, `annotator`, `annotation_version`, `notes` — 여기에 더해 아래를 **추가 속성**으로 허용 가능.

```json
{"text":"(원전 인용 한 절)","expected_parent":"TE","sample_id":"SASANG_CANON|dongui|excerpt-001","cohort":"sasang_canon_pilot","source_work":"동의수세보원","passage_ref":"권/페이지","license_note":"내부 연구","notes":"라벨 근거: …"}
```

템플릿 파일: `data/constitution/korean_cohort/sources/sasang_canon/sasang_canon.template.jsonl`

---

## mkmlife `expert-domain`과의 관계

- `projects/mkm/mkm-life/src/lib/expert-domain.ts`의 **health** 프로파일은 UI·채팅 4D 바이어스용이다. 원전 인제스트와 **직접 연결되지 않음**. 원전 적용은 **코호트/RAG/프롬프트** 층에서 처리.

---

## 다음 액션 (파일 확보 후)

1. **B만 있을 때**: `raw/`에 저장 + 메타 YAML 1개 → NotebookLM/로컬 RAG에 소스로 올리기.  
2. **라벨 가능할 때**: 절 단위로 `expected_parent` 합의 → A 형식 JSONL로 옮기고 `scripts/evaluate_constitution_korean_cohort.py` 재현 명령은 SSOT 문서 따름.

## 검증 (로컬)

**원클릭 (Sasang + T1 배치 + CI 동등 pytest + 이제마 dry-run):**

```powershell
.\scripts\run_integrated_constitution_canon_smoke.ps1
```

**Sasang만:**

```bash
python scripts/validate_sasang_canon_drop.py
python scripts/validate_sasang_canon_drop.py --jsonl data/constitution/korean_cohort/sources/sasang_canon/sasang_canon.template.jsonl
```

원전 `.txt`/`.md`가 있는데 `metadata.yaml`이 없으면 경고(기본). CI·게이트에서는 `--strict`로 실패 처리 가능.

**CI**: `push`/`pull_request` 시 `.github/workflows/ci.yml`·`pr-check.yml`의 `Sasang canon drop + template JSONL (smoke)` 단계에서 위 두 명령이 자동 실행된다(템플릿 JSONL·빈 raw 기준 통과).

---

## 2026-03-29 — Track B 운영·검증

- **MKM_DATA_VAULT** `data/corpus/ijeoma/_inventory/`: `IJEOMA_CHUNK_TABLE_2026-03-29.jsonl`, `IJEOMA_NOTEBOOKLM_QUERY_SET_2026-03-29.md` 미러(로컬 RAG FTS 증분 전제).
- **Vault** `docs/final/IJEOMA_CHUNKING_RULES_2026-03-29.md` 동기.
- **NotebookLM** 노트북 `332586f9-810e-4b86-af98-150963d68d71` — 고정 질의 9번으로 `notebook_query` 스모크: 응답에 일러두기·계보 소스 인용 확인.
- **local-rag** — `reindex_vault` 증분(2026-03-29): 52파일 갱신, FTS에 Vault 미러·이제마 인벤토리 반영.
- **Vault `sasang_canon/raw/`** — 워크스페이스 B갈래 정본·섹션 TXT·메타 전부 복제 후 `reindex_vault` +13건(총 69330건 FTS).
- **NotebookLM 소스 추가 (2026-03-29, `nlm source add --wait`)** — 노트북 `332586f9-810e-4b86-af98-150963d68d71`: `IJEOMA_B_TRACK_NEXT_TODO_2026-03-29.md` → `a1c54611-40d3-48b8-a44a-4245eaeb56de`. 본 핸드오프는 초판 `73aec34c-1366-4e4c-8c17-39be7304e93b` 후, 소스 ID 각주 반영판 **`57c0879e-f34b-41e0-8a05-21b8b3b66ff9`**(중복 시 UI에서 구판 삭제 가능).
- **`[PAPER_PROXY]` (2026-03-29)** — 격치고·천유초 원전 없이 진행 시 `IJEOMA_GEUKCHI_CHEONYU_PAPER_PROXY_LAYER_2026-03-29.md` + SciSpace DOI 목록을 B트랙에 추가. 동의수세보원 정본·코호트 A와 **경로 분리**.

### 최근 분석 결과 (Night Watch · Fusion, 2026-03-29)

- **산출물:** `reports/ijeoma/naptime_query_latest.json` — 융합 경계 질의 1회 스냅샷(본 문서 [STRAT] Proxy·가드레일과 정합).
- **재현:** `.\scripts\run_ijeoma_naptime_auto.ps1 -SkipVault -SkipPush -QueryFile scripts\naptime_ijeoma_fusion_bounded_query_ko.txt` (Vault/Push 생략 시 약 수십 초; 전체 동기가 필요하면 동일 스크립트에서 `-SkipVault`/`-SkipPush` 제거).
- **내용 요약:** 격치고·유고 쪽은 노트북·2차 통찰 파일명을 본문에 인용 형태로 포함; 사해(DSS) 담론은 프롬프트대로 **`[일반 지식]`** 으로만 서술. 두 전통의 직접 인과는 주장하지 않고 비교 각도 1문장.
- **한 줄 (사심신물 ↔ 양생):** 사심신물(事心身物) 틀로 세계·인간 상호작용을 읽고, 그 인식론·심성론이 멈추지 않고 **양생·수양의 실천 의학**으로 이어진다는 점이 해당 Fusion 답변에서 드러난 축이다(원전 단정 아님·2차·Proxy 경계 유지).
- **API 메모:** NotebookLM 응답 JSON에서 `sources_used` / `citations`가 비어 있는 경우가 있으나, 답변 본문의 파일명·출처 표기로 **운영 추적(Trace)** 은 가능. `completion_check`·게이트(GO/DONE)는 이 JSON과 **인과 연동하지 않음**(`run_constitution_completion_check.py` SSOT 유지).

---

## 관련 문서·파일

- `docs/final/TRACK_B_PROXY_MINIMUM_FIELDS_SSOT.md` — Track B 프록시 **`metadata.yaml`·MD 프론트매터** 최소 필수 필드 키 이름 **단일 SSOT** (SCHEMA.json·`metadata.example.yaml`과 드리프트 방지)
- `docs/final/DSS_APOCRYPHA_PROXY_HANDOFF_2026-03-29.md` — 사해·외경 **프록시** 티어·S–L–K–M 해석 앵커(가설)·NotebookLM 가드레일; 파일·FTS·Vault 정렬(벡터 DB 비필수)
- `docs/final/REPO_BRANCH_LINEAGE_2026-03-28.md` (Git PR 베이스: `chore/...` vs `main`)
- `docs/final/INTEGRATED_CONSTITUTION_CANON_SPRINT_TODO_2026-03-28.md` (스프린트 통합 체크리스트)
- `docs/final/FACT_BRIEF_2026-03-28.md` (실데이터·T1·스모크 증거)
- `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`
- `docs/final/IJEOMA_B_TRACK_NEXT_TODO_2026-03-29.md` (P0/P1·local-rag·로고스 대조 완료; [CANON] 격치고·천유초 HOLD·`[PAPER_PROXY]` 트랙; 인덱스는 파일·FTS)
- `docs/final/IJEOMA_GEUKCHIGO_YUGO_SECONDARY_INSIGHT_2026-03-29.md` (격치고·유고 **2차** 통찰·NotebookLM용; 원전 대체 아님)
- `docs/final/IJEOMA_GEUKCHI_CHEONYU_PAPER_PROXY_LAYER_2026-03-29.md` · `docs/final/SCISPACE_SASANG_LITERATURE_HELPFUL_ITEMS_2026-03-29.md` (원전 없이 논문·SciSpace만으로 **Proxy**)
- `NotebookLM_sources_manifest.md` → `## 이제마_B_Track` — Vault `notebooklm_sources\이제마_B_Track\`로 동기화됨(노트북에 폴더·파일 업로드)
- `data/constitution/korean_cohort/SCHEMA.json`
- `data/constitution/korean_cohort/sources/sasang_canon/raw/metadata.example.yaml`
