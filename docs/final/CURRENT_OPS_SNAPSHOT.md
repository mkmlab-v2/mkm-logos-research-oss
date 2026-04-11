# Current ops snapshot (ephemeral handoff)



**역할:** 새 Cursor 세션에서 `@docs/final/CURRENT_OPS_SNAPSHOT.md`로 붙이면, 직전 작전의 팩트만 빠르게 동기화한다.  

**성격:** 불변 SSOT가 아니다. 작전 종료·상황 변화 시 갱신하거나 비워도 된다.



**갱신일 (UTC):** 2026-04-12 (샤드 패치·0.70 재스윕 실측 반영)



## 연속 기억 (세션 핸드오프 — 권장)

- **새 Cursor 채팅:** `@docs/final/CURRENT_OPS_SNAPSHOT.md`를 우선 붙인다. 구현 여부·경로 판정이 필요하면 `@docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`. 장기 규약은 `AGENTS.md`, `CLAUDE.md`.
- **반복 금지 교훈 (NO_GO 클래스):** `docs/final/MKM_LESSONS_LEARNED_V1.md` — SSOT·레일·레짐·압축 측정·Git 추적 관련 5건; 상세 팩트는 여전히 `CONSTITUTION`·`artifacts`가 우선.
- **압축 벤치 혼동 방지:** `evaluate_report` 호출·브리지·스윕 차이는 `docs/final/COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1.md` (FAIL-COMP-004와 동일 선상).
- **역할 분리:** NotebookLM·옵시디언·아래 Vault 미러는 **브리핑·아카이브(B)**. “이미 구현·게이트 통과”는 **레포 스크립트·`docs/final/artifacts/*.json`(A)** 로만 단정한다.
- **H: 예전 작업 인제스트 (스냅 2026-04-09):** `G:\공유 드라이브\MKM_DATA_VAULT\vault\h_drive_knowledge_ingest\2026-04-09\` — `INGEST_SUMMARY_2026-04-09.txt`, `MATH_THEORY_INGEST_SUMMARY_2026-04-09.txt`, `manifest_h_drive_candidate_2026-04-09.csv` 등. `raw_mirror\`는 대량 아카이브·미러 성격.
- **H: 로컬 원본 트리 (지휘관 기록·레포와 트리 불일치):** 드라이브 `H:\`(라벨 `mkm`) — 특히 `H:\workspace\docs\` 아래 MD 다수(이론·가이드·일지 등; `docs\final` SSOT와 **동일 경로 아님**), `H:\workspace\daily\YYYY-MM-DD\notes.md`·`tasks.md`. 구현·게이트 판정은 **`C:\workspace` + CONSTITUTION**; H:는 **참고·연혁·초안**으로만 `@` 첨부해 조회.
- **NotebookLM 소스 Vault 미러:** `G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources\` — 레포 SSOT를 반영하려면 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` (마지막 동기 시각은 `vault\notebooklm_sources\_LAST_SYNC.txt`). 옵시디언 맥락까지 복사할 때 `-IncludeObsidianContext`. **권장 리듬:** 작전 전·주 1회 이상(스냅샷·매니페스트 갱신 후).
- **NotebookLM MCP:** Cursor에 `project-0-workspace-notebooklm-mcp`가 등록되어 있어도 **이 채팅에 도구가 주입되지 않으면** 호출 불가 — `.cursor/rules/notebooklm-mcp-session-bridge.mdc`. 로컬 MCP 툴 디스크립터는 `mcps/project-0-workspace-notebooklm-mcp/tools/` (`source_list`, `notebook_list`, `note`, `source_get_content` 등).
- **노트북 앵커·소스 목록:** `docs/NotebookLM_sources_manifest.md` 및 본 파일 하단「NotebookLM + Gemini」URL(메인 + **보조 2개**). **클라우드 노트북 안에만 있는 요약**은 이 레포가 자동으로 대체하지 않는다 — 필요 시 NotebookLM에서 소스로 유지하거나, 내보낸 파일을 레포/`notebooklm_sources` 경로에 두고 동기 스크립트로 미러한다。
- **노트북 전체 목록(서사 정비):** `docs/final/RESEARCH_HISTORY_V1.md` — 계정 소유 노트북 **제목·ID·소스 개수** 스냅샷(MCP `notebook_list`); 구현 SSOT 아님, 갱신 시 재수집。


