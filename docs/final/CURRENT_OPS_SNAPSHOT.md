# Current ops snapshot (ephemeral handoff)

**최신 날짜:** **맨 위** 첫 `## Ops slice (YYYY-MM-DD …)` 제목이 곧 그때 기준의 “오늘/최근” 핸드오프다. **장문 누적·4월 이전 메모**는 `docs/final/artifacts/ops_snapshot_body_archive_2026-05-15.md` 아카이브(본 파일 하단 절 참고).

## Ops slice (2026-05-16 · jema-ai /clinician 본선)

**Thread:** Cursor — **한의사 채팅·CDSS·환자 번들 VPS 반영**

- **완료:** `Deploy-No1kmediDestinyTarball_v1.ps1 -RunApiSmoke` **OK** · `app.jema-ai.com/clinician` **200** · CDSS envelope `validation.ok` · bundle MD ~1.9k · `dev` 커밋·**internal push**
- **막힘:** Pro 게이트는 payapp 결제+승인 또는 **`KM_CLINICIAN_PRO_EMAIL_ALLOWLIST`** 필요(운영 이메일 배포 예정)
- **다음:** VPS `.env.local`에 allowlist 반영 후 재배포 · 선택 `dev`→`main` 머지(VPS `git pull` 정합)

## Ops slice (2026-05-16 · Session handoff · LG 용어 정정)

**Thread:** Cursor — **LG 화요일=결과 발표만 (미팅 없음)**

- **완료:** SSOT 정정 — **5/20(화)=심사 결과 발표·통지** (`is_meeting: false`) · 제출 자료 동결 · factcheck·덱·`internal` push.
- **막힘:** **C-S3** outcome **pending** · 대외 send **false**(법무).
- **다음:** **화요일 결과 통지** 수신 시 `lg_hs_meeting_followup_v1.json` **한 줄만** 기록(미팅 준비·재발송 X) · **hold/reject** → 폴백 `LANE-TRACKC-B2B`.

## Ops slice (2026-05-16 · Session handoff · 채팅 종료 · 권장안 확정)

**Thread:** Cursor — **LG 5/20 결과 발표 대기 · Track C B2B 주력**

- **완료:** **권장안** — **5/20(화) 전 LG 추가 연락·대외 send 없음** (화요일은 **발표일**이지 **미팅 아님**) · hold/reject 시 **`LANE-TRACKC-B2B`** · OpenData 327 병행(~6/5) 법인 분리.
- **막힘:** **C-S3** `outcome_record_template` **pending** · **C-A2** `ready_for_external_send` **false**(법무).
- **다음:** **5/20** 통지 outcome 한 줄 → `lg_hs_meeting_followup_v1.json` · 재개: `@lg_hs_meeting_followup_v1.json` + factcheck MD.

## Ops slice (2026-05-16 · Session handoff · LG·압축·종료 완료)

**Thread:** Cursor — **LG 제출·결과 대기 · RQ-017 · 폴백 SSOT · Track C B2B 선행 산출**

- **완료:** RQ-017 VPS triplet+페이로드 스윕+쇼룸 sync · `lg_hs_fallback_two_week_pipeline_v1`(**`LANE-TRACKC-B2B`**) · **선행:** `build_track_c_macro_risk_mvp_filled_v1` → macro MVP+`track_c_b2b_macro_alert_offer_onepager_latest.md` · readiness **internal meeting OK** / compression **internal OEM draft OK** · CENTRAL checkpoint.
- **막힘:** **C-S3** LG **2026-05-20(화) 대기** · **대외 send=false**(법무).
- **다음:** LG outcome 한 줄만 기록 → **hold/reject** 시 폴백 W1-A1부터(선행 B2B는 `deliverable_status` 참고) · 재개: `장기기억 맥락이어라` + `@docs/final/CURRENT_OPS_SNAPSHOT.md`.

## Ops slice (2026-05-16 · Session handoff · 채팅 종료 · 쇼룸 레이더)

**Thread:** Cursor — **쇼룸 레이더 S2.1–2.2 + B2B 미팅 팩 + Lane E 운영 점검**

- **완료:** Phase **2.1** 레이더 UI·VPS **200** (`7754f8b`) · Phase **2.2** Logos 패널·`showroom_logos_research_slice_v0.json` (`c24139957e`) · **B2B** `Invoke-TrackCB2bMeetingPack_v1`(+commander) · readiness `ready_for_internal_meeting=true` · **Lane E** AmsaengHealth+AthenaBundle+reconcile **all_ok** · `sync_showroom_to_vps`+nginx 스니펫 · `dev` **internal push**.
- **막힘:** `ready_for_external_send` **false**(법무 전 고정) · CDN `assets.jemaai.cloud` PNG **404**(SOP는 soft-fail) · **LOGOS-THEME-RUN** 테마 **61+** 미완(active).
- **다음:** 내부 미팅: `docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md` · 테마 확장 시 `계속` / 중단 시 `테마 확장 중단`.

## Ops slice (2026-05-16 · Session handoff)

**Thread:** Cursor — **명리 거버넌스 + 초개인화 보좌 프로필**

- **완료:** `yongsin_hypothesis_candidates_v1`+SHA-256 fingerprint·환자 MD 격벽(`render_patient_care_bundle_markdown_v1`) · `commander_profile_v1` schema+example+pytest · CENTRAL 지휘관·딸 사주 앵커 · `dev` 커밋 `1d9e28b460`·`b1524152a8` · **internal push** · CONSTITUTION §9 포인터 2행.
- **막힘:** 없음(본 작전 범위).
- **다음:** 새 채팅 `장기기억 맥락이어라` 또는 `@commander_profile_v1.example.json`; 선택 `dev`→`main` 머지.

## Ops slice (2026-05-16 · 일일 3분 체크 실행)

**Thread:** Cursor — **`Invoke-MkmDailyShowroomTradingCheck_v1` 동등 루틴**

- **완료:** Fact-Safe sync 후 **gate ACTIVE** · `trading_go_no_go` **GO** · observation brief **GO** · live_sync **fresh** · SafeOps **overall_safe=True** · 쇼룸 URL **200**.
- **주의:** `promotion_ready=false`(전략 승격 별도) · 휴먼 승인 TTL ~**5/17** — `trading_human_execution_approval_latest.json` 확인.
- **다음:** 원클릭 `pwsh -File scripts/Invoke-MkmDailyShowroomTradingCheck_v1.ps1` · 쇼룸만 재배포 시 `sync_showroom_to_vps.ps1 -RefreshStaging`.

## Ops slice (2026-05-16 · 쇼룸 VPS 배포 승인 반영)

**Thread:** Cursor — **`sync_showroom_to_vps.ps1 -RefreshStaging`**

