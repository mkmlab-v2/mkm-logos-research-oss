# MKM_MULTI_LENS_INFERENCE_REPORT_V1

> **참조 규정 1:** `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (제12절)  
> 본 문서의 작성 원칙 및 라벨링 정책은 위 헌법 제12절의 상호 참조 및 SSOT 규정을 엄격히 따릅니다.
>
> **참조 규정 2:** `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` (말미 라벨 정의)  
> 문서 내 사용되는 4대 라벨(`[FACT]`, `[HYPO]`, `[VISION]`, `[NON-MEDICAL]`)의 정확한 정의는 위 SSOT 문서를 기준으로 합니다.
>
> **추가 면책 명시: `[NON-DETERMINISTIC]`**  
> 본 문서는 미래 현상이나 자산 시장의 방향에 대한 확정적 단정 및 예언을 하지 않습니다.

---

## Track A / B 서술 가이드라인 (작성 전 확인)

| 구분 | Track A (대외 / 시장용) | Track B (내부 R&D / B-Track용) |
| :--- | :--- | :--- |
| **목적** | 실전적 방향성 및 행동 철학 제공 | 4D 좌표 교정 및 데이터 측정 로그 |
| **용어 통제** | 내부 엔진 용어 철저히 은닉 (일반 언어로 순화) | Raw 메트릭, 4D 좌표, 내부 엔진 변수 투명 노출 |
| **톤앤매너** | 검증된 메트릭 기반의 절제된 서술 | 실험적 가설 및 비전의 자유로운 전개 |

### Fact-Safe 서술 체크리스트 (금지 사항)

- [ ] 수사적 단정 금지: 데이터적 근거(수치/경로) 없는 "파국이 임박했다", "깊은 공명" 등의 강한 문학적 수사 사용 금지.
- [ ] 인과율 합선 금지: 미시적 반응(예: 특정 체질의 특성)을 거시적 시장 하락 등의 단일 인과로 강제 연결하는 서술 금지.

---

## Fact-Safe 메타 고정 헤더 (작성 시 필수)

| 필드 | 값 |
| :--- | :--- |
| `generated_at_utc` | `YYYY-MM-DDTHH:MM:SSZ` |
| `engine_id` | `V1_Approx_Stub` / `V2_Precision_MCP` |
| `boundary_rule` | 예: `observatory_ephemeris_v1` |
| `high_reliability_decision` | `PASS` / `HOLD` |
| `gate_reason` | `low_badge_forced_hold` / `monthly_check_gate` / `badge_policy_default` |
| `reliability_badge` | `LOW` / `MID` / `HIGH` |

`[FACT]` **경고(근사 엔진):** `engine_id=V1_Approx_Stub`이면 아래 문구를 강제 삽입한다.  
`- 수치 불일치 가능성 경고: 절입/경계 규칙 차이로 외부 만세력·서비스와 결과가 다를 수 있음.`

### 신뢰도 배지 계산 규칙 (고정)

- `LOW`: `samples < 10` 또는 `engine_id == V1_Approx_Stub`
- `MID`: `engine_id == V2_Precision_MCP` 이고 `10 <= samples <= 49`
- `HIGH`: `engine_id == V2_Precision_MCP` 이고 `samples >= 50` 이며 `net_delta > 0`
- `high_reliability_decision`: `LOW -> HOLD`, `MID/HIGH -> PASS`

### 사전/사후 분리 계약 (고정)

- **사전 예측 근거(Pre-Execution):** 제1~제4장(HYPO/FACT) 해석 블록만 기록
- **사후 실행 성과(Post-Execution):** `exchange_snapshot_24h` 및 KPI 히스토리 통찰만 기록
- 동일 문단에서 사전 근거와 사후 성과를 혼합해 단정 문장으로 연결하지 않는다.

---

## 제1장. 실물 레짐 베이스라인 (The 1st Regime) `[FACT]`

*(현재 시장의 거시 경제 지표, 자산 변동성 등 검증된 데이터 팩트 서술)*

* **기준 지표:**
* **현재 상태:**

## 제2장. 명리적 시간 역학 (Timing & Tide) `[HYPO]`

*(현재 시간축의 에너지 패턴 및 거시적 타이밍 서술. Track B 작성 시에만 내부 운기 변수 명시)*

### 만세력·명식 프로비넌스 (Track B 산출·JSON 연동 시 필수) `[FACT]`

간지·명식·만세력 결과를 **수치·좌표·벤치마크**에 쓸 때, 해당 아티팩트 JSON(또는 로그) 상단에 아래 필드를 **기계 판독 가능**하게 둔다. (NotebookLM A 시드·운영 SSOT와 정합.)

| 필드 | 예시 값 | 의미 |
| :--- | :--- | :--- |
| `manseryeok_model` | `static_month_day_approx_v3` / `mcp_calculate_saju` / `remote_lunisolar` | 실제 호출한 엔진 식별 |
| `jeolgi_uncertainty` | `boundary_days_high_risk` / `observatory_ephemeris_v1` | 절기 경계 오차 등급 |
| `excluded_from_jaccard` | `true` / `false` | 근사 엔진일 때 절기 경계 근처 케이스는 렌즈 지표에서 배제 권장 |

코드 헬퍼(근사 스텁 태그 전용): `tools/myeongni/manseryeok_provenance.py` — `approx_stub_pipeline_metadata()`, `tag_excluded_from_jaccard_heuristic(...)`.

`[HYPO]` **면책 (명식 근사)**: 절입 시각·야자시·진태양시·역법·학파에 따라 상용 만세력·전문가 명식과 **다를 수 있다.** 법률·의료·실거래 판단에 사용하지 않는다.

* **관측된 에너지 풀:**
* **압력의 방향성:**

## 제3장. 로고스 공명 (The Biblical Resonance) `[HYPO]`

*(사출된 정예 아톰 중 최상위 텍스트의 상징적 의미 해석)*

* **추출된 마스터 아톰:**
* **상징적 궤적:**

## 제4장. 사상적 반응과 방어선 (Human Vessel & Action) `[HYPO]` `[NON-MEDICAL]`

*(다가오는 거시적 압력에 대해 인간 군상이 겪을 수 있는 메타포적 반응과 방어적 태도 제안. Track A 작성 시 체질/병증 관련 내부 용어 배제)*

* **예상되는 취약점:**
* **권고되는 대응 철학:**

## 제5장. 사후 실행 성과 (Post-Execution Evidence) `[FACT]`

* **exchange_snapshot_24h.available:**
* **fills_count / realized_pnl / commission / funding_fee / net:**
* **history insight (samples / net_delta / avg_net_per_fill):**
* **신뢰도 배지 / 운영 게이트 (PASS|HOLD):**