## 로컬 LoRA (Windows, RTX 5060 Ti) — 현재 정답 경로



- **PyTorch `cu128` 빌드**가 **sm_120(Blackwell)** 과 맞는다. **`cu124` 안정 휠만 쓰면** `no kernel image is available` 가 난다.

- **권장 venv:** `c:\workspace\.venv_lora_local128` — `torch==2.9.1+cu128`, Unsloth·TRL 0.24+.

- **스크립트:** `scripts/train_mkm_prophecy_lora_unsloth.py` — TRL **0.24+** 에 맞게 `SFTConfig` + `processing_class` 사용.

- **원클릭:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LoraTrainLocal.ps1 --max-steps 10 --batch-size 1`

- **준비만(훈련 없음):** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LoraTrainLocalPrep.ps1`



## 자동화 스크립트



| 스크립트 | 용도 |

|----------|------|

| `scripts/Invoke-LoraTrainLocalPrep.ps1` | JSONL export + `--dry-run` |

| `scripts/Invoke-LoraTrainLocal.ps1` | `.venv_lora_local128`로 실제 LoRA 훈련 |

| `scripts/Invoke-GeneralProphecyPatchAndExport.ps1` | 패치 적용 + JSONL export |

| `scripts/Invoke-GeneralProphecyExportThenLora.ps1` | JSONL export + 연속 LoRA 훈련 (레지스트리 갱신 후) |

| `scripts/mkm_unified_mcp.py` | stdio MCP 통합 허브: 예언 레지스트리 조회 + `mkm_compressed_payload_v1` 검증·조립 (`scripts/requirements-mkm-mcp.txt`) |

| `scripts/lora_train_remote_gpu_bootstrap.sh` | (선택) Linux GPU 호스트용 부트스트랩 |



## 하드웨어 / OS



- GPU: NVIDIA GeForce **RTX 5060 Ti** — `torch.cuda.get_device_capability()` **(12, 0)** (sm_120).



## 검증된 소프트웨어 상태 (로컬)



| 구분 | PyTorch | 빌드 CUDA | 비고 |

|------|---------|-----------|------|

| **`.venv_lora_local128`** | 2.9.1+cu128 | 12.8 | **로컬 LoRA 훈련 성공** (2026-04-11, 3 steps smoke). |

| `.venv_lora` (구) | 2.5.1+cu124 | 12.4 | sm_120에서 CUDA 커널 실패 — **사용 안 함**. |

| 시스템 `py` | 2.9.1+cu128 등 | 12.8 | 전역; venv 권장. |



## LoRA 훈련 경로 (Fact-Lock)



- 스크립트: `scripts/train_mkm_prophecy_lora_unsloth.py`

- 기본 데이터셋: `data/training/macro_prophecy_dataset_v1.jsonl` (없으면 `py scripts/export_general_prophecy_to_jsonl.py`)

- 어댑터 출력(기본): `models/adapters/macro_prophecy_lora_v1`



## LoRA 데이터 시나리오 (NotebookLM 영감 — 1안 확정)



**선택:** **일반 예언 레지스트리 한 줄**로만 GPU LoRA 데이터를 만든다. NotebookLM은 **원문 저장소**가 아니라 **포인터·브리핑 출처**로만 쓴다.



| 단계 | 경로 | 역할 |

|------|------|------|

| 1 | `docs/final/artifacts/general_prophecy_latest.json` | `general_prophecy_registry_v1` — 질문·확률·`resolution_criteria`·`layer3_interpretation_ref` |

