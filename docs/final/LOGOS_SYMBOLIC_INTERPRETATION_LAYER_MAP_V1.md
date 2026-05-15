# Logos · 원어 · 상징 해석 — 레이어 맵 v1

**상태:** `[DRAFT]` · 운영·감사·온보딩용 **조감도(색인)** — 단일 백서·신학 전서·TOE 완성 선언 **아님**.  
**Fact-Lock:** 구현·통과·경로 확정은 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 호출 가능 `.py`·pytest·exit code·아티팩트 JSON만. 본 문서는 **포인터·격벽·흐름**만 고정한다.  
**개정:** 2026-05-15 · 목표 분량: **~15페이지 상한**(장문 내러티브·신학 전개 금지).

---

## 0. 이 문서가 하는 일 / 하지 않는 일

| 하는 일 | 하지 않는 일 |
|---------|----------------|
| 분산 SSOT(코퍼스·그래프·증류·렌즈) **한 화면 맵** | 수백 페이지 백서로 **해석 내용** 누적 |
| 감사·B-track·신규 연구자 **나침반** | `CONSTITUTION` 본문에 **온톨로지** 삽입 |
| 대외 노출 **추출구** 명시 | NotebookLM·채팅만으로 **구현 완료** 단정 |

**상위 SSOT (읽는 순서):** 본 맵 → `CONSTITUTION` Logos 표 → `LOGOS_DEEP_RESEARCH_TRACK_B_BACKLOG_V1.md` → 필요 시 `docs/final/artifacts/LOGOS_MKM_THEOLOGY_BASELINE_V1.json`.

---

## 1. 배관 포인터 (The Pipeline)

데이터는 **항상 아래 방향**으로 무거워지며, **Track A·실매매·자동 라우팅**은 **증류·게이트·휴먼** 이후에만 논의한다.

### 1.1 흐름 (ASCII)

```
[원어·코퍼스 SSOT]
  verse_4pipeline / hebrew-greek jsonl / DSS·외경 JSONL
        │
        ▼
[슬라이스 1–2: 매니페스트·그래프]
  corpus_manifest → bible_meaning_graph (nodes/edges) + aramaic_graph (선택)
        │
        ├──────────────────┬─────────────────────┐
        ▼                  ▼                     ▼
[원어 마스터·특이점]   [벡터·ANN-lite]      [독립 렌즈 v0]
  master_atoms         manifest·ann_lite     run_lens_logos
  regime_singularity                         → logos_independent_lens_latest.json
        │                  │                     │
        └──────────┬───────┴─────────────────────┘
                   ▼
[상징·게마트리아·4D — HYPO]
  gematria metadata/bridge · run_lens_music_gematria* · symbolic_topology_insight*
                   │
                   ▼
[B-track 증류·지휘관 리포트 — 오프라인]
  run_lens_logos_deep_fusion · distill_v1 · commander_deep_report
  run_logos_track_b_pipeline_chain_v1 / Run-LogosTrackBChainV1.ps1
                   │
                   ▼
[일일 관측·쇼룸 입력 — NON_GATING]
  build_logos_insight_bundle_v1 · shadow/resonance · Track C dashboard
                   │
                   ✕  (자동 합선 없음)
                   ▼
[Track A / trading_go_no_go / 실주문 — 별도 축]
```

### 1.2 단계별 포인터 표

