# Logos–Risk Bridge v1 (개념·FACT 앵커)

**작성일**: 2026-03-29  
**최종 업데이트**: 2026-03-29  
**상태**: **v1** — 근원(Logos) 검색·임베딩 쪽 **코드 FACT**와, 시장·심리·레짐과의 **메타 브리지(가설)**를 한 문서에 고정한다. verse 파이프라인과 **동일 실행·동일 import 금지** (`.cursor/rules/logos-first-pipeline.mdc`).

---

## 목적

- **시장 쪽**에서 쓰는 공포·탐욕 지수(FGI 등)·변동성 계열 신호를 **“레짐 유사(보조)”** 관점으로만 기술하고,
- **성경 4D verse** 산출물(`verse_4pipeline_*`, `ensemble_core_*` 등)과의 **해석적 연결 아이디어**를 한 문서에 고정한다.
- **Logos 측 구현**으로 이미 존재하는 **계층형 검색**(`layered_search`)은 아래 §2에서 **FACT**로 인용한다. **Risk 측 수치·FGI·실매매 트리거**는 본 문서에서 수식·임계값을 확정하지 않는다.

---

## 1. 코드베이스 FACT — 계층형 Logos 검색

**경로**: `tools/core/logos_layered_search.py`

| 항목 | 내용 |
|------|------|
| **Phase 1** | 개신교 정경(canon) 코퍼스를 스트리밍·힙 기반으로 순위 매김; `canon_top_k` 상한. |
| **Phase 2** | DSS·외경(apocrypha) 등 **보조** JSONL이 있으면 동일 쿼리 임베딩으로 국소 순위 후 가중(`secondary_weight`)·병합. |
| **전역 2차 상한** | 보조 후보 전체를 합친 뒤 정렬하고 **`secondary[:secondary_top_k]`**로 **전역 캡**(문서화된 동작; 레짐·금융 import 없음). |
| **레짐/금융** | 본 모듈은 `data/regimes/`·KOSPI·트레이딩 API를 **import하지 않음** — Logos-first 정합. |

**회귀 검증**: `tests/test_logos_layered_search.py` — 계층 검색·상한 동작을 단위 테스트로 고정한다.  
**주의**: 저장소 전체 `tests/` 실행 결과는 환경·스코프에 따라 다를 수 있다. “전 테스트 녹색”은 **동일한 pytest 스코프·명령**으로 재현했을 때만 FACT로 서술한다.

---

## 2. 공명 감쇄율 (Resonance Decay) — 기호·가설 (v1)

**의도**: “비트코인(또는 포트폴리오) 쪽 4D 상태 벡터”와 “선택된 verse 서브셋의 4D/거리 요약”이 **동일 시점·동일 좌표계**에서 얼마나 **열화(decay)**되는지를 **설명용 지표**로 쓸 수 있는지 탐색한다. v1에서는 **구현·단일 수치 확정 없음**.

**기호 (채팅·대외 시 구체 수치 대신 변수명 사용)**:

- \(\mathbf{v}_M\): 시장·자산 쪽 메타에서 정의된 **정규화된 4D 벡터** (내부 상수는 문서·채팅에 노출하지 않음).
- \(\mathbf{v}_L\): 동일 시점·동일 규격으로 집계한 **Logos verse 서브셋**의 대표 벡터(예: 상위 \(k\)절의 평균 또는 가중 평균 — **정의는 실험 설계 후** 고정).
- \(d(\mathbf{v}_M, \mathbf{v}_0)\), \(d(\mathbf{v}_L, \mathbf{v}_0)\): Divine Centroid(측정용 앵커)와의 거리 등 **이미 verse 파이프라인에서 쓰는 거리 개념**과 동일 계열로만 서술.
- **공명 감쇄율(개념)**: 두 흐름이 “같은 장(場)”에서 얼마나 **동기화**되는지의 **감쇄**를 \(\mathcal{R}_{\mathrm{decay}} = f(d_M, d_L, \lambda_{\mathrm{sys}}, \ldots)\) 형태로 둘 수 있다고만 적는다. \(f\)·계수는 **제품 승격 전까지 확정하지 않음**.

**금지**: verse 스크립트 한 프로세스 안에서 FGI·레짐 API와 **같은 import 그래프**로 \(\mathcal{R}_{\mathrm{decay}}\)를 계산하는 설계 (Logos-first 위반).

---

## 3. 경계 (필수)

| 구분 | 허용 | 금지 |
|------|------|------|
| 실행 순서 | Logos 리포트·추출 완료 후, **별도 실행**에서만 “브리지 해설” | verse 파이프라인 한 실행 안에서 FGI·KOSPI·레짐 동시 연산 |
| 코드 | 금융·레짐은 `projects/bitcoin-trading/` 등 **확장 트랙** | `report_logos_*`, `extract_logos_*`에서 외부 금융 import |
| NotebookLM | 소스 매니페스트 `## Logos_MKM` + 본 문서로 역할 분리 | 한 노트에 “구절 4D + 매매 시그널” 혼재 서술 (혼선 유발 시 금지) |

---

## 4. 개념 스케치 (가설) — 시장 레짐과의 나란히 제시

1. **시장 레짐 보조 신호**: FGI·변동성 등은 `data/regimes/`·트레이딩 쪽 SSOT에서 정의된 **1차 실물 레짐**과 별개로, “심리·변동성 국면” 라벨을 **설명용**으로만 붙일 수 있다.
2. **Logos 측**: 절별 `vector_4d`·centroid 거리 등은 **근원 데이터**(`data/logos/…`)에서만 산출한다.
3. **브리지(메타)**: 동일 시점에 (a) 시장 심리 국면 요약과 (b) 특정 verse 서브셋의 분포 요약을 **나란히** 제시하는 것은 가능하나, **인과·예측 수식**으로 단정하지 않는다. 상관·검증은 별도 실험 설계 후 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 등 A 궤적에만 승격 기록.

---

## 5. 구현 상태 (v1 정리)

| 구분 | 상태 |
|------|------|
| **계층형 Logos 검색** | **코드 존재** — `layered_search` 등 (`tools/core/logos_layered_search.py`). |
| **Logos–Risk 단일 어댑터** | **미구현** — 전용 리포트·바인딩은 향후; 본 문서는 경계·기호·FACT 앵커만 제공. |
| **수치·임계값** | 채팅·대외 공개 시 **내부 상수 노출 금지**; 변수명·상대 표현만 사용. |

---

## 6. 참조 (실측 경로)

- Logos 메타: `docs/final/LOGOS_NOTEBOOK_META_GUIDE.md`
- Verse 4D 풀: `data/logos/verse_4pipeline_full_31102.json`
- 레짐(실물) 정책 예시: `data/regimes/regime_fusion_policy.json`, `data/regimes/regime_map.json`
- 헌법 추론·구현 팩트: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`
- 계층 검색 구현: `tools/core/logos_layered_search.py`

---

## 7. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-03-29 | v1 스텁 최초 작성 (Logos–Risk 경계·가설 고정) |
| 2026-03-29 | v1 확장: `logos_layered_search` FACT, 공명 감쇄율 기호, 구현 표 분리 |