| 2 | `py scripts/export_general_prophecy_to_jsonl.py` | 위 JSON → `data/training/macro_prophecy_dataset_v1.jsonl` (instruction/output, `[HYPO]` 접두) |

| 3 | `Invoke-LoraTrainLocal.ps1` (또는 train 스크립트 직접) | GPU LoRA |



**포인터 반영 자동화:** `general_prophecy_registry_patch_v1` JSON을 만들고 `py scripts/apply_general_prophecy_registry_patches_v1.py --patch <파일>` 로 `general_prophecy_latest.json`의 **기존 `question_id`** 행에 `layer3_interpretation_ref` 등을 합친다 (NotebookLM API 직결 아님). 그다음 `export_general_prophecy_to_jsonl.py` → LoRA. **노트 전체 덤프를 JSONL에 직접 붓지는 않는다.**



**품질을 올리려면:** 레지스트리의 문항 수·`lens_rationale` 채움을 늘리고, 같은 체인으로 export → 스텝·에폭을 늘린 뒤 `eval_general_prophecy_brier_score.py` 등 **기존 B 레일 평가**로만 “성과”를 말한다.



## 압축: 이중 게이트 (KPI + strict-90 도메인)



- **KPI 게이트** (`docs/final/artifacts/general_compression_kpi_gate_v2.json`): `report_general_compression_kpi_gate.py`가 `general_compression_ab_result_summary_v1.json`을 읽어, treatment **평균 Jaccard ≥ 0.60**(·절약·민감 무결성)이면 **GO** 가능.
- **도메인 가드** (`docs/final/artifacts/general_compression_domain_guard_gate_v1.json`): `report_general_compression_failure_taxonomy.py` → `report_general_compression_domain_guard_gate.py`. strict 90% 스윕은 `general_compression_90pct_failure_taxonomy_v1.json`의 `failure_taxonomy`가 비면 **GO**.
- **가변 해상도 (코드):** `scripts/report_multilens_performance_eval.py`의 `evaluate_report`에서 실험 모드이고 글로벌 상한 `general_max_saving_rate >= 0.85`일 때, 입력 케이스의 `domain`별로 최대 절약률 상한을 둠(`policy_legal_lite` / `meeting` / `support_faq` — 상수 `_HIGH_STRESS_DOMAIN_MAX_SAVING`).
- **도메인 바닥 (정책):** `docs/final/artifacts/general_compression_domain_tolerance_v1.json` — 위 스윕 실측에 맞춰 `fidelity_floor`를 조정(2026-04-12 노트). 엔진 개선 없이 숫자만 느슨하게 한 것은 **아님**이라고 단정하지 말고, 재실행으로 재확인할 것.
- **측정 이원 (혼동 금지):** **일반 레일** A/B·스윕은 `docs/final/artifacts/general_compression_eval_input_v1.json` 기준 9케이스 요약이다. **V2 극복원**은 별 트랙으로 `py scripts/run_ultra_compression_default.py --mode ultra-literal` → `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json` (갱신 시 `compression_metrics.avg_reconstruction_fidelity_jaccard` 확인; 2026-04-12 실측 예: **~0.992**, global 절약 **~0.13**).
- **고바닥 스윕 실측:** `docs/final/artifacts/extreme_quality_sweep_v1.json` — `py scripts/run_general_compression_sweep.py --fidelity-floor 0.80 --out …` 결과 **`go_candidate_count`: 0** · **`decision`: NO_GO** (현 그리드에서 baseline 대비 절약 개선 + Jaccard≥0.80 동시 만족 조합 없음).
- **0.70 바닥 스윕 실측:** `docs/final/artifacts/realistic_quality_sweep_v1.json` — `--fidelity-floor 0.70` 결과 **`go_candidate_count`: 0** · **`decision`: NO_GO**. 동일 9케이스·그리드에서 최고 평균 Jaccard는 **~0.671** 수준이라 **0.70 바닥 자체를 넘는 조합이 없음** (0.80과 동일하게 빈 집합이나, 원인은 “바닥이 현재 도달 가능 상한(~0.67)보다 높음”).
- **샤드 soft-term 패치 후 0.70 재스윕:** `docs/final/artifacts/general_compression_sweep_after_shard_patch_v1.json` — `shard_patch_proposal_v1` 5토큰을 `codebook/shards/zone_{a,b,c,d}_*.json`의 `must_keep_soft_terms`에 반영 후 동일 입력·그리드 재실행. **최고 Jaccard ~0.671** · **`decision`: NO_GO** (수치는 `realistic_quality_sweep_v1`과 동일). 9케이스 레일과 V2 손실 패턴 제안의 **벤치 불일치** 가능; 상향은 V2/`evaluate_report` 쪽 재측정으로 확인.
- **V2 A/extreme + 샤드 soft-term 병합 (2026-04-12):** `evaluate_report`가 **strategy=A · intensity=extreme**에서도 샤드 `must_keep_soft_terms`를 병합하도록 변경(`C/high`와 함께). 동일 V2 입력·AB_OFF 캡 재측정: `docs/final/artifacts/MULTILENS_V2_A_EXTREME_WITH_SHARD_SOFT_TERMS_V1.json` — 평균 Jaccard **~0.751** · 절약 **~0.480** (soft 미병합·동일 캡 시 **~0.735** / **~0.491**, 동결 스냅샷 `MULTILENS_BRIDGE_POLICY_AB_OFF_V1.json`). 참고: `MULTILENS_V2_STRATEGY_C_HIGH_AFTER_SHARD_PATCH_V1.json`은 **C/high** 별 프로파일(**~0.899** Jaccard / **~0.266** 절약)으로 AB_OFF와 직접 비교 금지.
- **샤드 패치 정밀 정찰 (2026-04-12):** `reports/constitution/btrack_pilot/precision_reconnaissance_shard_patch_v1.json` — `generate_shard_patch_proposal_v1` 다단계 스윕(strict **global≥3 · conc≥0.75** → 후보 0; strict **g2 · c0.65** → 이미 배포 3토큰만; **permissive g1 · c0.55** 풀 141건) 후 샤드 기존 용어 제외·순위: **next_10** / **next_10_korean** 초안 + 경고. 병합 전 수동 검토·V2 재측정 권장.
- **유실 패턴 갱신 (0.751 기준선):** `py scripts/report_compression_jaccard_loss_patterns.py --active-report docs/final/artifacts/MULTILENS_V2_A_EXTREME_WITH_SHARD_SOFT_TERMS_V1.json` → `reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_latest.json` (동일 내용 스냅샷: `compression_jaccard_loss_patterns_v2_a_extreme_soft_terms_v1.json`) → `aggregate_compression_jaccard_loss_patterns.py`. 갱신 후 `generate_shard_patch_proposal_v1` 기본 후보는 **1건**(`quality`, zone_b_timing/ssot)으로 수렴 — 대부분의 반복 유실은 이전 soft-term 패치로 이미 흡수된 상태로 해석 가능.
- **9케이스 유실 토큰 집계 (V2와 분리):** `py scripts/report_general_compression_token_loss_aggregate.py` → `docs/final/artifacts/general_compression_token_loss_aggregate_v1.json` — 스윕 최적 프로파일(A/high/0.55/0.6/0.6)과 동일하게 `evaluate_report` 한 번 돌려 **전역·도메인별 상위 `lost` 토큰**을 JSON으로 고정 (재현용).
- **4D 브리지 정책 A/B (V2 universal, 동일 캡):** `run_ultra_compression_default.py --mode universal --out …` vs `--apply-gematria-4d-bridge-policy` — 산출 `MULTILENS_BRIDGE_POLICY_AB_OFF_V1.json` / `MULTILENS_BRIDGE_POLICY_AB_ON_V1.json`. 실측(2026-04-12): OFF Jaccard **~0.735**·절약 **~0.491** → ON **~0.854**·절약 **~0.361** (품질↑·절약↓).
- **갱신:** `py scripts/report_general_compression_failure_taxonomy.py` → `py scripts/report_general_compression_domain_guard_gate.py`