| 단계 | 역할 | 입력 (예) | 스크립트 (호출 가능 SSOT) | 산출 (예) |
|------|------|-----------|---------------------------|-----------|
| **L0 코퍼스** | 정본 구절·4파이프라인 | `data/logos/verse_4pipeline_full_31102.json` | (인제스트는 별도 체인; §3.2 `CONSTITUTION`) | 동 파일·`bible_original_hebrew_greek.jsonl` 등 |
| **L1 매니페스트** | 코퍼스 버전·정렬 감사 | L0 | `scripts/build_logos_corpus_manifest_v1.py` | `docs/final/artifacts/logos_corpus_manifest_v1_latest.json` |
| **L2 의미 그래프** | 교차참조·의미 노드/엣지 | L1 + graph jsonl | `scripts/build_logos_corpus_graph_bundle_v1.py` | `logos_corpus_graph_bundle_v1_latest.json` · `bible_meaning_graph_*_v1.jsonl` |
| **L2b 아람·외경** | 별 코퍼스 그래프 | DSS/외경 JSONL | `aramaic_graph_*` (산출물 `docs/final/artifacts/`) | `aramaic_graph_nodes_v1.jsonl` 등 |
| **L3 원어 요약** | 마스터 아톰·레짐 내적 스코어 | verse jsonl | `scripts/core/build_original_language_master_atoms.py` · `scripts/core/build_original_corpus_regime_singularity_report_v1.py` | `original_language_master_atoms_summary_*` · `[HYPO]` tier B 리포트 |
| **L4 벡터·검색** | ANN-lite·스모크 (B-track) | L1–L2 | `scripts/build_logos_vector_index_manifest_v1.py` · `build_logos_vector_index_ann_lite_v1.py` · `query_logos_vector_index_ann_lite_v1.py` | `logos_vector_index_ann_lite_v1_latest.json` |
| **L5 독립 렌즈** | Logos-first·증거 refs | 4D 배치 샘플 | `scripts/run_lens_logos.py` | `logos_independent_lens_latest.json` |
| **L6 상징·오디오** | 게마트리아→음악 은유·게이트 | mapping json | `scripts/run_lens_music_gematria.py` · `run_lens_music_gematria_gate_chain_v1.py` | `lens_music_gematria_v1` · gate chain JSON |
| **L7 4D·토폴로지** | 구조 측정·[HYPO] | 코퍼스·브리지 | `gematria_4d_*` · `symbolic_topology_insight` 빌더 | `docs/final/artifacts/gematria_4d_*` · `symbolic_topology_insight_latest.json` |
| **L8 증류·딥퓨전** | 장문 추론→결정론 JSON | L2·벡터·신학 baseline | `scripts/run_lens_logos_deep_fusion.py` · `run_logos_track_b_deep_fusion_job_v1.py` | `logos_deep_research_distill_latest.json` (선택) |
| **L9 지휘관 축** | 6축 심층·채택 대기 | L5·융합 스텁 | `scripts/run_logos_track_b_commander_deep_report_v1.py` | `logos_track_b_commander_deep_report_latest.json` |
| **L10 일일 번들** | 매크로·관측 입력 | L5–L9 | `scripts/build_logos_insight_bundle_v1.py` (일일 융합 체인 내) | `logos_insight_bundle_v1_latest.json` |

**예언·가격 B-track** (`eval_prophecy_promotion_gates_v1`, `outcome_class`)는 **본 파이프라인과 데이터 자동 합선 없음** — 병렬 레일(§2).

### 1.3 원클릭·회귀 (재현)

```text
# Track B Logos 체인 (스모크·로컬)
scripts/run_logos_track_b_pipeline_chain_v1.py
# 또는 Windows
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-LogosTrackBChainV1.ps1

# 증류 스키마 회귀
py -m pytest tests/test_logos_deep_research_distill_schema_v1.py tests/test_logos_corpus_manifest_v1.py -q

# 독립 렌즈
py scripts/run_lens_logos.py
```

상세 백로그·슬라이스 우선순위: `docs/final/LOGOS_DEEP_RESEARCH_TRACK_B_BACKLOG_V1.md`.

---

## 2. 격벽 및 신학 정책 (The Walls)

### 2.1 신학·출력 정책 SSOT

| 문서 | 역할 |
|------|------|
| `docs/final/artifacts/LOGOS_MKM_THEOLOGY_BASELINE_V1.json` | 텍스트 우선순위·금지 출력·provenance·`not_a_deregulation_claim` |
| `docs/final/artifacts/LOGOS_DEEP_RESEARCH_DISTILL_CONTRACT_V1.json` | 증류 필드·`evidence_refs`·HITL `review_gate` |
| `docs/final/schemas/logos_response_schema_v1.json` / `v2` | LLM 응답 검열·렌더 (`scripts/logos_response_validator_v1.py`) |
| `docs/final/LOGOS_NOTEBOOK_META_GUIDE.md` | 성경 연구 노트북 분리·원어 우선·매매 맥락 오염 금지 |

### 2.2 레일 격벽 (합선 금지)

| 레일 | 태그 | 실전 트리거 | 본 맵과의 관계 |
|------|------|-------------|----------------|
| **Logos·원어·상징** | `[HYPO]`·`[NON_GATING]` | **금지** (해설·관측만) | §1 파이프라인 |
| **2차 성경 레짐** | 보조 | **금지** (`regime_map` 주) | `data/regimes/biblical_regime_matrix.json` — 해설용 |
| **B-track 예언·게이트** | `[HYPO]` | **금지** (승격=별 게이트) | `prophecy_promotion_gates_v1_latest.json` |
| **장-뇌·미생물 은유** | 커뮤니케이션 | **금지** (은유→수치 단정) | `AGENTS.md` · `.cursor/rules/gut-brain-metaphor-agent-v1.mdc` |
| **Track A·실매매** | 운영 | **휴먼·GO/NO_GO** | `trading_go_no_go_latest.json` · ECC — §1 그림 ✕ |

