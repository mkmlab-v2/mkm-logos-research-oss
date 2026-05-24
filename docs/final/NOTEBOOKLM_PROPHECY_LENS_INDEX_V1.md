# 예언 전용 NotebookLM 렌즈 인덱스 v1

**역할:** Google NotebookLM **`07_PROPHECY_BTRACK_2026Q2`** 전용 — 가격 B-track 예언·일반예언(비가격)·채점·게이트 **브리핑·연구 질의**만.  
**성격:** Creative-Lock / `[HYPO]`·`research_only` 기본. **구현·통과·실매매 SSOT**는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·호출 가능 `scripts/*.py`·`exit code`·`docs/final/artifacts/*_latest.json`만.

**노트북 UUID:** `3e95ca50-66f8-4b54-b0ef-81821c199518`  
**URL:** https://notebooklm.google.com/notebook/3e95ca50-66f8-4b54-b0ef-81821c199518  
**MCP 라이브러리 id:** `07-prophecy-btrack-2026q2` (`select_notebook` / `ask_question`의 `notebook_id`)  
**렌즈 팩 경로:** `reports/notebooklm_lens_packs_v1/LENS_PROPHECY/` (`py scripts/build_notebooklm_lens_source_packs_v1.py`)

---

## 1) 두 축 (혼선 금지)

| 축 | 내용 | 레포 SSOT |
|----|------|-----------|
| **가격 B-track** | KOSPI/BTC 방향 가설·OHLCV 채점·오버레이 AB·프로모션 게이트 | `eval_prophecy_hit_rate_v1.py` · `build_btrack_prophecy_score_from_ohlcv.py` · `run_btrack_daily_hypothesis_chain.ps1` |
| **일반예언** | 날씨·환경·비가격 확률 슬롯·Brier/ECE | `GENERAL_PROPHECY_SCHEMA_V1.json` · `run_general_prophecy_daily_queue_refresh_v1.ps1` |

**금지:** NL 답변만으로 Track A 승격·실매매 ON·「이미 구현/통과」 단정. 성경·명리·압축 KPI 본문을 이 노트에 섞지 말 것(별도 렌즈 노트).

---

## 2) 노트북 소스 목록 (갱신 시 팩 재빌드)

| 우선 | 파일 | 용도 |
|------|------|------|
| P0 | 본 파일 | 경계·질의 스타터·UUID |
| P0 | `NOTEBOOKLM_GENERAL_PROPHECY_VPS_GIT_FORESIGHT_BUNDLE_2026-04-11.md` | 일반예언·미래학·격벽 |
| P0 | `NOTEBOOKLM_HUB_B_BTC_AB_TRACK_CROSSCHECK_BRIEF_2026-04-04.md` | BTC Hub B vs A 교차 |
| P0 | `GENERAL_PROPHECY_SCHEMA_V1.json` | 일반예언 데이터 계약 |
| P0 | `BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json` | B-track 가설 JSON 계약 |
| P1 | `artifacts/general_prophecy_brief_latest.md` | 일반예언 문항 요약 |
| P1 | `artifacts/btrack_prophecy_score_latest.json` | 최신 가격 score |
| P1 | `artifacts/prophecy_hit_rate_eval_latest.json` | 최신 히트레이트 |
| P1 | `artifacts/prophecy_promotion_gates_v1_latest.json` | 승격 게이트 분류 |
| P1 | `artifacts/prophecy_restoration_spike_latest.json` | 오버레이 AB 스파이크 |
| P1 | `artifacts/general_prophecy_explainability_quality_v1_latest.json` | explainability 실측 |
| P1 | `artifacts/ATHENA_UPLOAD_ONEFILE_LATEST.md` | 운영 스냅샷 Path/Key/Value |
| P1 | `artifacts/ATHENA_SHADOW_LOOP_BTC_FIRST_COMMAND_V1.md` | BTC 섀도우 루프 지시 |
| P1 | `artifacts/general_prophecy_latest.json` | 일반예언 레지스트리 스냅 |
| P1 | `artifacts/prophecy_role_router_multiscenario_opt_30y_btc_neutralbase_latest.json` | Role Router 30Y 요약(레거시 [KEEP] 대응; **v1 477KB 원본은 팩 제외**) |
| P1 | `artifacts/prophecy_lens_combo_backtest_v1_latest.json` | Lens Combo 백테스트 |
| P1 | `artifacts/prophecy_2050_two_track_v1_latest.json` | 2050 two-track |
| P1 | `artifacts/trackc_prophecy_dual_leg_brief_latest.md` | Track C 듀얼 레그 브리프 |
| P1 | `reports/prophecy_lane_closure_bundle_v1_latest.json` | 예언 레일 클로저 번들 |

