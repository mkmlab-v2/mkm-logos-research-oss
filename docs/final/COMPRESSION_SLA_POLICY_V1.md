# Compression Two-Track SLA Policy (v1)

**Status:** operational policy (v1)  
**Aligned with:** `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`, `docs/final/artifacts/compression_alarm_thresholds_v1.json`  
**Not:** a guarantee of trading edge, legal advice, or literal replication of all payloads without separate audits.

### Operating summary — use-case mapping (고정)

**관심사 분리:** 토큰 경제·벤치용 **압축/복원 파이프라인**과 **시그널 생성·실매매(`dual_regime` 등)** 는 다른 축이다. 벤치 산출을 본선 트레이딩 근거로 섞지 않는다 — `MKM_LESSONS_LEARNED_V1.md`의 **FAIL-COMP-004** (연구/벤치 ↔ 상용 레일 무단 합선 금지) 및 Fact-Lock과 동일 선상. **가짜 인과(“압축 기술이 수익률을 올렸다”)** 홍보는 정책 위반에 가깝다.

| Profile | `run_ultra_compression_default.py` | 최적화 축 | 전형적 용도 (문서상 역할) |
|---------|-------------------------------------|-----------|-------------------------|
| **Track A — universal** | 기본 / `--mode universal` | 벤치·옵스·**`active_kpi`·웹훅 알람** | API/로깅·기본 재평가 |
| **Track B — literal** | `--mode literal` | 복원·감사 가능성(높은 Jaccard, 낮은 절감) | 도메인 리터럴·보수적 페이로드 |
| **Track B — ultra-literal** | `--mode ultra-literal` | 극복원·연구·정밀 밴드 (비용·시간↑) | **연구 레인**; 컴플라이언스/법적 인감 **아님** (§3·본 문서 경계) |

**라우팅:** 애플리케이션이 압축을 호출할 때는 **유스케이스별로 `mode`를 명시**하고(하드코딩 또는 설정 테이블), 트레이딩 모듈이 “수익 최적 조합”으로 프로파일을 바꾸지 않는다. 주문/감사 로그에 어떤 프로파일을 쓸지는 **별도 요구·지연·보관 정책**에 따르며, `ultra-literal`을 전 로그에 일괄 강제하는 것이 항상 타당하다고 단정하지 않는다.

#### Call-site audit (강제 라우팅 후보 — 레포 스캔 기준)

**결론:** `projects/bitcoin-trading/src/**` 전략·백테스트·주문 경로에서 **`evaluate_report` / `POST /v1/compress` HTTP 호출은 발견되지 않음.** 압축은 **워크스페이스 `scripts/` 벤치·스텁·자동화**에 집중. OPS는 스텁 **생존 확인만** `GET http://127.0.0.1:8010/health` (`ensure_compression_stub.ps1`, `build_ops_health_overview.ps1`).

| 진입점 종류 | 경로 | 비고 |
|-------------|------|------|
| 배치 벤치·KPI 재생성 | `scripts/run_ultra_compression_default.py` (`--mode`) | 단일 CLI로 Track 선택; **강제 라우팅의 기준선** |
| 자동화 체인 | `scripts/run_compression_automation_chain.ps1` | universal → (옵션) literal / ultra-literal 순 실행 |
| HTTP 스텁 v1 | `scripts/compression_token_api_stub.py` → `POST /v1/compress` | 티어·`hydrate_live_eval`·`runner_hint`(ultra_literal 등); **향후 앱이 붙을 때 가장 유력한 단일 게이트** |
| HTTP 스텁 v2 | `scripts/compression_token_api_v2_stub.py` | Trust Packet·`evaluate_report` 패밀리 |
| 스트레스·반증 | `scripts/run_compression_cross_domain_falsification_v1.py`, `scripts/run_cross_domain_compression_stress_v1.py` | 벤치용; 본선과 합선 금지(FAIL-COMP-004) |

**향후 코드 강제 권장:** 트레이딩/주문 모듈에 압축을 붙일 경우 **스텁의 요청 스키마**에 `sla_track` 또는 명시적 `runner_hint`를 필수화하고, `compression_token_api_stub.compress` 한 함수에서만 허용 프로파일을 검증한다(분산 하드코딩 지양).

## 1. Purpose

Separate **service expectations** for (A) default multi-lens bench / ops compression and (B) **domain-literal** payloads where token economy is secondary to reconstructive fidelity and auditability.

## 2. Track definitions

