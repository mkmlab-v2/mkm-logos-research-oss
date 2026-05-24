# MKM 인프라 토폴로지 v1 — Hostinger VPS + Cloudflare (단일 SSOT)

**작성:** 2026-05-21  
**목적:** “어디에 앱을 올리고, 어디는 DNS만 쓰는지”를 **한 장**으로 고정해 hPanel·타 클라우드·SSH 호스트 혼동을 막는다.

**머신 판정 SSOT:** `docs/final/MKM_HOSTINGER_CLOUDFLARE_TOPOLOGY_V1.json` (에이전트·스크립트 기본 참조)

---

## 한 줄 (지휘관·에이전트 공통)

| 층 | MKM 정책 |
|----|----------|
| **컴pute(앱·DB·PM2·nginx origin)** | **Hostinger VPS만** — SSH/scp, `pm2`, `/var/www/*`, 모노레포 `git pull` |
| **엣지(도메인·프록시·메일·리다이렉트)** | **Cloudflare만** — DNS, orange-cloud proxy, Email Routing, apex redirect 등 |
| **금지** | Hostinger **공유호스팅 hPanel `public_html`**, AWS/GCP/Azure **앱 서버**, Cloudflare **Pages/Workers를 본선 앱 호스트로**, GitHub Pages **상용 본선** |

앱 바이너리·Node·Python·SQLite·`.env`는 **항상 VPS 디스크**에만 둔다. Cloudflare는 **요청을 VPS로 넘기거나** 메일/리다이렉트만 처리한다.

---

## 2층 모델 (ASCII)

```
[브라우저/클라이언트]
        │
        ▼
┌───────────────────────────────┐
│  Cloudflare (엣지만)           │
│  · DNS A/AAAA/CNAME → VPS IP   │
│  · Proxy/CDN (주황 구름)        │
│  · Email Routing (MX/규칙)     │
│  · Redirect (예: jema12→jema-ai)│
└───────────────┬───────────────┘
                │ origin (HTTPS)
                ▼
┌───────────────────────────────┐
│  Hostinger VPS (유일 compute)  │
│  · nginx → 127.0.0.1:PM2 ports │
│  · PM2: no1kmedi-com, mkmlife, │
│    bitcoin-live-small-24h, …   │
│  · 정적: /var/www/jemaai, mkmlab│
└───────────────────────────────┘
```

---

## Hostinger VPS — SSH 이름이 둘로 보이는 이유 (실수 방지)

**물리:** MKM 본선은 **Hostinger VPS 한 대(또는 팀이 실측한 소수 대)** 를 전제로 문서화한다. **앱 호스트를 AWS 등으로 두지 않는다.**

| 접속 표기 | 전형적 용도 | 레포 기본 |
|-----------|-------------|-----------|
| **`vps-mkmlife`** | `~/.ssh/config` **별칭** — 실매매 PM2, destiny 모노레포 `/opt/mkm-destiny-ai-41e38ec6` | `VPS_BITCOIN_LIVE_RUNTIME_POINTER_V1.json` · `ship_to_vps.ps1 -VpsHost` 기본 |
| **`MKM_VPS_HOST`** (예: `srv1101456.hstgr.cloud`) | `.env` **호스트명** — scp/sync 스크립트, lab 트리 `/opt/mkm-lab-workspace-v2`, 쇼룸·mkmlab·L3 ANN 업로드 | `sync_showroom_to_vps.ps1` · `Sync-MkmlabRedesignToVps_v1.ps1` · `Sync-LogosRagL3ProdIndexToVps_v1.ps1` |

**같은 머신인지:** 별칭과 FQDN이 **다르게 보여도** 대개 **동일 Hostinger VPS**다. 혼동 시 한 번만 실측:

```bash
ssh vps-mkmlife "hostname; hostname -I"
ssh root@YOUR_MKM_VPS_HOST "hostname; hostname -I"
```

IP·hostname이 같으면 **동일 호스트** — 문서·스크립트만 표기가 다른 것이다.

### VPS 위 모노레포 트리 (둘 다 Hostinger 디스크 — 역할 분리)

| 경로 (기본·문서) | 역할 | PM2/운영 |
|------------------|------|----------|
| `/opt/mkm-destiny-ai-41e38ec6` | **본선 destiny** — bitcoin-trading, no1kmedi, jema-ai upstream | `bitcoin-live-small-24h`, `no1kmedi-com`, … |
| `/opt/mkm-lab-workspace-v2` | **lab/자동화/연구** — Fact-Lock, 쇼룸 산출, L3 아티팩트 scp 대상 | cron·일회성; **live PM2 cwd가 여기인지 `pm2 show`로 확인** |

**판정 규칙:** 문서 경로 < **`pm2 show <앱>`의 `exec cwd`·`script path`**.  
레거시 `/opt/bitcoin-trading-live` 는 **live 배포 루트로 쓰지 않음** (`VPS_BITCOIN_LIVE_RUNTIME_POINTER_V1.json`).

---

## Cloudflare — 쓰는 것 / 안 쓰는 것

### ALWAYS (엣지)