## B 레일: 패치 → JSONL (Fact-Lock 체크리스트)



**산출 이름 (혼동 방지):**

- 레지스트리 SSOT(머지 대상): `docs/final/artifacts/general_prophecy_latest.json`

- LoRA용 학습 JSONL(export 기본 출력): **`data/training/macro_prophecy_dataset_v1.jsonl`** — `general_prophecy_latest.jsonl` 같은 이름은 쓰지 않는다.



**멱등성:** 동일한 패치 파일을 반복 적용하면 **같은 필드가 같은 값으로 덮어쓰기**된다. 패치 내용이 바뀌면 결과도 바뀐다.



**무인 완주 금지:** 패치 JSON은 **에이전트 1턴 자동 적용**을 기대하지 말고, **diff 또는 스키마 확인 후** 실행한다. MCP·세션·`question_id` 불일치 시 실패할 수 있다.



**NotebookLM MCP 브릿지:** 노트·브리핑은 **초안·포인터 문자열**만 레포로 옮긴 뒤, **`general_prophecy_registry_patch_v1`**로 `layer3_interpretation_ref` 등을 채운다. 노트 전체를 JSONL에 직접 붓지 않는다.



**마스터 커맨드 (패치 + export 한 줄):**

```powershell

Set-Location c:\workspace

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-GeneralProphecyPatchAndExport.ps1 -Patch <path\to\patch.json>

```

