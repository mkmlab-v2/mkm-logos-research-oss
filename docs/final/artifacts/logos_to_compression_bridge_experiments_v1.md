# Logos → 압축 KPI 연결 실험 3종 v1 (합선 금지)

- **schema:** `logos_to_compression_bridge_experiments_v1`
- **status:** `COMPLETE_EXP1_RECOMMEND_KEEP_41775` (2026-05-18)
- **hypothesis_tier:** B (compression bench only; not prophecy / not Track A trading)
- **generated_at_utc:** 2026-05-18
- **SSOT:** `docs/final/CENTRAL_AGENT_MEMORY_V1.md` 「41k·압축·LG」·`COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` §9

---

## 공통 금지

- Logos 철학·위성·Global atom 승격이 **예언 hit / BTC / 실매매** 로 자동 전이된다고 말하지 않는다.
- Export 체인에 **게마트리아 4D 없음** — 「4D가 사전을 만든다」 금지.
- 상용 동결 KPI 기본값: **`apply_gematria_4d_bridge_policy: false`** (실험 3은 **연구 AB** 전용).

## 공통 성공 판정 (압축만)

동일 벤치·동일 `run_ultra_compression_default.py` 버전에서 **전후 비교**:

| 지표 | 산출 경로 |
|------|-----------|
| `global_token_saving_rate` | `compression_metrics` in active report |
| `avg_reconstruction_fidelity_jaccard` | 동일 |
| `ultra_saving_policy_ok` | `quality_gate` |
| `case_count` | 동일 조건(기본 **40**) 유지 |

**Before SSOT:** `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`  
**After:** 새 `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` (또는 타임스탬프 부록) + `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json`

---

## 실험 1 — 코드북 재Export → must_keep → 벤치 (주력)

**가설:** Logos 원어·MorphHB/Strong 매핑 품질이 오르면 **렉시콘 lookup(must_keep)** 이 좋아져 절감·Jaccard가 변한다.

**입력:** `data/logos/` (`verse_decoded_v2_complete_v1.jsonl` 등 SSOT 코퍼스)

**순서 (저장소 루트 `c:\workspace`):**

```powershell
py scripts/core/build_original_language_master_atoms.py
py scripts/map_master_atoms_lexicon_seed.py
py scripts/map_master_atoms_morphhb_seed.py
py scripts/resolve_morphhb_multi_deterministic.py --write-latest
py scripts/export_master_codebook_v1.py
py scripts/run_ultra_compression_default.py
py scripts/report_ultra_compression_kpi_summary.py
```

**브리지 (구동 시):** `scripts/core/master_codebook_lexicon_v1_bridge.py` — `use_master_codebook_lexicon_v1=True` (active report에 이미 true)

**산출:**

- `reports/constitution/btrack_pilot/master_codebook_lexicon_v1_*_rows_latest.json`
- `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`

**완료 기준:** `row_count` ≥ prior · KPI 메트릭이 frozen 대비 **개선** (지휘관 임계: 예. saving ≥ prior AND jaccard ≥ prior − ε)

**합선 금지:** 이 실험만으로 예언·쇼룸·마중 문구 갱신하지 않음.

---

## 실험 2 — 렉시콘 커버리지·MorphHB 정합 (실험 1 전/후 진단)

**가설:** Export 품질 병목은 **미매칭 형태·커버리지** — 수치로 병목을 찾은 뒤 실험 1만 선택 재실행.

**순서:**

```powershell
py scripts/report_morphhb_match_by_corpus.py
py scripts/report_lexicon_coverage_v2.py
py -m pytest tests/test_fact_lock_lexicon_gate.py tests/test_export_master_codebook_v1.py -q
```

**산출:**

- `reports/constitution/btrack_pilot/master_atoms_morphhb_match_by_corpus_latest.json`
- `reports/constitution/btrack_pilot/master_atoms_lexicon_coverage_summary_v2_latest.json`

**완료 기준:** 커버리지↑ / unmatched↓ 방향이 확인되면 → **실험 1** Export만 재실행 (전체 Logos 철학 승격 아님).

---

## 실험 3 — 게마트리아 4D bridge policy AB (연구; 상용 기본 아님)

**가설:** `apply_gematria_4d_bridge_policy` ON/OFF가 **동일 입력**에서 saving↔Jaccard 트레이드오프를 만든다 (CENTRAL: ON 시 saving↓ 가능).

**명령:**

```powershell
py scripts/run_multilens_bridge_policy_ab.py --mode universal
# 또는: py scripts/run_multilens_bridge_policy_ab.py --all-modes
```

**산출:**