- **완료:** 체인 재실행(5/5) · `deploy_showroom_static` 8종 스테이징 · **scp OK** → `root@srv1101456.hstgr.cloud:/var/www/jemaai/` (nginx reload는 미실행 — `JEMAAI_VPS_RELOAD_NGINX=1` 시에만).
- **공개 URL(확인용):** `https://api.jemaai.cloud/public_showroom_board_minimal.html` · `…/public_showroom_poll.html` (예능 레이어) · trust viz HTML 동일 루트.
- **막힘:** 없음(배포 exit 0). DNS/SSL이 다르면 Hostinger/nginx 경로만 실측 확인.
- **다음:** 브라우저에서 위 URL 열기; 필요 시 VPS에서 `JEMAAI_VPS_RELOAD_NGINX=1` 후 재배포.

## Ops slice (2026-05-16 · 쇼룸 SSOT 갱신 — 관측·과시 라인)

**Thread:** Cursor — **디스크 SSOT → Track C 대시보드 → 쇼룸 번들**

- **완료:** `build_mkm_trackc_ops_dashboard_v1` · `trading_observation_brief` · `build_showroom_track_c_bundle_chain_v1` **(5/5 OK)** → `showroom_public_bundle_v1.json` · `showroom_trust_visualization_slice_v0.json`(trust/STT **OK**) · topology radar **신규 emit**.
- **관측:** `GO_NO_GO=NO_GO`(LOCKED 정책) · brief `52/52` trades24h · public bundle `context_stale=true`(context TTL) — **과시면 면책·지연 표기 유지**.
- **다음:** 브라우저 확인 `public_showroom_board_minimal.html` / `public_showroom_poll.html`(예능 레이어) — **VPS 반영은** `sync_showroom_to_vps.ps1 -RefreshStaging`(SSH·의도 확인 후).

## Ops slice (2026-05-16 · Trading comfort — GO/NO_GO 정렬)

**Thread:** Cursor — **안심 매매 3단계 체크리스트 실행**

- **완료:** `Invoke-TradingComfortReadinessBrief_v1.ps1` → `reports/trading_comfort_readiness_brief_latest.json` · Fact-Safe chain · preflight(메인넷+거래 ON 경고) · **원인:** prophecy `reliability_badge=LOW`·`HOLD` → `risk_profile.mode=LOCKED_MODE` → gate/risk **NO_GO**(휴먼 GO와 별축).
- **막힘:** 디스크 **전체 GO**는 **의도적 LOCKED** 해제 전 불가 — `ACTIVE_MODE`는 예언 품질·hold 게이트 개선·**휴먼 승격** 후.
- **다음:** **Tier A** 일상: SafeOps(기본)·`Verify-TradingAutomationHealth -AllowPolicyLockedGoNoGo`·5분 live_sync pull · **Tier B/C**는 승인 후만.

## Ops slice (2026-05-16 · Trading ops — 선택 항목 마감)

**Thread:** Cursor — **30d 청크 수수료·VPS 하트비트·스냅샷·채팅 종료**

- **완료:** `build_trading_fee_metrics_chunked_v1.py` 30d 실행·`reports/trading_window_metrics_chunked_30d_v1.json` · `tests/test_build_trading_fee_metrics_chunked_v1.py` · `Deploy-LiveSyncHeartbeatToVps.ps1 -SoftFail` → `reports/live_sync_vps_deploy_latest.json` **ok**, pull **fresh** · `Register-LiveSyncHeartbeatPullTask.ps1` **MKM-LiveSync-Heartbeat-Pull** 5분·SoftFail · `Verify-GitWorkspaceSanity.ps1` **OK** · `athena_checkpoint.py` 한 줄 반영.
- **막힘:** 없음.
- **다음:** `.git/info/exclude` 54행 `config/`가 `projects/bitcoin-trading/config/trading_config.yaml`까지 `git check-ignore`됨 — **비밀·환경별 값**이면 의도 유지; **추적이 필요하면** `config/` 축소 또는 `!projects/bitcoin-trading/config/…` **선별 부정**(템플릿·비밀 분리 후)만 검토. `trading_go_no_go`/Trinity·실주문은 기존 **휴먼·정책** 축.

## Ops slice (2026-05-16 · Session handoff)

**Thread:** Cursor — **스냅샷 저장 + 한의사 홈·차트보조 AI 컨셉 질의**

- **완료:** `CURRENT_OPS_SNAPSHOT.md` 본 블록 갱신. 한의·차트 축은 레포에서 **별축(의료 격벽)**·`km_physician_cds_assist_envelope_v1`(의사결정 **보조** 봉투, 최종 진단·처방 대체 아님)로 고정됨을 SSOT로 정리해 답변 예정.
- **막힘:** 없음.
- **다음:** 한의 CDS는 `run_fact_lock_bundle.ps1` 3e·`CONSTITUTION` 표 유지; 상용 **한의원 전용 홈** 단일 URL은 SSOT 표에 **미배치** — NotebookLM·구기획 “B2B 한의원”은 `JEMA_AI_DOMAIN_POINTER_V1.md`대로 **참고만**, 본선 역할은 `MKM_DOMAIN_PORTFOLIO_POINTER_V1.md`·Track C §3.4와 정합 재확인.

## Ops slice (2026-05-15 · ML-CORP-WEB-1 · 잔여 정리)

**Thread:** Cursor Ops — **「남은 문제 다 해결해」**

- **완료:** `/enterprise` 배포·스모크 **200** (`app.jema-ai.com`) · 푸터 **목소리네트워크**·`support@mkmlife.com` · 클리닉 브랜딩 제거 · `ML-CORP-WEB-1` **DONE** · PM2 경로 문서 **destiny** 반영 · 배포 스크립트 기본 destiny · `Deploy-No1kmediDestinyTarball_v1.ps1` 추가.
- **CF Registrar:** 7/8 apex `transfer_completed` (`registrar_transfer_tracker_v1.json`; `mkmlab.space` 보류).
- **막힘 (API 토큰 zone 미가시):** `mkmlife.com` Email Routing · `jema12.com` 301 — 대시보드에서 zone 추가/확인 후 `Invoke-CloudflareEmailRoutingSetup_v1.ps1` · `Invoke-CloudflareJema12RedirectSetup_v1.ps1 -ZoneId <id>` (또는 Redirect Rules 수동).
- **다음:** `ML-TTL-1` Fact-Safe TTL · 주간 AthenaBundle · jema12/mkmlife zone을 동일 CF 계정·토큰에 연결.

## Ops slice (2026-05-15 · MISSION Phase 2)

**Thread:** Cursor Ops — **MISSION_LOG Active 리셋** (Phase 1 클리어).

- **완료:** Phase 1 ML-DEV/OPS **전부 DONE** → `MISSION_LOG.md` Completed 「Phase-1 클리어」.
- **다음:** `ML-TTL-1` Fact-Safe/승인 TTL · 일간 `AmsaengHealth` / 주간 `AthenaBundle`.
- **보류:** LG 결과 · 예언 승격 · RQ-013 자율주행(연구 큐만).

