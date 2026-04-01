# Logos 교집합 랭킹 SSOT (2026-03-29)

**역할**: Fact-Lock 교집합(1,574 ID, `k_top=6866`) 위에 **추가 랭킹**을 얹을 때의 지표·경로·재현 조건을 고정한다. **실매매 트리거·본선 OOF와 자동 합선하지 않는다** (B/연구 레이어).

## 지표 (Ranking SSOT)

| `ranking_strategy` | 정의 | 용도 |
|--------------------|------|------|
| `mean` (기본) | 네 레짐 `cosine_to_regime_fingerprint_4d`의 산술평균 → 출력 필드 `mean_cosine` | “전 레짐 평균 정렬”이 필요할 때 |
| `min` | 네 코사인 중 **최솟값** → 출력 필드 `min_cosine` | 한 레짐이라도 약하면 전체 점수가 내려가는 **보수(병목)** 뷰 |

기호 **λ(편향 0.25)** 와 혼동 금지. 랭킹 문서·JSON에서는 **mean_cosine / min_cosine** 만 쓴다.

## 입력·출력 경로

- **교집합 (Git 추적 가능)**: `backtest_results/sweep_kmin_refine/LOGOS_RESONANCE_BTC_EXT_INTERSECTION_TOP6866.json`
- **레짐별 점수 (로컬 산출물, Git 미추적이 일반적)**: 동일 디렉터리의 `LOGOS_RESONANCE_BTC_EXT_{bear_trend|bull_pump|capitulation|sideways_accumulation}_TOP6866.json`
- 네 파일이 없으면 스윕/정제 파이프라인을 **로컬에서 재실행**해 동일 `k` 산출물을 생성한 뒤 `py scripts/refine_top_1_percent_logos.py` 실행.

## 스크립트

- `scripts/refine_top_1_percent_logos.py`
- 예: `py scripts/refine_top_1_percent_logos.py` (기본 `mean`, 상위 약 1%)
- 예: `py scripts/refine_top_1_percent_logos.py --strategy min`
- (선택, B-track) `scripts/join_logos_verses_myeongni_states_4d.py` — 상위 16구절과 명리 16상 `vector_4d`의 **합의 최대 코사인 배정**(랭킹 1위≠state 1 고정 아님). 산출(추적 권장): `docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json`

생성 JSON은 `**/backtest_results/` 규칙상 저장소에 올리지 않을 수 있음; SSOT는 **스크립트 + 본 문서**이며, 숫자 리포트는 필요 시 `docs/final` 요약만 별도 반영한다.

---

## 문서 라벨 규칙 (Fact-Safe)

| 라벨 | 의미 | 사용 기준 |
|------|------|-----------|
| `[FACT]` | 랭킹·경로·명명 고정 | 지표 표(`mean`/`min`), 스크립트 경로, 교집합 JSON 상대 경로; λ(0.25)와의 비혼동 규칙 |
| `[HYPO]` | 조인·배정 해석 | `join_logos_verses_myeongni_states_4d.py`의 합의 배정·“1위≠state 1” — 실험 가설층 |
| `[VISION]` | 로컬 재실행·승격 | 파이프라인 재실행 후 승격은 `CONSTITUTION`·A 궤적 별도 기록 |
| `[NON-MEDICAL]` | 비의료 고지 | 명리 조인은 **의료 판단·체질 처방 주장 아님**; B-track 연구 격벽 유지 |

대외 인용 시 수치는 `출처 JSON/스크립트 + 셋 구성(k_top·교집합 ID 수) + 지표 필드명(mean_cosine|min_cosine)`을 한 줄에 적는다.
