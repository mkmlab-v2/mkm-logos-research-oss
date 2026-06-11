# personadiary.com — 도메인 포인터 v1 (미확정 항목 명시)

**목적:** `personadiary.com` 을 **다른 MKM 소비자 제품(mkmlife·no1kmedi 랜딩 등)과 동일 배포·동일 API로 가정하지 않도록** 레포에 고정한다. NotebookLM·구 기획의 B2C 일기·페르소나 서술은 **참고**이며, **데이터 주거·법무는 별도 검토**다.

**프리뷰 운영 SSOT (2026-05-20):** `docs/final/artifacts/personadiary_preview_ops_v1_latest.json` — 호스트 라우팅·배포·메일·면책 경계. **제품 본선 확정 아님.**

---

## 0) 프리뷰 단계 (2026-05-20 · Fact-Lock)

| 항목 | 프리뷰 값 | 비고 |
|------|-----------|------|
| **단계** | `preview_only` | 결제·일기 저장·Track A 합선 **없음** |
| **레포 경로** | `projects/no1kmedi` | 전용 앱 트리 **없음** — `/personadiary` + `middleware.ts` 호스트 rewrite |
| **PM2** | `no1kmedi-com` | `exec cwd`: `/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi` · upstream `:3010` |
| **nginx** | `scripts/deploy/linux/nginx-personadiary-com.conf.example` | `personadiary.com` / `www` / `preview` → 동일 upstream |
| **데이터** | **미구현** | 사용자 일기·PII 저장 **없음** — 법무 전 단정 금지 |
| **메일** | `hello@` · `contact@` → `support@mkmlife.com` | Cloudflare Email Routing (2026-05-20) |

---

## 1) 현재 상태 (Fact-Lock)

| 항목 | 값 |
|------|-----|
| **레포 내 전용 앱 경로** | **미확정** — `projects/...` 에 고정된 트리 없음. |
| **전용 런북** | **없음** — 확정 전 **타 도메인 런북 복붙 금지**. |
| **PM2 앱 이름 / `exec cwd`** | **미확정** — 본선은 **`pm2 describe` 실측**만 신뢰. |
| **개인 일기·페르소나 데이터** | 저장 위치·암호화·해외 이전 여부는 **제품 설계·법무 확정 전** 레포 SSOT로 단정하지 않는다. |

---

## 2) 확정 전 금지 (VPS·혼선 방지)

- **mkmlife**(`mkm-life`)·**no1kmedi** 백엔드·**jemaai.cloud** 쇼룸과 **동일 DB·동일 API 키·동일 PM2 앱**이라고 가정하고 nginx/upstream 을 묶지 않는다.
- `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` 의 **면책·§10 배지** 문구를 personadiary UI에 **그대로 복사해 “동일 서비스”로 표시**하지 않는다 — **화면별 법무 검토** 전제.
- 기획 노트만으로 **본선 URL·웹훅·실키** 를 배포한다고 단정하지 않는다.

---

## 3) 확정 시 이 문서에 채울 항목 (체크리스트)

- [x] Git 원격 또는 모노레포 하위 경로 — **프리뷰:** `projects/no1kmedi` (`personadiary_preview_ops_v1_latest.json`)
- [x] 로컬 작업 디렉터리 — **프리뷰:** `C:\workspace\projects\no1kmedi`
- [x] PM2 이름 · `exec cwd` (실측) — **프리뷰:** `no1kmedi-com` · `/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi`
- [x] nginx `server_name` 및 정적/API 분리 여부 — **프리뷰:** vhost → `:3010` (Next `/personadiary`)
- [ ] 데이터 저장소(로컬 전용 / 서버 / 분리 계정) — **미확정** (프리뷰는 무저장)
- [x] `MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` 표 갱신 — **2026-06-10** (디자인 허브·Phase 2 lattice ritual; `preview_only` 유지)
- [x] **디자인 허브 푸터** — `PersonadiaryHubFooter` · `mkm_domain_design_tokens_v1.json` · 라이브 스모크 `Run-PersonadiaryPortalDesignSmoke_v1.ps1`
- [x] **Phase 2 UI (B-track)** — Lattice Convergence + Major-22 ritual LUT (`personadiary_ritual_draw_lut_major22_v1.json` · bloom slice); **세션 저장만** · mkmlife API 합선 없음
- [x] **멀티도메인 결선** — `Invoke-MkmDomainDesignClosureBundle_v1.ps1` · 산출 `reports/mkm_domain_design_closure_v1_latest.json` (`closure_ok`)

---

## 4) 오늘의 마음 가이드 패키지 (PersonaDiary 홈 UX · 2026-05-22)

| 항목 | SSOT |
|------|------|
| **제품 콘셉트** | 명리 일운 + MKM 4AI + 라이프(날씨·컬러·식사) + 성경 앵커(Logos) 융합 **가이드형** 답변 — 의료·투자·실매매·예언% **단정 없음** |
| **계약** | `docs/final/artifacts/PERSONADIARY_DAILY_RESPONSE_PACKAGE_V1_CONTRACT.json` |
| **빌드** | `scripts/build_commander_daily_fortune_v1.py` → `scripts/assemble_personadiary_daily_response_package_v1.py` |
| **산출** | `docs/final/artifacts/personadiary_daily_response_package_v1_latest.json` · `projects/no1kmedi/public/data/personadiary_daily_response_package_v1.json` |
| **API** | `GET /api/personadiary/daily-guide` (`projects/no1kmedi`) |
| **UI** | `PersonadiaryDailyGuideCards` + `PersonadiaryReflectTeaser` + **Phase 2** `PersonadiaryRitualDraw` / `PersonadiaryLatticeOverlay` (`[HYPO]` · preview_only) |
| **격벽** | `[가설]` · `[NON_GATING]` · preview_only · mkmlife/jemaai **합선 금지** |

텔레그램 `personal` 다이제스트와 **동일 upstream** (`commander_daily_fortune_latest.json`)을 쓰되, PersonaDiary는 **ui_blocks**로 렌더한다.

**프로필(확장 v1):** `data/personadiary/profile_registry_v1.json` — `profile_id`(기본 `commander`)별 `public/data/profiles/{id}.json`. API: `?profile_id=` · reflect body `profile_id`. 일일 갱신: `scripts/Register-PersonadiaryDailyGuideDailyTask.ps1`(기본 07:15) 또는 `scripts/refresh_personadiary_profile_packages_v1.py`.

**VPS 배포:** `scripts/Invoke-PersonadiaryParallelBundle_v1.ps1 -Deploy` (가이드 갱신 → `npm run build` → `Deploy-No1kmediDestinyTarball_v1.ps1`). SSOT 호스트: `personadiary_preview_ops_v1_latest.json` → `vps-mkmlife` · PM2 `no1kmedi-com`.

---

## 5) 교차 참조

- **mkmlife.com** 원퀘스천·단건 과금 락 — `NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` §11 — personadiary 와 **합쳐서 서술 금지** (제품이 다르면).
- **jemaai.cloud** 공개 쇼룸 — 실매매·조종실 격벽; personadiary 와 **동일 “관측 파이프”로 합선 금지** (역할이 다르면).

**개정:** 체크리스트 완료 후 v2 또는 “확정” 절 추가.