## Ops slice (2026-05-15 · 진행해 — 루틴 2회차)

**Thread:** Cursor Ops — **「진행해」** (이 채팅 자율).

- **완료:** Fact-Safe **GO** · VPS **aligned** · live_sync **fresh** · Observation **0** · SafeOps **ok** · 클로저 **closure_ok** · `app.jema-ai.com` **200**.
- **TTL:** 승인 ~**5/17 13:02 UTC** · 리스크 ~**5/16 01:04 UTC** (4h sync; **01:04 전** Fact-Safe 한 번 더 권장).
- **Hostinger:** 5건 CF **완료 대기** · Wave 1 메일 = **지휘관**.
- **보류:** 예언 승격·실주문 확대.

## Ops slice (2026-05-15 · 융합 SSOT — 우선순위 + 「진행해」 루틴)

**Thread:** Cursor Ops — 지휘관 **「이것도 융합해서 계속 진행해」** · **이 채팅에서 쭉 진행 OK**.

### 자동·루틴 (방금 실행)

| # | 할 일 | 결과 |
|---|--------|------|
| A | **4h Fact-Safe** `\MKM-FactSafe-RiskProfile-Sync-4H` | 다음 예약 **2026-05-16 00:10** · 방금 chain **GO** |
| B | **타이머 B 선연장** | `Run-TradingExecutionChainOnce` **GO 48h** (proposal+approve; **주문 없음**) |
| C | **VPS GO 동기화** | `Invoke-VpsTradingGoReadinessSync` **aligned=true** · local/VPS **GO** |
| D | **【암행어사】** | `AmsaengHealth` **ALL OK** (~52s) |
| E | live_sync | **fresh** |

**TTL:** `approval_valid_until_utc`·`risk_expires_at`는 `trading_human_execution_approval_latest.json`·`risk_profile_fact_safe_latest.json` 참조. **만료 ≠ PM2 종료.**

### Hostinger exit (백로그 #1–3 · 지휘관 손)

| 우선 | 할 일 | 상태 |
|------|--------|------|
| **1** | CF 이전 5건 `transfer_completed` | **대기** — `jema-ai.com`, `jemaai.cloud`, `no1kmedi.com`, `mkmlife.com`, `jema12.com` |
| **2** | Wave 1 **이체 승인** 메일 | **지휘관** (거절 금지) |
| **3** | Wave 3 (`personadiary`, `a-codeai`, `mkmlab.space`) | **미착수** |

**SSOT:** `registrar_transfer_tracker_v1.json` · `hostinger_registrar_transfer_playbook_latest.json` · EPP **레포·채팅 금지**.

### Ops 백로그 (보류)

| 우선 | 항목 | 정책 |
|------|------|------|
| **4** | 예언 Track A 승격 | `combined_all_passed=false` — **명시 승인 전** |
| **5** | n8n 레거시 문서 | 낮음 |

### 개발 채팅으로 넘김

- aroon × Fact-Safe TTL 코드 정합 · VPS health monitor bundle · RQ-009~011

**재개 (복붙):**

```
@docs/final/CURRENT_OPS_SNAPSHOT.md
융합 SSOT — Hostinger 5건 CF 대기·Wave1 메일·GO 48h·VPS aligned·Amsaeng OK·승격 보류.
```

## Ops slice (2026-05-15 · 진행 — TTL·클로저)

**Thread:** Cursor Ops — 지휘관 **「진행해」**.

- **완료:** `Run-FactSafeRiskProfileSyncChain` **GO** · live_sync **fresh** · Observation **Last Result 0** · 클로저 **full** `closure_ok: true`·SafeOps **ok**. 예언 승격 **combined=false** 유지.
- **TTL(로컬):** `approval_valid_until` ~**2026-05-16** UTC · `risk_expires_at`는 sync 후 `build_trading_go_nogo`·`risk_profile_fact_safe_latest.json` 참조(짧은 TTL이면 2번에서 재sync).
- **막힘:** 없음(자동).
- **다음(1번):** Wave 2 — `jema12.com`·`mkmlife`(zone active 확인) 등 playbook wave2; Wave 1 CF 전송 모니터.

## Ops slice (2026-05-15 · 권장 Ops 레인 — 유지)

**Thread:** Cursor Ops — 지휘관 **「권장으로 해」**.

- **완료:** P0 **725** · TrackC auto chain+copy guard **DONE** · evidence pack·dashboard 갱신 · SSOT: 클로저 **closure_ok**·SafeOps **ok**·예언 승격 **combined=false**(보류). **미실행:** Wave 2(1번)·VPS GO 동기화·승격·mkmlife 실배포.
- **막힘:** 없음.
- **다음:** **1번** Wave 1/2 레지스트라 · **2번** TTL·VPS parity(필요 시) · 승격은 **명시 승인** 전까지 보류.

## Ops slice (2026-05-15 · SafeOps 복구 + 클로저 full)

**Thread:** Cursor Ops — 지휘관 **「진행해」**.

- **완료:** `Invoke-LiveSyncHeartbeatPull` **fresh** · `Run-TradingObservationLoop` + `schtasks` Observation **Last Result 0** · `Invoke-SafeOpsSurfaceCheck` **ok** · 예언 클로저 **full** `closure_ok: true`·`go_no_go: GO`·pytest 137 pass. 예언 승격은 여전히 **combined=false**(보류).
- **막힘:** 없음(자동).
- **다음(인간):** **1번** Wave 1 메일·CF·Wave 2. 승인 TTL은 `approval_valid_until_utc`·`risk_expires_at` 모니터(2번과 공유 가능).

## Ops slice (2026-05-15 · 3채팅 분리 권장 — Ops 레인만)

**Thread:** Cursor Ops — 지휘관 **「권장으로 해」** (채팅 역할 고정).

- **완료(이 채팅):** P0 **725** OK · 예언 게이트 **opportunistic/soft_band_review/combined=false**(승격 안 함) · TrackC auto chain DONE · 예언 클로저 **pytest·prereqs OK** (`-SkipSafeOpsSurfaceCheck`·`-SkipGoNoGoRefresh` — **2번 채팅 담당**).
- **막힘(2번으로):** ~~SafeOps degraded~~ → **아래 슬라이스에서 복구**.
- **막힘(1번으로):** Wave 2 레지스트라(`jema12.com` 등) — **미착수**(1번 채팅).
- **다음:** **1번** Hostinger 메일 승인·CF 전송 상태·Wave 2. **2번** live_sync·Observation 루프·`go_no_go` TTL. **이 채팅** 예언/TrackC만.

## Ops slice (2026-05-15 · 순서 밀기 — sweep·VPS GO·mkmlife DryRun)

**Thread:** Cursor — 지휘관 **「순서대로 밀어」**.