---

## 3) 질의 스타터 (NotebookLM / MCP `ask_question`)

**가격 B-track:**  
「`btrack_prophecy_score_latest.json`과 `prophecy_hit_rate_eval_latest.json`만 인용해, 최근 eval_date·instrument·hit_rate를 Path/Key/Value로 요약하라. Track A·실매매 합선 금지.」

**일반예언:**  
「`general_prophecy_brief_latest.md`의 미해소 문항 3개와 Brier/ECE는 `general_prophecy_explainability_quality_v1_latest.json` 수치만 인용하라. [HYPO] 서술 유지.」

**게이트:**  
「`prophecy_promotion_gates_v1_latest.json`의 `outcome_class`·`combined_all_passed`만 읽고, 휴먼 승인 없이 승격 가능하다고 말하지 말 것.」

---

## 4) 로컬 운영 (Fact-Lock)

```powershell
# 팩 재생성 + Vault 미러(선택)
py scripts/build_notebooklm_lens_source_packs_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1

# Google NL 소스 푸시 (nlm on PATH)
# reports/notebooklm_lens_packs_v1/notebook_ids.json 에 LENS_PROPHECY UUID 확인 후:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Push-NotebooklmLensPacks_v1.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Push-NotebooklmLensPacks_v1.ps1
```

**예언 레일 점검:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1`  
**B-track 일일:** `scripts/run_btrack_daily_hypothesis_chain.ps1`  
**일반예언 일일:** `scripts/run_general_prophecy_daily_queue_refresh_v1.ps1`

---

## 5) 레거시 이관·아카이브 (2026-05-19 완료)

| 노트 | UUID | 상태 |
|------|------|------|
| **본선 (질의 SSOT)** | `3e95ca50-66f8-4b54-b0ef-81821c199518` | `07_PROPHECY_BTRACK_2026Q2` · MCP `07-prophecy-btrack-2026q2` |
| **아카이브** | `9de651e6-199d-4ea7-88d5-cbca2f177312` | Google 제목 `90_ARCHIVE_P2_PROPHECY_migrated_2026Q2` — **신규 질의 금지** · MCP `archive-p2-prophecy-legacy` |
| MKM Core (`aba1f8b1-…`) | 압축·예언 혼합 | 예언만 → **본 노트** |

**이관 원칙:** 레포에 있는 `*_latest`·스키마·번들만 팩 `LENS_PROPHECY`에 넣고 재푸시. 구 노트의 `SYNC_3LENS_*` 등 **NL 전용 스냅샷**(디스크 없음)은 아카이브 노트에만 남김 — 필요 시 아카이브 노트에서만 참조.

**레거시 소스 인벤토리:** `reports/notebooklm_prophecy_legacy_source_inventory_v1.json` (32 titles, 2026-04-30 시점)

**추가 팩 푸시 (신규 파일만):** `py scripts/push_notebooklm_prophecy_lens_pack_v1.py`

**갱신:** 2026-05-19 — 레거시 `9de651e6` → `07_PROPHECY` 이관·아카이브 rename.
