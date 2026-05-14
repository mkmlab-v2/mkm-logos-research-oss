# MKM — 쇼룸 운영 마감 + Pack 0-B 작업 일정 v1

**schema:** `mkm_showroom_ops_and_pack0b_work_schedule_v1`  
**last_updated_utc:** 2026-05-16  
**목적:** Track C 공개 쇼룸 파이프라인(로컬 개통 이후)과 **Pack 0-A/0-B** LoRA 전선을 **순서·DoD**로 고정한다.  
**채팅창·임무 추적:** 루트 **`MISSION_LOG.md`**(로컬 비추적)에 Phase 완료·Evidence 한 줄씩 남긴다. **옵시디언**은 개인용·그래프용으로만 쓰고 Fact-Lock SSOT로 자동 승격하지 않는다(`AGENTS.md`·`CENTRAL` 동일 방향). (선택) Ops 한 줄 요약만 `reports/daily_thread_work_YYYY-MM-DD.md` + `athena_daily_thread_log_sync_v1.py`. **CENTRAL에는 본 일정 본문을 올리지 않는다.**

---

## 운영 원칙 (고정)

1. **Pack 0-A(Control-Integrity)** 회귀는 Pack 0-B 본격 작업 전 **항상 녹색** (`docs/final/LORA_PACK_V0_DOD_V1.md` §3).  
2. **한의 CDS·환자 번들** 축은 **Hold** — 기능 확장보다 기존 회귀(예: Fact-Lock 번들 **3e**, `run_fact_lock_bundle.ps1`) 유지.  
3. **LoRA 스프롤 금지** — 공식 LoRA 팩 라인은 문서상 **0-A / 0-B**만; 새 팩은 별도 DoD·법무·골든 스키마 없이 추가하지 않는다.

---

## Phase 0 — 게이트 스모크 (반나절 이내)

**목표:** 0-A 기준선 확인 후 일정 착수.

- [x] `py -m pytest tests/test_mkm_control_integrity_pipeline_smoke_v1.py -q` → exit 0 — **2026-05-16** 7 passed  
- [x] (선택) `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1` → exit 0 — **2026-05-16** 719 paths  

**완료 조건:** 위 최소 1종 통과 기록(날짜·명령 한 줄을 본 문서 하단 Log에 남김).

---

## Phase 1 — 쇼룸 로컬 체인 재검증 (이미 개통 시 생략 가능)

**목표:** 로컬에서 번들·검증 일관성 확인.

- [x] `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/build_showroom_track_c_bundle_chain_v1.ps1` → exit 0  
- [x] 산출 확인: `docs/final/artifacts/showroom_public_bundle_v1.json` 내 `observability.topology_radar_snapshot_present` 등  
- [x] (선택) **Visualization v0 thin:** 체인 **(5/5)**가 `showroom_trust_visualization_slice_v0.json`을 갱신 — 동 폴더 `public_showroom_trust_visualization_v0.html`은 HTTP로 JSON fetch( `file://` 제한 참고 )  

**참조:** `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` (Track C 원클릭 체인 절).

**완료 조건:** 체인 exit 0 + 번들 필드 확인 한 줄 기록.

---

## Phase 2 — 스테이징·본선 동기 (운영 신뢰 표면)

**목표:** 로컬을 넘어 **스테이징 또는 VPS 웹 루트**에 정적 자산 반영 및 HTTP 확인.