- **완료:** (1) `run_prophecy_btrack_recommended_eval_chain_v1.py --auto-sweep-and-apply` exit 0 (~39s) → **best `neutral_bps=2.0`**·`reports/prophecy_promotion_gates_recommended_chain_v1_latest.json` **`outcome_class: opportunistic`**, `soft_band_review`, `combined_all_passed: false`(렌즈 mean ~0.486·instrument ~0.535) → **승격 안 함**. (2) 로컬·VPS `trading_go_no_go` **GO** · `Invoke-VpsTradingGoReadinessSync_v1.ps1` **`aligned=true`**. (3) mkmlife `deploy-to-hostinger.ps1 -DryRun` OK(SSH/배포 미실행). **예언 클로저** `closure_ok: true`·safe_ops ok.
- **막힘:** strict/combined 승격 게이트 **미통과**(수치).
- **다음(인간):** Track A 승격·실주문은 **명시 승인**; mkmlife **실배포**는 `-DryRun` 없이 지휘관 실행; RQ-009·GPU Pack0-B.

## Ops slice (2026-05-15 · 권장안 마감 — 승격 보류·관측 유지)

**Thread:** Cursor — 지휘관 **「권장 방안으로 해봐」**.

- **완료:** **예언** `recommended_chain`·`dual` 재평가 → `reports/prophecy_promotion_gates_human_gate_check_latest.json` **`outcome_class: opportunistic`**, `promotion_recommendation: soft_band_review`, `combined_all_passed: false` → **Track A 승격 안 함(권장 준수)**. **P0** 725 OK. **예언 클로저** `closure_ok: true`·`ops_mainline_observability_only_no_orders`. **Track C** `Run-TrackCRecommendedAutoChain_v1.ps1` DONE(copy guard PASS)·`track_c_evidence_pack_latest.json`·`mkm_trackc_ops_dashboard_latest.json`. **실매매** `trading_go_no_go` **GO**·`ACTIVE_MODE`·지휘관 승인 유효(`trading_human_execution_approval_latest.json` **GO**, ~2026-05-16 UTC) — **주문 자동 없음**.
- **막힘:** 없음(자동).
- **다음(인간):** **RQ-009** OPEN(법무 D·COGS 실측)·**GPU Pack0-B**·**mkmlife** `deploy-to-hostinger.ps1` — 에이전트 미실행. 예언 **strict 승격** 원하면 `run_prophecy_btrack_recommended_eval_chain_v1.py --auto-sweep-and-apply` 후 재평가·**명시 승인**.

## Ops slice (2026-05-15 · 순서 마감 — AthenaBundle + VPS 재동기)

**Thread:** Cursor — 지휘관 **「순서대로 쭉 밀어」**.

- **완료:** **gitea/main `f1c9957859`**. **AthenaBundle** exit 0 (~3m, prophecy 137 pass, premium queue GO shadow, tail SafeOps ok). **AmsaengHealth** exit 0 (일간). jema-ai VPS **destiny 번들+lab rsync** (이전 턴). ML-DEV-4 표면·P0 725.
- **막힘:** 없음(자동).
- **다음(인간):** 예언 **승격**·실매매·RQ-009 법무·GPU Pack0-B — `combined_all_passed`·`LOCKED_MODE`·`trading_go_no_go` **합선 금지**. mkmlife `deploy-to-hostinger.ps1` 별도. VPS 재기동 직후 **502** 가능 → 수 초 후 **200** 정상(실측).

## Ops slice (2026-05-15 · ML-DEV-4 + 권장 검증 번들)

**Thread:** Cursor — 지휘관 **「권장안으로 쭉 밀어」** (Track C 표면 + Ops 게이트).

- **완료:** `no1kmedi` — `src/lib/homepagePreset.ts` 기본 **`stripe-linear`** · `sync:marketing-copy`·`check:marketing-copy`·`check:trackc-claims` · `check_track_c_copy_guard_v1.py` **exit 0** · `npm run gate:fast` **exit 0** · `internal` **`831e9baf3c`**. Vault — `RULE_격벽_장뇌축_Logos_합선금지.md`(로컬 `memory/`, Git 미추적). **P0** 725 OK · `Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1` `-SkipLiveSyncPull -SkipGoNoGoRefresh -SkipWebhook` → `reports/prophecy_lane_closure_bundle_v1_latest.json` **`closure_ok: true`** · SafeOps **ok**.
- **막힘:** 없음.
- **다음(인간):** 예언 승격·실매매는 `combined_all_passed`·`LOCKED_MODE` **별도** — `trading_go_no_go`와 합선 금지.

## Ops slice (2026-05-15 · VPS jema-ai 자동 배포)

**Thread:** Cursor — 지휘관 **「자동 진행해」**.

- **완료:** `SoloDev-MergeFeatureToGiteaMain` → **gitea/main `37b9263`**. `Invoke-VpsDestinyBundleSync` (ff9262→37b9263) → `/opt/mkm-destiny-ai-41e38ec6`. **rsync** `projects/no1kmedi` → `/opt/mkm-lab-workspace-v2` · `npm ci` · `npm run build` · **`pm2 restart no1kmedi-com`** online. `https://jema-ai.com` smoke **301** (리다이렉트 정상).
- **막힘:** `run_showroom_vps_guarded_deploy.ps1` 게이트 스크립트는 lab 경로에 없음 → **번들+rsync 경로**로 우회. 장기: lab↔destiny 단일 SSOT 정리 권장.
- **다음:** `mkmlife` Hostinger는 §2.2 `deploy-to-hostinger.ps1` 별도; lab `git pull`만으로는 **hq GitHub**라 monorepo `internal`과 **분리** 유지.

## Ops slice (2026-05-15 UTC · 채팅 종료 — Fact-Safe·KOSPI·main 동기)

**Thread:** Cursor — 지휘관 **스냅샷 후 채팅 종료**.

- **완료:** Fact-Safe `MKM-FactSafe-RiskProfile-Sync-4H` **Last Result 0** 경로(`run_conditional_action_gate_v1.py` **`--dry-run-exit-zero-on-block`**, `Run-FactSafeRiskProfileSyncChain_v1.ps1` **`-ExitZeroOnNoGo`**, 등록 스크립트 기본); **`7fe9c1a`**(스케줄 위생) + **`5cd2259654`**(KOSPI stress 관측 v1·B-track 체인·`-StrictTradingGoNoGo`·렌즈 웹훅 테스트 격리) **`gitea/main`** fast-forward; 원격 **`dev` 유지** 합의; 마지막 루프 **P0**·예언 클로저(스킵 4종)·`run_fact_lock_bundle.ps1 -SafeOpsIgnoreLiveSync` **exit 0**·추적 `*_latest` **restore**·워킹트리 **clean**·`dev`/`gitea/main` **0/0**.
- **막힘:** 없음.
- **다음(채팅 밖):** RQ-012 n8n 인프라 철거/유지 **운영 결정**; RQ-009 **OPEN**·법무(D)·실측; 실매매 **`LOCKED_MODE`** 해제는 **거버넌스·실측 입력** 후 동일 체인으로 재검증.

