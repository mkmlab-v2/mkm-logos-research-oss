# MKM 도메인 · 임상·체질 데이터 레인 v1 (Fact-Lock)

**상태:** 운영 SSOT (2026-05-31)  
**상위:** `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` · `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.0  
**격벽:** `docs/final/artifacts/clinic_constitution_dual_lane_policy_v1.json` · `docs/final/CLINIC_CONSTITUTION_MVP_V1.md`

---

## 1. 3층 토폴로지 (대외)

```text
[브랜드 허브]     jema-ai.com / app.jema-ai.com  (소스 projects/no1kmedi)
        │
        ├── [소비자 B2C]  mkmlife.com     — MAI·14문항 설문 · consumer_survey_only
        ├── [임상 B2B]    app…/clinician  — SOAP · CDSS · care bundle · physician_gold (제안서·대외 공식 URL)
        ├── [한의사 포털] clinic.no1kmedi.com · no1kmedi.com(apex) — 동일 Next·/clinician (현장 북마크)
        ├── [관측]        jemaai.cloud    — 쇼룸 · NON_GATING
        ├── [API]         a-codeai.com
        └── [연구소]      research.no1kmedi.com  (구 mkmlab.space → 301)

[인프라·결제]     api.no1kmedi.com · eno. · saju-api. — PayApp·Express (UI 없음)
[레거시]          jema12.com → 301 jema-ai.com · mkmlab.space → 301 research.* (갱신 중단)
```

**명명:** `no1kmedi` = 레포·PM2 **내부 식별자**. **대외 브랜드**는 **`jema-ai.com`**; **한의사 실무 URL**은 **`clinic.no1kmedi.com`** 병행 (`JEMA_AI_DOMAIN_POINTER_V1.md`).

---

## 2. 도메인 × 제품 × 데이터 레인

| 도메인 | 제품·표면 | 소스 | 데이터 레인 |
|--------|-----------|------|-------------|
| **jema-ai.com** / **app.** | 허브 · `/enterprise` · **`/clinician`** | `projects/no1kmedi` | **physician_gold** — 사상 4진 · SOAP · care bundle · 원장 확정 → `data/clinic/*.jsonl` |
| **mkmlife.com** | 원퀘스천 · ask-one | `projects/mkm/mkm-life` | **consumer_survey_only** — 14문항 · **MAI** · 사상/확정 **미노출** |
| **jemaai.cloud** | 공개 전광판 | 쇼룸 정적·게이트웨이 | 없음 (실매매·임상 합선 금지) |
| **clinic.no1kmedi.com** · **no1kmedi.com**(apex) | 한의사 진료 보조 · `/clinician` | `projects/no1kmedi` + `middleware.ts` | **physician_gold** — app.jema-ai.com/clinician 과 **동일 앱** |
| **research.no1kmedi.com** | MKM LAB 연구소 정적 | `mkmlab-redesign/` → `/var/www/mkmlab` | 제품 스토리만 · AI·실매매 합선 금지 |
| **api.no1kmedi.com** 등 | PayApp · Express | `payapp-api/` | **UI 없음** — apex/clinic 과 nginx vhost 분리 |

**금지:** consumer KPI ↔ physician KPI 합산 · 오행%→체질 합산 · MAI를 임상 진단으로 표기 · MBTI® 호칭.

---

## 3. 체질·설문·SOAP 배치 (확정)

| 기능 | 도메인 | 스크립트·API |
|------|--------|----------------|
| 진료실 설문 + AI 가설 + SOAP + 솔루션 | **app.jema-ai.com/clinician** | `build_han_physician_clinical_assist_turn_v1.py` · care bundle 체인 |
| 14문항 + MAI 카드 | **mkmlife.com** (`/ask-one` → 추후 전용 경로) | `/api/v1/constitution/survey/*` · `lookup_gtm_mai_archetype_v1.py` |
| 비식별 학습 | 모노레포 ledger | `clinic_constitution_mvp_ledger_v1.py` — `ref_token`만 |

**후속(2026-05-31):** `/clinician` → `GET /api/clinician/constitution-survey-ssot` · `MKM_WORKSPACE_ROOT` 시 `clinic_constitution_survey_item_bank_v1.json` 메타 · mkmlife 소비자 URL은 env(`NEXT_PUBLIC_MKMLIFE_CONSUMER_SURVEY_URL`).

---

## 4. 허브 CTA (코드 SSOT)

`projects/no1kmedi/marketing-site/public-copy.json` → `hub_links.*`  
검증: `projects/no1kmedi`에서 `npm run check:marketing-copy`.

| 키 | 목적 |
|----|------|
| `clinician_support` | app.jema-ai.com/clinician (대외 공식) |
| `clinician_no1kmedi_portal` | clinic.no1kmedi.com |
| `research_mkmlab` | research.no1kmedi.com |
| `mai_profile_card` | mkmlife 소비자 설문·MAI (ask-one 등) |

교차 표: `MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` §1.1b.

---

## 5. no1kmedi.com — 갱신·한의사 포털·연구소 이전 (운영 메모)

| 항목 | 레포·실측 |
|------|-----------|
| **등록 만료** | hPanel 스냅샷 **2026-12-17** — `hostinger_hpanel_domains_manifest_v1.json` |
| **CF Zone** | `1516522160411707c33f84e145416a53` · **active** |
| **한의사** | `clinic.no1kmedi.com` + apex → Next `:3010` · `middleware.ts` → `/clinician` |
| **연구소** | `research.no1kmedi.com` → `/var/www/mkmlab` (구 `mkmlab.space` **301** 후 갱신 중단) |
| **인프라 유지** | `api.` · `eno.` · `saju-api.` · Email Routing — apex 포털과 **vhost 분리** |

**로컬 번들:** `scripts/Invoke-No1kmediDomainParallelMigrate_v1.ps1` · CF DNS `ensure_no1kmedi_research_clinic_cloudflare_dns_v1.py` · VPS nginx `apply_*_no1kmedi_*_v1.sh` · mkmlab 퇴역 `apply_mkmlab_space_retire_301_v1.sh`.

---

## 6. 마케팅·진화 가드

- `physician_gold` **N≥20** 전 consumer↔physician 일치율 **대외 주장 금지**.
- B-track · `[HYPO]` · Track A·실매매 자동 합선 없음.

---

*version: 1.1.0 · 2026-05-31 — research/clinic no1kmedi · mkmlab retire*