**선언:** §1에서 생성된 모든 통찰·상징·게마트리아 산출은 **가설·관측 레이어**이며, `combined_all_passed`·`go_no_go`·주문 API로 **자동 연결되지 않는다.**

### 2.3 라벨 계약 (감사·NL 공통)

| 라벨 | 사용 |
|------|------|
| `[FACT]` | 경로·스키마·exit code·재현 명령 |
| `[HYPO]` | MKM 내부 해석·게마트리아·4D 브리지·상징 연결 |
| `[NON_GATING]` | Logos·성경 렌즈 — 최종 액션 미확정 |
| `[BRIEFING_ONLY]` | 옵시디언·NotebookLM — SSOT 승격 전 |

---

## 3. 대외 추출구 (The Output)

백엔드(L0–L10)는 **그대로 대외에 노출하지 않는다.** 나가는 것은 **스크럽·압축·면책**을 거친 표면만.

| 대외 표면 | 허용 형태 | SSOT·초안 |
|-----------|-----------|-----------|
| **Track C·B2B** | 관측·게이트·재현 KPI·은유(비생물·비단정) | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.5–3.6 · `docs/research/TRACK_C_B2B_GUT_BRAIN_METAPHOR_ONEPAGER_DRAFT_V1.md` |
| **쇼룸·Topology** | 읽기 전용·아티팩트 근거 | `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` · Trust Visualization v0 |
| **카피·법무** | 금지 패턴·NON_GATING | `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` **v1.7** |
| **지휘관·유료 브리프** | 문제–근거–행동·스니펫 가드 | `docs/final/artifacts/logos_symbolic_paid_user_brief_latest.md` (내부 검토 후) |
| **LG·투자자 덱** | 70/20/10·조건부 수치 | `docs/final/artifacts/lg_hs_persuasion_module_v1_2026-05-08.md` |

**금지 추출 예:** 원본 `verse_4pipeline` 전체 덤프 · 미검증 장문 “성경이 시장을 예언” · 게마트리아 수치만으로 **매매 GO** · 신경·장내 미생물 **임상 입증**.

---

## 4. 감사·온보딩 체크리스트 (1페이지)

1. 질문이 **어느 레이어(L0–L10)** 인지 먼저 고른다.  
2. 답변에 **아티팩트 경로 + 재현 명령 1줄**을 붙인다.  
3. 해석 문장에는 **`[HYPO]`** 또는 **`[NON_GATING]`** 를 붙인다.  
4. Track A·실매매 질문이면 **§1 파이프라인과 분리**해 `trading_go_no_go`·휴먼 승인 축으로 보낸다.  
5. 대외 문서에는 **§3 표면**만 사용하고 §1 원본 그래프는 **비공개** 유지.

---

## 5. 관련 맵·볼트 (교차 링크)

| 필요 | 경로 |
|------|------|
| 옵시디언 그래프 | `memory/obsidian_vault/UNIVERSE_MKm/TECH_Logos_성경렌즈.md` · `00_START_그래프_맵.md` |
| 장-뇌 은유 (별 레일) | `memory/obsidian_vault/UNIVERSE_MKm/CONCEPT_장뇌축_*.md` |
| 멀티렌즈 작업 | `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` |
| Logos-first 규칙 | `.cursor/rules/logos-first-pipeline.mdc` (있을 때) |

---

## 6. 개정·승격

- **변경 시:** `CONSTITUTION` Logos 표와 **불일치하면 CONSTITUTION이 이긴다.**  
- **승격:** P0 경로 등록 후 팀 공유; 장문 신학은 **본 파일에 쓰지 않고** baseline·distill·옵시디언에 둔다.  
- **다음 압축 한 줄:** `Logos 맵 = L0 코퍼스 → L2 그래프 → L5–L8 HYPO 증류 → NON_GATING 관측; A-track·실매매 자동 합선 없음.`

---

**면책:** 본 맵은 투자·의료·신학적 권위 주장이 아니며, 법무·규제 적합성은 별도 검토 대상이다.