### Track A — Universal ops (default)

- **Role:** Primary benchmark profile driven by `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json` and refreshed by `scripts/run_ultra_compression_default.py` with `--mode universal` (default).
- **Quality targets (indicative, from archived KPI snapshots):** sensitive integrity 1.0; reconstruction fidelity (Jaccard) on the order of ~0.73; global token saving rate near ~0.49 with policy floor 0.49 per Fact-Lock §6.1.
- **Artifacts:** `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`, `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json`.

### Track B — Literal-priority (conservative)

- **Role:** Conservative compression: lower saving caps, strategy `C`, intensity `high`, to prioritize fidelity over savings. Invoked by `scripts/run_ultra_compression_default.py --mode literal`.
- **Targets (engineering bounds, not certifying legal/medical correctness):** maximize Jaccard toward 1.0; accept saving rates roughly in the 0.10–0.30 band when the experimental compressor honors caps; integrity remains gated by the same `must_keep` / sensitive logic as Track A.
- **Artifacts:** `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json` (does not overwrite Track A active report).
- **Example bench snapshot (V2 input, refresh to reproduce):** on a representative run, average reconstruction fidelity (Jaccard) moved to approximately **0.92** with global token saving near **0.25** — illustrative only; re-run the script for current numbers.

### Track B — Ultra-Literal (research, precision-first)

- **Role:** Same strategy `C` / intensity `high`, but **much lower saving caps** (order ~0.06 general/sensitive, ~0.08 Hangul on the reference implementation) so reconstruction Jaccard approaches **1.0** on the V2 bench, at the cost of token economy. Targets **precision-heavy proxy bands** on that bench: `cmp2_001`–`010` (EN policy/ops, finance-adjacent) and `cmp2_011`–`040` (Korean medical/sasang lines). Subset aggregates are written under `compression_metrics.precision_domain_subsets` in the active report.
- **Command:** `py scripts/run_ultra_compression_default.py --mode ultra-literal`
- **Artifact:** `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json` (does not overwrite Track A or Track B literal reports).
- **Automation (optional):** `scripts/run_compression_automation_chain.ps1 -IncludeUltraLiteralTrack` (also runs loss-pattern report for `--sla-track ultra_literal`).
- **Boundaries:** Research profile only — not a compliance seal for regulated medical or financial advice; webhook alarms remain **Track A `active_kpi`** per section 3.

## 3. Boundaries

- Track B does **not** replace dedicated legal, wallet, or clinical verification pipelines. It is a **compression profile**, not a compliance seal.
- `go_no_go` in decision JSON is **not** auto-derived from KPI alone (Fact-Lock §6.1).
- Legacy `ultra_saving_50_ok` vs policy-min 0.49: Track A may satisfy policy while failing the legacy 50% flag; document thresholds in `compression_alarm_thresholds_v1.json`.

## 4. Operational commands

| Track | Command |
|-------|---------|
| A | `py scripts/run_ultra_compression_default.py` or `--mode universal` |
| B | `py scripts/run_ultra_compression_default.py --mode literal` |
| B ultra-literal (research) | `py scripts/run_ultra_compression_default.py --mode ultra-literal` |
| Full chain + Track B + dual loss reports | `scripts/run_compression_automation_chain.ps1 -IncludeLiteralTrack` |
| Full chain + ultra-literal + loss patterns | `scripts/run_compression_automation_chain.ps1 -IncludeUltraLiteralTrack` (can combine with `-IncludeLiteralTrack`) |
| Workspace health + two-track compression | `scripts/run_workspace_automation_health.ps1 -IncludeCompressionKpi -IncludeLiteralTrack` (optional; adds runtime vs `-IncludeCompressionKpi` alone) |

KPI summary (`reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json`) includes optional `literal_kpi` when `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json` is present.

Webhook alarm (`send_compression_kpi_alarm_if_needed.ps1`) evaluates **Track A `active_kpi` only**; Track B low saving does not by itself trigger that alarm.

## 5. Loss-pattern diagnostics

- **Script:** `scripts/report_compression_jaccard_loss_patterns.py`  
- **Output (Track A):** `reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_latest.json` (`--sla-track universal`)  
- **Output (Track B):** `reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_literal_latest.json` (`--sla-track literal`)  
- **Input join:** bench input `MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json` + active report for reconstructed text.

## 6. Revision

Bump version when caps, artifact paths, or Track B semantics change; cross-link from this file to Fact-Lock changelog entries.