검증만: `-DryRun` (레지스트리 미변경, export 생략).



**학습까지:** export는 위까지. GPU LoRA는 별 단계 — `Invoke-LoraTrainLocalPrep.ps1`(export+dry-run) 또는 `Invoke-LoraTrainLocal.ps1`.

**export → LoRA 한 번에 (패치 없이 레지스트리만 이미 갱신된 경우):**

```powershell

Set-Location c:\workspace

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-GeneralProphecyExportThenLora.ps1 --max-steps 10 --batch-size 1

```



## NotebookLM MCP 플레이북 (패치 초안 → Fact-Lock)



1. **도구 주입 확인:** 이 Cursor 채팅에 NotebookLM MCP가 실제로 붙어 있는지 본다. UI만 녹색이면 부족할 수 있음 — `.cursor/rules/notebooklm-mcp-session-bridge.mdc`.

2. **레지스트리에서 `question_id` 확정:** `docs/final/artifacts/general_prophecy_latest.json` 안에 있는 ID만 패치 대상으로 쓴다. 없는 ID는 `apply` 단계에서 exit 2.

3. **노트·출처:** MCP `note_list` / 노트 본문으로 브리핑을 읽고, 레포에 둘 **포인터 MD 경로**가 있으면 그 문자열을 `layer3_interpretation_ref` 후보로 쓴다. 노트 전문을 JSONL에 붙이지 않는다.

4. **패치 파일 작성:** 스키마 `general_prophecy_registry_patch_v1`, 샘플 `tests/fixtures/general_prophecy_registry_patch_sample_v1.json` 참고.

5. **사람 검증:** 저장 후 diff·필드명 확인 → `-DryRun`으로 apply 검증.

6. **적용 + 산출:** `Invoke-GeneralProphecyPatchAndExport.ps1 -Patch <파일>` → 필요 시 `Invoke-GeneralProphecyExportThenLora.ps1`으로 LoRA까지.



## MKM unified MCP (stdio 허브)