- [x] 로컬 스테이징: `pwsh … -File projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1` (또는 `-WebRoot` / `JEMAAI_WEB_ROOT`) — **2026-05-16** `-WorkspaceRoot c:\workspace` 실행 **exit 0** → 기본 `projects/bitcoin-trading/ops/windows-rehearsal/.showroom_staging/` 에 8파일(폴·미니멀 보드·`showroom_public_bundle_v1.json`·topology·Trust viz HTML/JSON·사주 HTML/JSON).
- [x] (본선) `scripts/sync_showroom_to_vps.ps1` → **2026-05-14** `scp` exit 0 (`/var/www/jemaai/`). 비대화형 키 검증 버그 수정: `Test-HasIdentityArgs` 매개변수명이 PowerShell 자동 `$args`와 충돌해 `-i`가 무시되던 문제 → `$ScpLeadingArgs`로 변경(`sync_showroom_to_vps.ps1`).  
- [x] SPEC(로컬 분기): 스테이징 `showroom_public_bundle_v1.json` **JSON 파싱 OK**; `public_showroom_board_minimal.html`에 `data-disclaimer-ref="jemaai_showroom_v1"` 존재(`JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` §3·§4 정합). **§4.1** `curl` `public-events/ingest` 스모크는 **`127.0.0.1:8788` 게이트웨이 기동 + `PUBLIC_EVENT_GATEWAY_TOKEN`** 전제로 운영 호스트 또는 로컬 E2E에서 수행.

**완료 조건:** 대상 URL 또는 호스트에서 `200` + 캐시 정책 확인(가능한 범위) 한 줄. — **2026-05-14:** `https://jemaai.cloud/public_showroom_poll.html` HEAD **200** (VPS `scp` 직후).

---

## Phase 3 — 쇼룸 반복 자동화 (선택)

**목표:** 주간/일일로 체인만 재실행해도 되도록 **스케줄 또는 문서상 루틴** 고정.

- [ ] Task Scheduler: **미등록 기본(권장)** — 필요 시에만 등록(작업명·인자 `build_showroom_track_c_bundle_chain_v1.ps1` 또는 아래 원클릭과 동일 동작인 `sync_showroom_to_vps.ps1 -RefreshStaging` 기록).  
- [x] 문서상 **권장 수동 루틴** 고정(본 절 아래 블록).

**완료 조건:** “누가 언제 어떤 명령”이 한 블록으로 적힘。

**권장 루틴 v1 (수동, 주 1회):** **운영자(지휘관 PC)** · **매주 월요일 로컬 작업 시작 시**(또는 Track C 공개면 갱신 직전) · 모노레포 루트 `C:\workspace`에서 **한 줄**:

```text
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/sync_showroom_to_vps.ps1 -WorkspaceRoot c:\workspace -RefreshStaging -SkipDotenvUserSync
```

- `-RefreshStaging`: `build_showroom_track_c_bundle_chain_v1.ps1` → `deploy_showroom_static.ps1` → `scp`까지 연쇄(`sync_showroom_to_vps.ps1` 본문 SSOT).  
- `-SkipDotenvUserSync`: User 환경에 `MKM_VPS_*`·`MKM_VPS_SCP_EXTRA_ARGS`가 이미 맞춰진 PC 기본. **`.env`에서 VPS 관련 키를 바꾼 직후**에는 생략하지 말고(동 스크립트 기본 선행) `sync_required_env_to_user.ps1` 한 번 또는 본 명령에서 `-SkipDotenvUserSync` 제거.  
- 점검: `Invoke-WebRequest -Uri "https://jemaai.cloud/public_showroom_poll.html" -Method Head` → **200**(도메인·경로는 배포 SSOT와 정합 시).

---

## Phase 4 — Pack 0-B 데이터 N/K (명리 결정론 골든)

**목표:** `LORA_PACK_V0_DOD_V1.md` §0.1 — train ≥ **1000**, locked_eval ≥ **100**.

- [ ] `scripts/build_myeongri_deterministic_lora_golden_bulk_v1.py` (시드·`dataset_version`·매니페스트·`sha256`) 실행 및 매니페스트 검증  
- [ ] 대량 JSONL은 `.gitignore` 정책 경로에만 두고 **커밋하지 않음**  

**참조:** `docs/final/LORA_PACK_V0_DOD_V1.md`, `scripts/prep_myeongri_deterministic_lora_golden_v1.py`  