- `docs/final/artifacts/MULTILENS_BRIDGE_POLICY_AB_V1.json`
- `MULTILENS_BRIDGE_POLICY_AB_OFF_V1.json` / `..._ON_V1.json`

**완료 기준:** AB 요약이 디스크에 있고, **상용 KPI는 OFF arm만** 승격 후보로 표기.

**금지:** AB ON 결과만 보고 「Logos 4D 승격으로 압축 완성」— OFF가 동결 47% SSOT.

**선행 (선택):** `py scripts/build_gematria_metadata.py` · `py scripts/build_gematria_4d_bridge.py` — **벤치 policy와 별 레일**; bridge AB는 policy 플래그만 토글.

---

## 실행 순서 권장

```text
실험 2 (진단) → 실험 1 (재Export+벤치) → 실험 3 (정책 AB, 선택)
```

예언 체인(`eval_prophecy_hit_rate_v1` 등)은 **본 문서 범위 밖** — 병렬 트랙.

---

## 실행 로그 (2026-05-18 · 순서 2→1)

### 실험 2 — 완료

| 단계 | exit | 산출 |
|------|------|------|
| `report_morphhb_match_by_corpus.py` | 0 | `master_atoms_morphhb_match_by_corpus_latest.json` |
| `report_lexicon_coverage_v2.py` | 0 | `master_atoms_lexicon_coverage_summary_v2_latest.json` |
| pytest `test_fact_lock_lexicon_gate` + `test_export_master_codebook_v1` | 6 passed, 1 skipped | — |

### 실험 1 — 부분 완료 + 명시 A/B

| 단계 | 결과 |
|------|------|
| `build_original_language_master_atoms.py` | OK · **41,658** atoms |
| `build_morphhb_form_to_lemma_index.py` | OK (선행 누락이었음) · 79,464 norm keys |
| `map_master_atoms_morphhb_seed.py` | OK · Hebrew match **56.9%** (13,032/22,913) |
| `map_master_atoms_lexicon_seed.py` | **SKIP** · `strongsgreek.xml` 없음 (`vault/external_lexicon` 미수신) |
| `resolve_morphhb_multi_deterministic.py --write-latest` | OK · `resolved_multi: 0` |
| `export_master_codebook_v1.py` | OK · `master_codebook_lexicon_v1_41658_rows_latest.json` |
| `run_ultra_compression_default.py` (기본) | KPI **불변** — bridge가 **행 수 최대** 파일(41775) 자동 선택 |

**명시 코드북 A/B** (`evaluate_report` + `master_codebook_lexicon_path`):  
`docs/final/artifacts/logos_exp1_codebook_41658_vs_41775_latest.json`

| arm | saving | jaccard | policy_ok |
|-----|--------|---------|-----------|
| **41775** (동결 SSOT) | **0.4712** | **0.8854** | true |
| **41658** (재Export) | **0.4796** | **0.8755** | true |
| Δ (41658−41775) | **+0.0084** | **−0.0099** | — |

**해석:** 재Export만으로는 saving↑·jaccard↓ **트레이드오프** — active report·쇼룸 수치는 **41775 arm 유지** 권장. Greek Strong 수신 후 `fetch_external_lexicons.ps1` → `map_master_atoms_lexicon_seed.py` 재실행 필요.

### 실험 1 — 권장안 완료 (lexicon 수신 후)

| 단계 | 결과 |
|------|------|
| `fetch_external_lexicons.ps1 -SkipPush` | OK · repos=4, strongsgreek.xml 수신 |
| `map_master_atoms_lexicon_seed.py` | OK · Greek match **13.0%** · Hebrew **22.1%** |
| MorphHB 시드 + Export | OK · **41,658**행 (행 수 동일, Strong 메타 보강) |
| A/B (`logos_exp1_codebook_41658_vs_41775_latest.json`) | **`recommendation: keep_41775_frozen`** |

| arm | saving | jaccard |
|-----|--------|---------|
| 41775 (동결) | **47.26%** | **88.36%** |
| 41658 (lexicon seed 후) | **47.96%** | **87.55%** |
| Δ | **+0.70pp** | **−0.81pp** |

**운영 결정:** `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`·bridge 자동 선택(**최대 행 수 → 41775**) **변경 없음**. 41658은 연구 부록·MorphHB/Strong 커버리지 개선 추적용.

---

## 쇼룸·마중 재개 조건 (참고)

- 실험 1 **After** KPI가 Before 대비 개선·문서화됨
- `compression_enterprise_executive_summary_v1.md` 수치 갱신
- 그 다음 `showroom_demo_pack_v1.md` 리허설