## Ops slice (2026-05-15 UTC · 채팅 종료 — 스냅샷·체크포인트)

**Thread:** Cursor — 지휘관 **「진행해」** → 핸드오프만 갱신하고 창 종료.

- **완료:** 본 파일 **상단 Ops slice** 추가; `py scripts/athena_checkpoint.py`로 `CENTRAL_AGENT_MEMORY_V1.md` **last_updated_utc**·체크포인트 1줄 갱신. 권장안(직전 세션): `dev`/`gitea/main` 동일선·SoloDev **Already up-to-date**·`verify_p0` OK.
- **막힘:** 없음.
- **다음:** `git status`에 남은 `CONSTITUTION`·`PUBLIC_FACING`·`silver_tech_cogs*`·`*_latest.json`·`blind_replay*`·`trading_execution*`·`sync_latest_24h.log.jsonl` 등은 **의도 확인 후** 커밋 또는 `git restore`; 재개 시 `@docs/final/CURRENT_OPS_SNAPSHOT.md`. 인간 게이트(COGS·법무 D·RQ-009·GPU Pack0-B)는 아래 **2026-05-17** 슬라이스·`AGENTS.md`와 동일.

## Ops slice (2026-05-17 · Session handoff — RQ-010·원격 동기·채팅 종료)

**Thread:** Cursor — 지휘관 **스냅샷 후 채팅 종료** 여부.