- **DNS** — apex·`www`·`api` 등 → **Hostinger VPS IP** (또는 VPS nginx가 받는 CNAME)
- **HTTP(S) proxy** — 공개 웹·API 앞단 (지연·캐시·WAF는 제품 설정 따름)
- **Email Routing** — `hello@`, `contact@` → `support@mkmlife.com` 등 (`setup_cloudflare_email_routing_v1.py`)
- **Redirect** — 예: `jema12.com` → `jema-ai.com` (`Invoke-CloudflareJema12RedirectSetup_v1.ps1`)
- **점검 산출** — `reports/cloudflare_dns_ensure_*.json`, `reports/cloudflare_dns_ensure_chain_latest.json`

Zone 픽스처 예: `scripts/data/hostinger_full_exit/*_cloudflare_zone_v1.json` (no1kmedi, mkmlife, mkmlab, a-codeai, jema12, personadiary). `jema-ai.com`·`jemaai.cloud`는 ensure 리포트 우선 (`MKM_DOMAIN_PORTFOLIO_POINTER_V1.md`).

**존·토큰 재발 방지 (2026-05-23):** 머신 SSOT `docs/final/artifacts/mkm_cloudflare_zone_registry_v1.json` — 8개 CF 존·역할·혼동 쌍(`jemaai.cloud` ≠ `jema-ai.com`). 원클릭 점검:

`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmCloudflareRecurrenceGuardBundle_v1.ps1`

산출: `reports/mkm_cloudflare_zone_audit_v1_latest.json` · `reports/cloudflare_token_roles_triage_v1_latest.json`. **jemaai rulesets API 통과 ≠ jema-ai.com redirect API 통과** — 대시보드로 1-hop 넣었어도 triage의 `jema_ai_redirect_403`은 scope 1회 추가를 의미(만료 아님).

### NEVER (MKM 본선 앱 호스트로)

- Cloudflare **Pages / Workers** 에 Next/Express **본선** 배포
- Cloudflare만 두고 **VPS origin 없음** 인 상용 구성
- **Hostinger hPanel 공유호스팅** `public_html` — mkmlab·jema-ai·쇼룸 **본선 아님** (문서·probe 반복 확인)

---

## 도메인 → 어디에 붙는지 (요약)

상세 표·CTA: `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md`.

| 도메인 | Cloudflare | Origin (Hostinger VPS) |
|--------|------------|-------------------------|
| jema-ai.com, no1kmedi.com, mkmlife.com | DNS·proxy·(메일) | PM2 + nginx (`NO1KMEDI_MKMLIFE` SSOT) |
| jemaai.cloud, api.jemaai.cloud | DNS·proxy | `/var/www/jemaai` · 쇼룸 스크립트 · **CF 수동 엣지:** `JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md` |
| mkmlab.space | DNS·NS(zone) | `/var/www/mkmlab` — **hPanel 아님** |
| a-codeai.com | DNS·proxy | nginx 정적 + API 분리 |
| jema12.com | Redirect·DNS | **앱 호스트 아님** (→ jema-ai) |

---

## 배포·동기화 스크립트 — 어디로 가나

| 작업 | 스크립트 | 대상 (Hostinger) |
|------|----------|------------------|
| Git 본선 반영 | `scripts/deploy/ship_to_vps.ps1` | `VpsRepoPath` 기본 `/opt/mkm-lab-workspace-v2` — **PM2 cwd와 다를 수 있음** |
| 쇼룸 정적 | `scripts/sync_showroom_to_vps.ps1` | `/var/www/jemaai` (env `JEMAAI_VPS_SHOWROOM_ROOT`) |
| mkmlab 정적 | `scripts/Sync-MkmlabRedesignToVps_v1.ps1` | `/var/www/mkmlab` |
| mkmlife 배포 | `deploy-to-hostinger.ps1` (레거시 경로 E: 가능) | `/var/www/mkmlife` 등 — **PM2 실측 우선** |
| Logos L3 ANN | `scripts/Sync-LogosRagL3ProdIndexToVps_v1.ps1` | `…/docs/final/artifacts/` on lab path |

**공통 env:** `MKM_VPS_HOST`, `MKM_VPS_USER`, `MKM_VPS_SSH_KEY_PATH`, `MKM_VPS_SCP_EXTRA_ARGS` (`.env.example` VPS 절).

---

## 에이전트·문서 교차 참조 (읽는 순서)

1. **본 파일** (토폴로지 고정)
2. `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` — 코드는 로컬, VPS는 pull·PM2
3. `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` — 도메인별 런북
4. `docs/final/VPS_BITCOIN_LIVE_RUNTIME_POINTER_V1.json` — 실매매 PM2
5. `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` — mkmlife/no1kmedi (**jema12 런북 혼용 금지**)

---

## NEVER (재발 방지 체크리스트)

- jema12 nginx 절차를 **mkmlife Hostinger**에 적용
- **hPanel 파일관리자·public_html** 를 mkmlab/jema-ai 본선으로 안내
- **Cloudflare만** 고치고 VPS origin·PM2를 빼먹음
- `srv1101456…` 와 `vps-mkmlife` 를 **서로 다른 클라우드**처럼 서술
- VPS scp 성공 = **실매매 GO** (격벽·human gate 별도)

---

**상태:** v1 고정 (2026-05-21). 인프라 변경 시 **본 파일 + JSON** 먼저 갱신 후 도메인·VPS 포인터를 맞춘다.