- **역할:** `project-0-workspace-compression-server`를 대체하지 않는다. **예언 레지스트리 Fact-Lock 조회**와 **`mkm_compressed_payload_v1` 봉투 검증**을 한 stdio 프로세스로 제공한다.

- **의존성:** `pip install -r scripts/requirements-mkm-mcp.txt`

- **실행:** Cursor **Settings → MCP**에 stdio로 `py scripts/mkm_unified_mcp.py`(cwd: 레포 루트)만 등록한다. **일반 터미널에서 직접 실행하지 않는다**(빈 줄이 JSON-RPC 오류를 유발). 디버그만 `MKM_MCP_FORCE_STDIO=1`.

- **환경:** `MKM_PROPHECY_REGISTRY_PATH`로 레지스트리 JSON 경로를 덮어쓸 수 있다 (기본: `docs/final/artifacts/general_prophecy_latest.json`).

- **도구:** `prophecy_registry_summary`, `prophecy_get_question`, `mkm_payload_validate`, `mkm_payload_build`



## 재현 명령 (로컬 권장)



```powershell

Set-Location c:\workspace

.\.venv_lora_local128\Scripts\python.exe scripts\train_mkm_prophecy_lora_unsloth.py --max-steps 10 --batch-size 1

```



## NotebookLM + Gemini (작전 브리핑 동기화)



- **지휘관 워크플로**: Gemini 쪽에서 NotebookLM 노트북을 **컨텍스트로 연결**해 작전 브리핑·지시 초안을 쓸 수 있으면, 아래 **동일 URL**을 레포 SSOT(`docs/NotebookLM_sources_manifest.md` · 본 절)와 맞춘다.
- **노트북 앵커 (메인)**  
  - https://notebooklm.google.com/notebook/347e5cbe-0ade-4615-9aac-8747d4fa644e  
  - https://notebooklm.google.com/notebook/71f55a03-09d0-411f-b365-0ce2a2064c24  
- **보조 (B 궤적 · 매니페스트 동일 SSOT)**  
  - https://notebooklm.google.com/notebook/978ab6ca-d069-4a78-8916-30c7844c4fa6  
  - https://notebooklm.google.com/notebook/d193d8d4-5678-4cc7-8eb6-7046a9a3b16d  
- **한계**: 브리핑은 **참고**이며, “이미 구현·이미 통과” 같은 판정은 **레포 스크립트·산출 JSON**으로만 한다. MCP/NotebookLM 세션 미주입 시 도구 호출 불가 — `.cursor/rules/notebooklm-mcp-session-bridge.mdc`.



## 운영 원칙



- 이 파일은 **레인 합선 방지**: 압축 엔진(A/B Track)과 역할을 섞지 않는다. 장기 불변 규약은 `AGENTS.md`, `CLAUDE.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`를 따른다.



### 자동화 기동 마스터 페이로드 (One-Shot Execute) — 복붙 계약



복붙용 — 에이전트에게 그대로 전달:



> 현재 활성화된 NotebookLM의 최신 통찰을 읽어 `general_prophecy_registry_patch_v1` 초안을 작성하라. 이후 `apply` dry-run → 실제 적용 → `export_general_prophecy_to_jsonl` → `pytest` 검증까지 **중간 승인 없이(TITAN Mode)** 완주하고, 최종 결과와 0.70 스윕 가능 여부만 요약 보고하라.



**Fact-Lock:** NotebookLM MCP가 이 채팅에 주입되지 않았으면, 노트·포인터는 `docs/final/CURRENT_OPS_SNAPSHOT.md`의 NotebookLM 절·레포 MD 경로에 맞춰 **수동으로** 초안을 만든 뒤 동일 체인을 실행한다. 루트 `.cursorrules`의 **고위험 승인 예외**(실거래·파괴적 삭제·비가역 스키마 등)는 이 페이로드로 면제되지 않는다. `0.70 스윕`의 정의·근거는 팀이 쓰는 스크립트·산출물 기준으로만 보고한다.