- **완료:** `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-010** 행 + **IR·제안서 한 줄 초안**(KO/EN, `[HYPO]`); `git push gitea dev:main`으로 **`gitea/main`** 최신선 동기(로컬 `dev`와 동일 커밋).
- **막힘:** 없음.
- **다음:** 선택 — 워킹트리만 더러운 `docs/final/artifacts/logos_s1_shadow_promotion_human_approval_latest.json`·`reports/agent_decisions_log.jsonl`는 의도 없으면 `git restore`; **GPU** Pack0-B 실학습·**RQ-009** 법무(D)·실측 KPI는 휴먼 게이트.

## Ops slice (2026-05-14 · Autonomous ops chain — STT·gates·예언 클로저)

**Thread:** Cursor — 지휘관 **「순서대로·권장안으로 쭉 밀어」** → 로컬 잡음 정리 후 권장 검증 번들.

- **완료:** `git fetch gitea --prune`; 스케줄로 흔들린 추적 `*_latest`·`CENTRAL` 잡음은 **HEAD `git restore`**로 정리; STT `append_stt_routing_audit_log_v1`×2 + `summarize_stt_routing_audit_log_v1` → `reports/stt_routing_audit_log_v1.jsonl`·`reports/stt_routing_audit_log_v1_summary_latest.json`(비추적); `verify_p0_constitution_gate_paths.ps1` **719** OK; `pytest` `test_append_stt_routing_audit_log_v1`+`test_stt_routing_audit_log_schema_v1`+`test_validate_showroom_public_bundle` **17** pass, 이어 `test_mkm_control_integrity_pipeline_smoke_v1`+`test_validate_showroom_public_bundle` **19** pass; `Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1` `-SkipLiveSyncPull -SkipGoNoGoRefresh -SkipWebhook` → `reports/prophecy_lane_closure_bundle_v1_latest.json` **`closure_ok: true`**(번들 내 pytest **137** passed, 3 skipped).
- **막힘:** 없음.
- **다음:** 인간·운영 — **프로덕션 JSONL** 적재 경로·호스트별 **COGS 월소계**(청구서)·**법무 (D)**; RQ-009는 **OPEN** 유지(수치·최종 면책 Git 동결 전). 선택 — `scripts/run_fact_lock_bundle.ps1` 전체; 쇼룸 VPS는 `MKM_SHOWROOM_OPS_AND_PACK0B_WORK_SCHEDULE_V1.md`·호스트 확정 후.

## Ops slice (2026-05-16 · Visualization v0 — 목표·작업 분해)

**Thread:** Cursor — 지휘관 **「진행해」** → **Trust Visualization v0** 로드맵을 스냅샷에 장전(서브에이전트·**별 브랜치** 병렬 가이드 포함).

- **완료:** Stream **1** — `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md`(§3.6)·`PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`(§3)에 **Visualization v0** Fact-Lock·`[NON_GATING]`·아티팩트 근거형 역참조; `CENTRAL_AGENT_MEMORY_V1.md` 체크포인트. Stream **2** — `append_stt_routing_audit_log_v1.py` / `summarize_stt_routing_audit_log_v1.py`·롤업 필드·`verify_p0`·`dual-regime`·`tests/test_append_stt_routing_audit_log_v1.py`·`tests/test_stt_routing_audit_log_schema_v1.py`·**로컬** `reports/stt_routing_audit_log_v1.jsonl` 샘플 2행 append + `stt_routing_audit_log_v1_summary_latest.json` 갱신(비추적). Stream **3** — `build_showroom_trust_visualization_slice_v1.py`·`public_showroom_trust_visualization_v0.html`·체인 **(5/5)**·`deploy_showroom_static.ps1`·`.gitignore` 생성 JSON; **`gitea/main`** 반영(Visualization v0 + STT 롤업 + 쇼룸 thin 커밋선). Stream **4** — `pytest` 3d3a+`test_validate_showroom_public_bundle` **19** pass; 예언 클로저 번들 **`closure_ok: true`**(`Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1` 생략 스위치 조합)·MKM_SHOWROOM Phase **0**·진행 로그 Phase **4** 기록.
- **막힘:** 없음.
- **`[목표]` Visualization v0:** 파이프 **1사이클**(COGS·감사·법무 게이트) **재현 후**, `Field→Lens(사상/명리/Logos)→Conflict→Final` 조율을 **감사 로그에 정렬된 읽기 전용 패널**로 시각화(Logos는 **`[NON_GATING]`** 해설 레이어). **Track C 쇼룸**은 **동일 스키마의 thin 시연 슬롯**만 연계(**본선·연구 격벽 유지**).
- **Streams (병렬 권장 / 직렬):**
  1. **직렬·SSOT** — `CURRENT_OPS` / `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` / `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` 문구·DoD 한 줄; `CENTRAL` 체크포인트(`py scripts/athena_checkpoint.py "…"`). **한 채팅** 권장.
  2. **병렬 A·감사** — STT 경로 **상륙 완료**; **로컬** `append`×2 + `summarize` 루프는 실측 샘플로 재현 가능(`silver_tech_cogs…` §Stream 2). **잔여(인간·운영):** 프로덕션 JSONL 적재·호스트별 청구서 기반 **COGS 표 월소계**·법무(D).
  3. **병렬 B·쇼룸** — thin HTML/슬라이스·배포 스크립트 **상륙 완료**; Phase 2 스테이징·VPS는 **`MKM_SHOWROOM_OPS_AND_PACK0B_WORK_SCHEDULE_V1.md`**·지휘관 확정 호스트로 수동.
  4. **통합·게이트** — `verify_p0`·`dual-regime`에 STT+스키마+쇼룸 pytest **3파일**·`run_fact_lock_bundle.ps1` **3d3a** 정합; **`Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1`** `-SkipLiveSyncPull -SkipGoNoGoRefresh -SkipWebhook` → `reports/prophecy_lane_closure_bundle_v1_latest.json` **`closure_ok: true`**. **쇼룸 번들 검증:** `pytest tests/test_validate_showroom_public_bundle.py` 포함 **19** 통과(로컬). **쇼룸 일정 Phase 0** — `MKM_SHOWROOM_OPS_AND_PACK0B_WORK_SCHEDULE_V1.md` Control-Integrity smoke + `verify_p0` **2026-05-16** 기록.

## Ops slice (2026-05-15 · 채팅 종료 스냅샷 — 본 스레드)

**Thread:** Cursor — 지휘관 **스냅샷 후 이 대화 종료**.

- **완료:** 권장 한 사이클 — P0(707)·비밀 스캔 strict OK·예언 클로저 **`closure_ok: true`**; **실버·본 스냅샷·`CENTRAL`**은 레포 **`dev` = `gitea/main`** 동일선(맨 끝 해시는 루트에서 **`git rev-parse HEAD`**); 워킹트리 **clean** 목표; `CENTRAL` 에디터 잡음은 **`git restore docs/final/CENTRAL_AGENT_MEMORY_V1.md`**.
- **막힘:** 없음.
- **다음(재개):** 아래 **Silver** 표·`docs/research/silver_tech_cogs_unit_economics_template_v1.md`; 인간 — COGS 출처·시나리오·법무(D)·RQ-009 `CLOSED` 조건. **쇼룸 스테이징 3파일**(`.showroom_staging/public_showroom_board_minimal.html`·`…_poll.html`·`jemaai-cloud-mvp/showroom_public_bundle_v1.json`) — **실버와 무관**이면 의도 없을 때 **`git restore`(3경로)**로 끝, 쇼룸 작업이면 **별 커밋/PR**(실버와 섞지 않음). 선택 — `_pr_sasang_promotion` stash·`git push gitea --delete dev`·`py scripts/athena_checkpoint.py "…한 줄"` .

## Ops slice (2026-05-15 · Silver — COGS·STT·RQ-009·장기기억 동기)

**Thread:** Cursor — 실버 `[HYPO]`·Hybrid STT·지휘관 승인 구조·NotebookLM `nlm` 푸시 경로·템플릿 슬림.

- **완료:** (1) RQ-009·`PUBLIC` v1.3·`TRACK_C` §3.7.2 **(B)/(D)** — KPI·마진·면책 Git 동결 지연; 민감 외부 액션 **휴먼 게이트** SSOT. (2) `silver_tech_cogs_unit_economics_template_v1.md` **압축**(COGS·시나리오·공개 링크; STT는 **jsonschema만 SSOT** `latency_ms` 등 필드명은 `stt_routing_audit_log_v1.schema.json` 준수). (3) `RESEARCH_OPEN_QUESTIONS`·MISSION_LOG·**CENTRAL** 체크포인트/`nl_sync`. (4) NotebookLM: `RESEARCH_HISTORY`·렌즈 팩·`Push-NotebooklmLensPacks_v1.ps1`·`notebooklm_lens_pack_push_map_v1.template.json`·하이브리드 `-PushLensPacksToNotebookLm`; **Vault≠NL** 자동 합선 없음.
- **막힘:** 없음.
- **다음:** COGS **출처·시나리오(S-CONS/BASE/STRESS)** 채움; 텔레메트리·견적·법무(D) 확정문 후 RQ-009 **CLOSED**·Track C 수치 문장은 **artifacts/별첨**만. 쇼룸·스마트팜 내러티브는 **새 채팅** 권장.

| 항목 | 레포 포인터 |
|------|-------------|
| COGS `[HYPO]` | `docs/research/silver_tech_cogs_unit_economics_template_v1.md` |
| STT 감사 v1 | `docs/final/schemas/stt_routing_audit_log_v1.schema.json` · `…minimal.example.json` · `tests/test_stt_routing_audit_log_schema_v1.py` |
| Track C / 대외 | `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.7.2 · `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` §3 |
| 연구 | `RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-009** |

## Ops slice (2026-05-14 · Session handoff — User Rules·채팅 종료)

**Thread:** Cursor — 핸드오프 규칙·User Rules 복붙·창 종료.

- **완료:** `AGENTS.md` **「Recommended Cursor User Rules — User 탭 합본」**(Fact-Lock·사실 확인·최소 변경·세션 시작·`CURRENT_OPS` 핸드오프·일기 배제) 레포 고정·커밋; User Rules는 펜스 없이 붙여도 됨·레포와 **문구 1:1 필수 아님** 안내; 채팅 종료·스냅샷 절차 재확인.
- **막힘:** 없음.
- **다음:** 새 세션 `@AGENTS.md` / `@docs/final/CENTRAL_AGENT_MEMORY_V1.md`; 스냅샷 상단만 주기 슬림; `git pull` 후 다른 PC에서 User Rules 동기.

## Ops slice (2026-05-14 · Track C §3.7.2 Silver ↔ PUBLIC v1.2)

**Thread:** Cursor — 실버 테크 SSOT·대외 카피 **양방향** 잠금·핸드오프.

| 항목 | 레포 포인터 |
|------|-------------|
| Track C 실버 `[DRAFT]` | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` **§3.7.2** — **(B)** `PUBLIC_FACING` **§3** Silver / senior-care 불릿 **필수** + **(D)** 면책 초안 이중 정합. **Revised / SSOT** 2026-05-14. |
| 대외 카피 헌법 | `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` **v1.4** — §3 + Silver freeze(v1.3)·Trust Visualization v0(2026-05-16); 앵커에 §3.7.2 `(B)` 역포인터. |
| 연구 큐 | `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-009** — 근거 열·「왜 열려 있는가」에 엔지니어링 진척 반영, **메타 `last_reviewed_utc: 2026-05-14`**, 상태 `OPEN` 유지. `MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` Phase 4 표 아래 **연구·정책 큐** 단락 교차. |
| CENTRAL | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` — `nl_sync`·체크포인트(실버·PUBLIC 교차). |
| 로컬 일기(비추적) | `memory/obsidian_vault/SPIRIT/10_Daily_Log/2026-05-14_silver_track_c.md` — `memory/`는 `.gitignore`. |

- **완료:** §3.7.2 ↔ PUBLIC §3 교차 잠금; RQ-009·CENTRAL·MISSION_LOG(로컬) 정리.
- **막힘:** 없음 (법무 전 **DRAFT**).
- **다음:** `git status` → 의도한 파일만 커밋·`push-internal` 등; RQ-009 **CLOSED**는 법무·파일럿 KPI 동결 후.

