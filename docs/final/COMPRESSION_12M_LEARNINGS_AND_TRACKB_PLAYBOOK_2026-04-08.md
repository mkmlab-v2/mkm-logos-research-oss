# Compression 12M Learnings + Track B Playbook (Fact-Safe)

## 1) Session Fact Check (Completed Now)

- NotebookLM Hub B mirror sync executed:
  - Command path: `scripts/Invoke-HubBWeeklyMirror.ps1`
  - Latest log: `reports/hub_b_weekly_mirror_log.jsonl`
  - Latest record: `exit_code=0`, `step=vault_mirror` (2026-04-08 run)
- This document uses repository artifacts only; no unverifiable external performance claims.

## 2) What We Actually Built (12M compression lane snapshot)

Representative evidence (not exhaustive):

- General compression lane:
  - `docs/final/artifacts/general_compression_ab_result_summary_v1.json`
  - `docs/final/artifacts/general_compression_kpi_gate_v2.json`
  - `docs/final/artifacts/general_compression_benchmark_manifest_v1.json`
- Multi-lens compression lane:
  - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`
  - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json`
- Genesis v3/v3.1 lane:
  - `docs/final/artifacts/comparison_summary_latest.json`
  - `docs/final/artifacts/genesis_v3_multimap_mixed_api_finance_v1_latest.json`
  - `docs/final/artifacts/tracka_vs_zstd_native_bench_latest.json`

## 3) Key Learnings (Hard Lessons)

1. **Claim boundary failure risk**
   - Repeated drift from simulation metrics to billing/VRAM marketing claims caused decision noise.
2. **Benchmark ordering mistake**
   - Build-first, market-check-later sequence created rework risk.
3. **Track A originality overestimation**
   - Shared dictionary patterns overlap with established techniques; moat is not in raw compression primitive.
4. **Control-plane value is real**
   - Route policy, isolation, fallback, audit artifacts are defensible operational value.
5. **Backend reality**
   - In current 10MB bench, native zstd dictionary path outperformed pointer pipeline (`tracka_vs_zstd_native_bench_latest.json`).

## 4) Anti-Repeat Guardrails (Mandatory)

Before any new compression feature merge, all 4 gates must pass:

1. **Market-overlap gate**
   - Must document overlap with native/vendor features and explain residual moat.
2. **Cost-of-operations gate**
   - Must quantify sync/update/deploy overhead vs measured benefit.
3. **Fact-safe claim gate**
   - Must map every external sentence to one artifact key/path.
4. **Fallback integrity gate**
   - Must show deterministic fallback behavior and `decode_check_ok` equivalent.

If any gate fails: feature remains research-only.

## 5) Track A Policy (Freeze / Narrow Use)

- Track A remains useful only as:
  - research scaffold,
  - control-plane policy harness,
  - niche constrained-network use cases.
- Track A is **not** default growth thesis for broad B2B billing reduction.
- Default backend preference in experiments: native zstd dictionary route when applicable.

## 6) Track B Execution Focus (What To Do Well Next)

Primary lane: quaternion restore/generalization research with strict governance.

Immediate evidence anchors:

- `docs/final/TRACKB_QUATERNION_RESTORE_DECISION_MEMO_V2_2026-04-08.md`
- `docs/final/artifacts/trackb_quaternion_two_stage_gate_v2.json`
- `docs/final/artifacts/trackb_quaternion_restore_bridge_v1.json`

Execution priorities:

1. Expand Track B stress grid (`length>=7`, higher OOV bins, adversarial variants).
2. Keep GO/HOLD research gate explicit; no production merge without separate latency/memory checks.
3. Produce weekly Track B delta bundle with:
   - exact restoration stats,
   - collision metrics,
   - runtime/memory trend,
   - failure cluster drift.

## 7) 14-Day Practical Plan

Day 1-2:
- Freeze Track A scope in decision docs (no new broad-market claims).
- Standardize one benchmark manifest template for Track B runs.

Day 3-7:
- Run expanded Track B grid and generate failure cluster diffs.
- Add reproducibility checks (seed, schema, command fingerprint).