**완료 조건:** 매니페스트상 `train_rows` / `locked_eval_rows`가 DoD 이상.

---

## Phase 5 — Pack 0-B 평가

**목표:** 골든 핏 리포트 산출.

- [ ] `scripts/eval_myeongri_deterministic_lora_golden_fit_v1.py` → `reports/myeongri_deterministic_lora_golden_fit_latest.json`  

**완료 조건:** 스크립트 exit 0 + 리포트 경로 기록.

---

## Phase 6 — Pack 0-B 학습·프로모션 (선택 · GPU·호스트 의존)

**목표:** 프로파일·어댑터 경로 SSOT 준수 후 학습 및 (정책대로) 프로모션 게이트.

- [ ] `docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json` 확인 (`pack: "0-B"`)  
- [ ] (선택) 학습 호스트에서 어댑터 산출·`check_mkm_*promotion*` 계열 게이트 — 경로는 CONSTITUTION §1.2.1 인근 및 `LORA_PACK_V0_DOD_V1.md`  

**완료 조건:** 게이트 `decision=GO` 또는 “의도적 보류” 사유 한 줄.

---

## Phase Hold — 한의 CDS·환자 번들

- [ ] 변경 없음; PR·주간 점검 시 `run_fact_lock_bundle.ps1` **3e** 생략하지 않기 (`-SkipKmPhysicianCdsEnvelope` 남용 금지).

---

## 진행 로그 (수동 append)

| 날짜 (UTC) | Phase | 메모 |
|------------|-------|------|
| 2026-05-14 | 1 | 예: 로컬 체인 exit 0, topology ref_count=5 |
| 2026-05-14 | 2 | `sync_showroom_to_vps.ps1` scp OK; `Test-HasIdentityArgs` `$args`→`$ScpLeadingArgs` fix; `https://jemaai.cloud/public_showroom_poll.html` HEAD 200 |
| 2026-05-14 | 2 | 재실행: `build_showroom_track_c_bundle_chain_v1.ps1` exit 0 → `deploy_showroom_static.ps1 -WorkspaceRoot c:\workspace` → `.showroom_staging/` 8파일; bundle JSON 파싱 OK; `data-disclaimer-ref="jemaai_showroom_v1"`; `pytest tests/test_validate_showroom_public_bundle.py` 12 pass |
| 2026-05-14 | 2 | 권장 자동 루프: `scripts/sync_showroom_to_vps.ps1 -RefreshStaging -SkipDotenvUserSync` exit 0 (체인+deploy+`scp` → `/var/www/jemaai/`); 이어 `verify_p0` 719 OK; `pytest` `test_mkm_control_integrity_pipeline_smoke_v1`+`test_validate_showroom_public_bundle` 19 pass |
| 2026-05-14 | 3 | 권장=문서 수동 루틴: 주 1회 `sync_showroom_to_vps.ps1 -RefreshStaging`(Phase 3 DoD) |
| 2026-05-16 | 0 | Control-Integrity smoke 7 passed; `verify_p0` 719 OK; 워킹트리 쇼룸 스테이징 추적 파일은 HEAD 기준 복원(로컬 체인 잡음 제거) |

---

## 관련 SSOT (복붙용 경로)

| 항목 | 경로 |
|------|------|
| LoRA Pack DoD | `docs/final/LORA_PACK_V0_DOD_V1.md` |
| 헌법(구현·CI) | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` |
| 쇼룸 SPEC | `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` |
| 원클릭 체인 | `scripts/build_showroom_track_c_bundle_chain_v1.ps1` |
| 정적 배포 | `projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1` |
| 채팅창·임무 체크리스트 | 루트 `MISSION_LOG.md`(비추적) — 완료 시 Evidence 한 줄 |
| (선택) Ops 한 줄 요약 | `reports/daily_thread_work_YYYY-MM-DD.md` · `athena_daily_thread_log_sync_v1.py` |
| 장기 정체성 | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` (**본 일정 본문 미등록**) |