## Ops slice (2026-05-14 · patient_care_bundle v1 + PUBLIC_FACING §3)

**Thread:** 환자 통합 번들 파이프라인·대외 카피 체크리스트 교차(법무 RQ-009는 별도).

- **완료:** `patient_care_bundle_v1` 스키마 `provenance` 후처리 감사 필드·assemble `--validate` 최종 파일 기준·`Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1`(`-PolicyJson`·`-DryRun`)·CDS 체인 정책 전달·`PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` §3 **Engineering cross-check** 불릿(RQ-009와 구분)·`CLAUDE.md` 더 읽을 때·`run_fact_lock_bundle.ps1` 3e 주석·`verify_p0` **704**.
- **막힘:** 없음.
- **다음(선택):** RQ-009 **법무·파일럿 KPI 동결** 후 `CLOSED`/이관; 시간 허용 시 `run_fact_lock_bundle.ps1` 전체.

## Ops slice (2026-05-14 · NotebookLM 인덱스·레포 정렬 — 채팅 종료 스냅)

**Thread:** Cursor — NotebookLM MCP 주입 세션에서 라이브러리 검수·권장안 적용·장기기억 체크포인트.

- **완료:** MCP `get_health` / `list_notebooks`(라이브러리 3건) / 노트별 `ask_question` 소스 프로브; `RESEARCH_HISTORY_V1.md` **현행 전용** 재작성 + `docs/final/artifacts/research_history_notebooklm_snapshot_2026-04-12.md` 아카이브(41); `NotebookLM_sources_manifest.md`(연구 인덱스·OPS 표)·`MULTI_LENS` Phase 4.3 비고·`CURRENT_OPS` 노트북 목록 bullet; `sync_notebooklm_sources_to_mkm_data_vault.ps1` `$SourceFiles`; `build_notebooklm_lens_source_packs_v1.py` OPS 팩에 `RESEARCH_HISTORY_V1.md`; `CENTRAL_AGENT_MEMORY_V1.md` `nl_sync`/체크포인트/`py scripts/athena_checkpoint.py`; `Sync-PrSasangPromotionMirror_v1.ps1`(10); `verify_p0_constitution_gate_paths.ps1` OK; 스냅샷 본문 상단 “최신 날짜” 안내 문구.
- **막힘:** 없음.
- **다음(선택):** Vault 미러 스크립트 실행(G: 환경 시); NotebookLM **웹** 소스 탭과 프로브 수 대조; 변경분 `git commit`.

## Ops slice (보관 · 이전 핸드오프 잔여)

**Thread:** 이전 세션(스마트팜/실버 테크 등). **이번 채팅 작업은 위 슬라이스.**

- **완료:** 금산 스마트팜 농업법인 설립 전략 수립, 실버 테크(시니어 AI) 사업 파이프라인 및 규제 방어 로직 설계, 레포 내 핸드오프(Handoff) 운영 체계 확정 및 `CENTRAL` 반영.
- **막힘:** 없음. (농업인 자격증 발급 기간은 행정적 대기 시간으로 분류)
- **다음:** 레포 SSOT는 상단 **Track C §3.7.2 ↔ PUBLIC v1.2** 슬라이스 참고. 스마트팜·실버 **내러티브 1p**만 이어갈 때는 별도 채팅 권장.

## Ops slice (2026-05-13 · Cross-chat SSOT + next schedule)

**채팅은 서로 기억을 공유하지 않는다.** C: 정리·Ollama 경로 등은 **레포 경로만** 새 세션에서 `@docs/final/CURRENT_OPS_SNAPSHOT.md` 또는 아래 스크립트를 연다(말로만 다른 창에 전달해도 재현 불안정).

| 주제 | 레포 포인터 |
|------|-------------|
| C: 인스톨러 잔재 정리 | `scripts/Invoke-CRootInstallerLeftoversCleanup_v1.ps1` |
| C: AMD 인스톨러 캐시 | `scripts/Invoke-CRootAmdInstallerCacheCleanup_v1.ps1` |
| Ollama·대용량 모델 | **F:** 정션(또는 본인 PC 실경로)은 비추적 `docs/final/LOCAL_MACHINE_POINTER_V1.md`의 `ollama_models_dir`에만 기록. 런타임 태그는 루트 `.env`의 `OLLAMA_HOST` / `OLLAMA_MODEL`(`.env.example`·`CLAUDE.md`). Cursor **User Rules**는 레포와 자동 동기화되지 않음. |
| 통합 거버넌스 + M31 스냅 | `invoke_build_integrated_governance_if_deps_present_v1.py` → 조건 충족 시 `build_integrated_governance_v1.py --validate-digest-schema`·`integrated_governance_v1_latest.json`. 체인: `run_fact_lock_bundle`·`Invoke-TrackCMacroDailyFusion_v1`·`Invoke-MkmAiV2DailyReadiness`. 스키마·예시·`-SkipIntegratedGovernanceBuild` / `Register-*` 전달. |
| Hostinger 퇴거(VPS만)·등록 → Cloudflare Registrar | `scripts/Invoke-HostingerFullExitAutomationChain_v1.ps1` → `reports/hostinger_decommission_gate_latest.json`(`go`) · `reports/hostinger_full_exit_automation_chain_latest.json` · 진행표 `scripts/data/hostinger_full_exit/registrar_transfer_tracker_v1.json` — 백업·hPanel 호스팅 해지·EPP/이전은 수동. |
| Windows · B-track·패널·워치독·BTC 주간·헬스 (로그오프 후 실행) | 관리자: `scripts/Register-MkmBtrackProphecyTasksRunWhenLoggedOff_v1.ps1` — 아래 **5개** 작업이 `Principal.LogonType=S4U`로 재등록됨(로그오프 후에도 동일 사용자 컨텍스트). `MKM_BTrack_Automation_Health_Daily` 포함이 정상. **작업 스케줄러의 `Last Task Result` / `LastTaskResult` 값 1**은 등록 실패가 아니라 **직전 실행의 종료 코드**(예: 패널 24h 스크립트는 KPI 미달 시 **exit 1**이라 자주 1로 남음); 다음 성공 실행 후 바뀔 수 있음. **수동 유지:** `\GeneralProphecyDailyQueueV1`, `\GeneralProphecyHoldoutEvolutionWeeklyV1`는 `schtasks` 경로라 본 스크립트가 건드리지 않음 — 로그오프 후에도 돌리려면 해당 두 작업만 작업 스케줄러에서 **사용자 로그온 여부와 관계없이 실행** + 계정 비밀번호 저장(또는 `schtasks /RU`/`/RP`)으로 맞출 것. |

### 일일 운영 1페이지 — B-track 시장 예언 (Fact-Lock 체크리스트 행 6·7·9 압축)

