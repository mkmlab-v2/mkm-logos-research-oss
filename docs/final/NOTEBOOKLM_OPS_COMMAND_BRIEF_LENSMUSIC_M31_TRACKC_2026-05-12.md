# NotebookLM 지휘부 브리프 — Lens music M31 · §3.9 승격 게이트 · Track C 일일 퓨전 (2026-05-12)

**역할**: 작전지휘부 / **Ops Command Anchor (Fact-Lock)** 노트북에 `source_add`할 **단일 파일 소스**.  
**Fact-Lock**: 구현·통과 여부는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·호출 가능 `.py`·pytest·exit code만 SSOT. 본 문서는 **핸드오프·동기화용(B-track 연구 레인)**.

---

## 1. 요약 (이번 세션 반영분)

| 주제 | 상태 | 비고 |
|------|------|------|
| §3.9 승격 게이트 pytest 번들 | 확장됨 | `tests/test_dispatch_lens_music_hormone_trend_webhook_v1.py` 포함(로컬 HTTP + WATCH + `--webhook-url` POST 스모크). |
| `check_lens_music_symbolic_audio_promotion_gate_v1.py` | 녹색 시 `B_TRACK_RESEARCH_PROMOTION_READY` | **연구 레인만**; `track_wall`(A 상용 오디오·C 1차 GTM 자동 승격 금지) 불변. |
| M31 hormone trend / webhook | 배선 완료 | `build_lens_music_hormone_trend_v1.py`, `dispatch_lens_music_hormone_trend_webhook_v1.py`; User env `LENS_MUSIC_HORMONE_WEBHOOK_URL`; CLI `--webhook-url` 스모크용. **WATCH일 때만** POST. |
| Track C 일일 퓨전 | 스케줄 연동 | `Invoke-TrackCMacroDailyFusion_v1.ps1` 대시보드 직전 trend+webhook 기본; `-SkipLensMusicHormoneTrend` 선택. |
| Windows 등록 | 검증됨 | `MKM-TrackC-MacroDailyFusion` Ready·`last_task_result=0`; 재등록은 **관리자 PowerShell** 필요(스크립트 사전 검사 추가). |
| CI `paths` | 보강 | `dual-regime-integrity.yml`, `audio-bgm-gate-smoke.yml`에 M31 스크립트·테스트 경로 추가(M31만 고쳐도 PR CI 타도록). |
| `.env.example` | 보강 | `LENS_MUSIC_HORMONE_WEBHOOK_URL` + `--webhook-url` 로컬 스모크 안내. |

---

## 2. SSOT 포인터 (질의 시 인용)

- `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — 상징→오디오·상징→텍스트 M0–M31 보강 줄.
- `AGENTS.md` — §3.9 승격 번들·Track C 일일 퓨전 한 줄.
- `docs/NotebookLM_sources_manifest.md` — **3채널**(Vault / Google NL / Cursor MCP) 분리; “매니페스트만 고치면 클라우드 동기” **아님**.

---

## 3. NotebookLM에 올리는 방법 (클라우드 B채널)

1. 노트북: **`작전지휘부 Ops20260318`** 또는 라이브러리의 **Ops Command Anchor (Fact-Lock)** (`347e5cbe-0ade-4615-9aac-8747d4fa644e` 등 매니페스트 URL 기준).
2. **소스 추가**: 이 파일을 웹 UI에서 업로드하거나, MCP 인증 후 **`add_source`**(도구가 채팅에 주입된 경우에만)로 텍스트/경로 반영.
3. **MCP 인증**: `get_health`에서 `authenticated=false`면 `setup_auth` → 전용 Chrome 프로필 로그인(내장 브라우저 로그인과 **비동기**).

---

## 4. 금지·경계 (브리핑용)

- **임상·내분비 실측·치료 효능** 단정 금지. M31 `hormone_like`는 **비생물학 메타포·advisory** 고지.
- **단일 TOE·자동 상용 승격** 단정 금지.

---

**끝.** 갱신 시 본 파일을 덮어쓰고 Vault 미러 스크립트(`sync_notebooklm_sources_to_mkm_data_vault.ps1`)를 선택 실행.
