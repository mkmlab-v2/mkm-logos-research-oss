# Current ops snapshot (ephemeral handoff)



**역할:** 새 Cursor 세션에서 `@docs/final/CURRENT_OPS_SNAPSHOT.md`로 붙이면, 직전 작전의 팩트만 빠르게 동기화한다.  

**성격:** 불변 SSOT가 아니다. 작전 종료·상황 변화 시 갱신하거나 비워도 된다.



**갱신일 (UTC):** 2026-04-12



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



## 재현 명령 (로컬 권장)



```powershell

Set-Location c:\workspace

.\.venv_lora_local128\Scripts\python.exe scripts\train_mkm_prophecy_lora_unsloth.py --max-steps 10 --batch-size 1

```



## NotebookLM + Gemini (작전 브리핑 동기화)



- **지휘관 워크플로**: Gemini 쪽에서 NotebookLM 노트북을 **컨텍스트로 연결**해 작전 브리핑·지시 초안을 쓸 수 있으면, 아래 **동일 URL**을 레포 SSOT(`docs/NotebookLM_sources_manifest.md` · 본 절)와 맞춘다.
- **노트북 앵커**  
  - https://notebooklm.google.com/notebook/347e5cbe-0ade-4615-9aac-8747d4fa644e  
  - https://notebooklm.google.com/notebook/71f55a03-09d0-411f-b365-0ce2a2064c24  
- **한계**: 브리핑은 **참고**이며, “이미 구현·이미 통과” 같은 판정은 **레포 스크립트·산출 JSON**으로만 한다. MCP/NotebookLM 세션 미주입 시 도구 호출 불가 — `.cursor/rules/notebooklm-mcp-session-bridge.mdc`.



## 운영 원칙



- 이 파일은 **레인 합선 방지**: 압축 엔진(A/B Track)과 역할을 섞지 않는다. 장기 불변 규약은 `AGENTS.md`, `CLAUDE.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`를 따른다.