**판정:** 채팅 요약이 아니라 **exit code + 아래 JSON 필드**만으로 GO/HOLD를 쓴다. `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 일일 B-track·패널·히트레이트 절과 동일 선상.

**체인 exit 0 vs 패널(9):** 히트레이트가 `no_data`이거나 패널이 exit 1이면 **기본 체인은 throw로 중단**될 수 있다. **수동**으로 완주만 분리할 때는 **6**에 `-SkipPanel24hAlertsCheck`를 넘기고, **9**는 직후 `Check-ProphecyPanel24hAlerts.ps1`로 단독 실행·로그를 남긴다. **작업 스케줄러**는 `Register-BTrackDailyHypothesisTask.ps1`가 등록 인자에 **기본으로** `-SkipPanel24hAlertsCheck`를 붙이므로(재등록 후 반영), `Register-MkmBtrackProphecyTasksRunWhenLoggedOff_v1.ps1` 등으로 갱신하면 **6**과 동일 효과를 별도 플래그 없이 얻는다. (유료 반성 생략: `-SkipProphecyContemplationGemini`.)

| 단계 | 체크 | 최소 명령 (저장소 루트 `C:\workspace` 가정) |
|------|------|-----------------------------------------------|
| 0 (선행) | [ ] 사전 조건 스캔 | `py scripts/check_btrack_prophecy_chain_prereqs_v1.py --stdout-only` (엄격 운영: `--strict`) |
| 6 | [ ] 일일 B-track 번들 완주 | **수동:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_btrack_daily_hypothesis_chain.ps1` — 기본은 패널 포함; 완주만이면 `-SkipProphecyContemplationGemini -SkipPanel24hAlertsCheck` (위 단락). **스케줄:** `Register-BTrackDailyHypothesisTask.ps1` 기본이 체인에 `-SkipPanel24hAlertsCheck` 포함(재등록 필요 시 관리자 번들 스크립트). `-Skip*` 사용 시 **의도·로그** 남김. |
| 7 | [ ] 가설·스코어·히트레이트 산출물 존재·스키마 | `docs/final/artifacts/btrack_hypothesis_prophecy_latest.json`, `docs/final/artifacts/btrack_prophecy_score_latest.json`, `docs/final/artifacts/prophecy_hit_rate_eval_latest.json` — 타임스탬프·`schema`·`[HYPO]` 표기 훼손 없음 (`P0_COMMERCIALIZATION_TRACKER.md` 월간 표와 동일 계약) |
| 9 | [ ] 24h 패널 알림 | 체인 종단과 동일 실행 맥락에서 `scripts/Check-ProphecyPanel24hAlerts.ps1` → `reports/prophecy_panel_24h_alerts_latest.json`의 `overall_passed`·ALERT 1–3 필드만 인용; **exit 1 = 등록 실패 아님**(직전 실행 KPI/정책 종료 코드일 수 있음) |

체크박스(일일 복붙용):

- [ ] **0** — `py scripts/check_btrack_prophecy_chain_prereqs_v1.py --stdout-only` (필요 시 `--strict`)
- [ ] **6** — 수동: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_btrack_daily_hypothesis_chain.ps1` (필요 시 `-SkipProphecyContemplationGemini -SkipPanel24hAlertsCheck`); 스케줄은 등록 스크립트 기본이 패널 스킵 인자 포함
- [ ] **7** — `btrack_hypothesis_prophecy_latest.json` / `btrack_prophecy_score_latest.json` / `prophecy_hit_rate_eval_latest.json` 필드 확인
- [ ] **9** — `reports/prophecy_panel_24h_alerts_latest.json`만으로 패널 판정(exit 코드 ≠ 작업 등록 상태)

### 예언 레일 일단락 (권장 방안 · 운영 본선만)

**정의:** “일단락” = **관측·스케줄·정렬·Safe ops 표면**까지 권장 순서가 **exit 0**으로 닫힌 상태. **상용 Track A 승격·실매매·`schtasks` 일반예언 두 작업**은 이 블록 밖(별도 인간 게이트·수동 설정).

| 단계 | 내용 |
|------|------|
| A | **원클릭 검증+리포트:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1` → `reports/prophecy_lane_closure_bundle_v1_latest.json`에 단계별 exit·`safe_ops` 요약·수동 잔여 2줄 기록. 엄격 선행: `-StrictPrereqs`. live_sync 생략: `-SkipLiveSyncPull`. GO/NO_GO만 생략: `-SkipGoNoGoRefresh`. |
| B | **주간:** `run_prophecy_alignment_pytest.ps1` 또는 `run_fact_lock_bundle.ps1`(시간 여유). |
| C | **월간:** `run_waiting_queue_monthly_check.ps1`(`-SkipBundle`는 정렬 중복 생략용). |
| D | **스케줄:** 관리자 `Register-MkmBtrackProphecyTasksRunWhenLoggedOff_v1.ps1`(경로 필수: `.\scripts\...`). |
| E | **수동 고정:** `\GeneralProphecyDailyQueueV1`, `\GeneralProphecyHoldoutEvolutionWeeklyV1` — 로그오프 실행·자격 증명. |

**다음 작업 일정 (권장 순)**

- **Hostinger / CF Registrar:** 새 세션에서는 위 표 한 줄만 `@`로 열고 체인 재실행; `go` 이후에도 해지·이전은 사람 확인.

1. **P0 — 워킹트리 WIP:** `git status`로 스테이징/수정 분리 → 의도 없는 아티팩트는 `git restore`, 소스·테스트는 **한 커밋** 또는 분기.
2. **P1 — 예언 정렬 회귀:** 주 1회 `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`(exit 0) 또는 시간 여유 시 `scripts/run_fact_lock_bundle.ps1`(`-Skip*`로 조절).
3. **P2 — 월간 러너:** `scripts/run_waiting_queue_monthly_check.ps1` — BTC 기본 CSV·듀얼 레그는 스크립트에 반영됨; Slack/게이트는 환경에 맞게 `-Skip*` 최소화.
4. **P3 — 정렬 목록 lockstep:** `run_prophecy_alignment_pytest.ps1` / `run_prophecy_alignment_pytest.sh` **동일 커밋에서 함께 수정**(`docs/final/P0_COMMERCIALIZATION_TRACKER.md` 해당 절).

`internal/main` 최신 커밋은 매번 `git rev-parse internal/main`(본 파일에 SHA 박제 금지).


---

## 본문 누적 아카이브 (split 2026-05-15)

**과거 및 누적 본문:** `docs/final/artifacts/ops_snapshot_body_archive_2026-05-15.md` — 2026-05-12 이하 `Ops slice`·AUTO_OPS·히스토리·기타 장문(노트북 목록 bullet 등 포함).

**갱신:** 스냅샷이 다시 길어지면 동일 방식으로 `ops_snapshot_body_archive_YYYY-MM-DD.md`에 잘라 넣고, 본 파일은 **상단 `Ops slice` + 이 절**만 유지.