Day 8-14:
- Use **§9** as the promotion-readiness checklist (research-only default; fill numeric thresholds when product owner locks them).
- Only if all §9 gates pass for a named scope, draft route-specific production readiness (Hostinger/VPS checklist remains separate).

## 8) Non-Negotiable Reporting Rule

All summaries must start with:

- what was measured,
- where the artifact is,
- what is explicitly out of scope.

No artifact, no claim.

## 9) B-track → Track A / production promotion readiness (checklist v1, 2026-04-10)

**Status:** default **no promotion** — B-track and research artifacts stay `research_only` / `GO_RESEARCH` until this checklist is completed for a **named scope** (route, daemon, billing surface). NotebookLM·브리핑은 참고만; 통과 여부는 레포 산출물·CI·지휘관 승인으로만 기록한다.

### 9.1 Scope and approval (all required)

- [x] **Named scope** in writing: `POST /v1/compress`, `POST /v1/expand`, `POST /v1/metering/log` (compression lane candidate). **Exclude by default:** `POST /v1/research/l1_side_channel/wire` unless separately approved as research-exposed.
- [x] **Command fingerprint**: script path + argv + git commit hash recorded in `docs/final/artifacts/bench_l1_api_load_latest.json.command_fingerprint` (includes `bench_script`, `argv`, `git_commit`, and `mkm_user_context_included` when `--mkm-user-context-json` is used).
- [x] **No conflation**: side-channel `exact_restore_rate = 1.0` harness (`run_l1_permutation_channel_integrated_spike.py` + artifact) is **not** evidence for LLM-beam or Track A compress; promotion claims require a **new** artifact under the same decoding assumptions.

#### 9.1.1 승격 후보 범위·성능 계약 초안 (지휘관 입력용, 2026-04-10)

**OpenAPI SSOT와 경로 이름 정렬:** 계약 파일은 `docs/final/openapi_token_compression_stub_v1.yaml` 이다. 예시로 드는 승격 후보·제외는 아래와 같다(최종 조합은 지휘관이 체크).

| 구분 | 경로 / 대상 |
|------|-------------|
| 상용 후보(예시) | `POST /v1/compress`, `POST /v1/expand`, `POST /v1/metering/log` — 실제 승격 시 **이 중 어디까지** 포함할지 명시 |
| 연구 노출(기본 비상용 주장) | `POST /v1/research/l1_side_channel/wire` — 스텁·와이어 코덱 검증용; 상용 SLA와 **합쳐서** 말하지 않음 |
| 증거 혼동 금지 | 사이드채널 통합 스파이크의 exact 복원은 **그 하네스 가정**에서만 FACT; 빔 역추론 요약 JSON·Track A compress와 **동일 근거로 승격** 금지 |
| §9 밖 연구 | OOV·Mamba 등 전방 벤치 — 별도 스코프·메모 없으면 승격 게이트에 넣지 않음 |

**성능 숫자(잠금 전에는 TBD):** P95 지연·피크 RSS는 **비즈니스/인프라 예산**과 **실측 분포** 없이 임의 기입하지 않는다. 절차는 (1) 동일 입력·동일 환경에서 반복 측정 → (2) 분포 확보 → (3) 임계 합의 → (4) 아래 9.2 표·본 절 갱신.

### 9.2 Metric and artifact gates (fill thresholds when locked; until then mark TBD)

| Gate | SSOT / artifact | Pass criterion (draft) |
|------|-----------------|-------------------------|
| L1 inverse (beam) baseline | `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json` | Re-run reproduces `aggregate.*` within agreed tolerance; prose uses same file’s `generated_at_utc`, `scoring_mode`, `research_only` (`MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md` §D drift guard). |
| Track B weekly semantic SSOT | `docs/final/artifacts/trackb_semantic_eval_*_latest.json`, `trackb_weekly_gate_recheck_latest.json` | Operational gate metric remains **Jaccard** unless `CONSTITUTION` / playbook is formally revised; `cosine_tokens` and embedding backends stay parallel research unless promoted by separate memo. |
| Latency | `scripts/bench_l1_api_load.py` → `docs/final/artifacts/bench_l1_api_load_latest.json` | **[DRAFT target]** P95 **200** ms vs `latency_ms.p95` (client-observed RTT). **[FACT]** only after artifact records `generated_at_utc`, git hash in run notes, and stub fingerprint per §9.1. Input proxy: **~1,000 words** repeated token (`--approx-words`). |
| Memory | same artifact + optional `--server-pid` (psutil, same host) | **[DRAFT target]** peak RSS **2.5 GiB** process under test. **4 GiB host = OOM risk**; draft infra **8 GiB RAM**. **[FACT]** requires sampled `server_rss_bytes_*` or documented measurement method; client-only bench does **not** prove server peak. |
| RS/ECC | `scripts/run_mkm_l1_parity_prototype.py` lineage | **Not** a promotion blocker description for “parity prototype”; full RS pipeline + error-injection bench required before any “FEC production” claim (`FACTCHECK_GEMATRIA_ENGINEERING_REPRODUCIBILITY_2026-04-09.md`). |
| Compression SLA / pilot tone | `docs/final/COMPRESSION_SLA_POLICY_V1.md`, `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` §10 | Partner brief avoids 100% lossless / RS production / external bpb as MKM12 service facts unless matching artifacts exist. |

#### 9.2.1 [DRAFT] 성능 목표 (측정 전 — FACT 아님)

다음은 **잠정 목표(draft target pending bench)**이다. `1.5 GiB 오라클 코드북 상주` 등은 레포 팩트체크상 **[HYPO]/미검증**일 수 있어, **확정 SLA로 대외 발표 금지**.

| 지표 | 잠정 목표 | 검증 | 비고 |
|------|-----------|------|------|
| P95 지연 | **200 ms** | 동일 페이로드·100회·동시 10 (`bench_l1_api_load.py` 기본) | 클라이언트 RTT; 스텁·네트워크·디스크에 민감 |
| 피크 RSS | **2.5 GiB** (단일 프로세스) | `--server-pid` + `psutil` 동일 호스트 | **4 GiB RAM 호스트 비권장** |
| 인프라 (초안) | **8 GiB RAM** VPS | 벤치 JSON에 `infra` 메모 수동 기록 권장 | 커널/캐시 여유 |
| 부하 | **최대 동시 10** 기본 | `--max-concurrent`, `--total-requests` 조정 가능 | RPS 상한은 운영에서 별도 정의 |

### 9.3 Automation references (smoke, not a substitute for §9.1)

- L1: `.github/workflows/l1-inverse-decoder-smoke.yml`, `l1-inverse-decoder-nightly-sweep.yml`
- Track B research: `.github/workflows/trackb-research-smoke.yml`, `scripts/Run-TrackBWeeklyRefresh.ps1`
- Token API stub contract: `docs/final/openapi_token_compression_stub_v1.yaml` v1.1.0+; implementation row: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §2
- §9.2 draft SLA bench (stub must be running unless `--dry-run`): `scripts/bench_l1_api_load.py` → `docs/final/artifacts/bench_l1_api_load_latest.json`

**CI vs local bundle:** GitHub `l1-inverse-decoder-smoke.yml` runs the **same pytest targets as below** and **adds** `python scripts/run_l1_inverse_decoder_spike_test.py --samples 24 …` (single-run spike). So: **local bundle ⊆ smoke**; passing locally is necessary but not sufficient for §9.1.

**Local pytest bundle (Fact-Lock pre-flight, ~1s):** does not satisfy §9.1 alone; use before PRs that touch L1 wire / OpenAPI / summary SSOT.

```bash
pytest tests/test_l1_inverse_decoder_summary_schema.py \
  tests/test_l1_side_channel_wire_codec.py \
  tests/test_compression_token_api_stub.py::test_openapi_includes_l1_side_channel_wire_path \
  tests/test_compression_token_api_stub.py::test_l1_side_channel_wire_research_endpoint_roundtrip \
  -q --tb=short
```

### 9.4 Related production checklists (orthogonal)

- Trading / staging: `projects/bitcoin-trading/docs/final/STAGING_TO_PRODUCTION_PROMOTION_CHECKLIST_2026-03-25.md` — does **not** replace §9 for compression research → API claims.
