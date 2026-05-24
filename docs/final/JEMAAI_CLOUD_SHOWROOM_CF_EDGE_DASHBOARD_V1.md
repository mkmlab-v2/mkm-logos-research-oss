# jemaai.cloud 쇼룸 — Cloudflare 대시보드 수동 엣지 규격 v1

**작성:** 2026-05-22  
**목적:** API 토큰에 **Zone Rulesets Edit**가 없을 때(O-P23 BLOCK), 지휘관이 **Cloudflare Dashboard**에서만 장전하는 정본.  
**Zone:** `jemaai.cloud` · zone id `cf557dfa09436d998416ad849e73c0ec`  
**대시보드(지휘관):** https://dash.cloudflare.com/646e42cf881ab43043c32430e99d9af4/jemaai.cloud  
**Origin:** Hostinger VPS `148.230.97.246` (`/var/www/jemaai`, nginx snippet `jemaai_showroom_ui.conf`)  
**자동화 프로브:** `scripts/ensure_jemaai_cloud_cf_edge_hardening_v1.py` → `reports/jemaai_cloud_cf_edge_hardening_v1_latest.json` (rulesets API는 토큰 scope 없으면 `Authentication error` — **수동이 SSOT**)

**인접:** `docs/final/artifacts/cloudflare_api_no1kmedi_ops_checklist_v1.json` (zone **no1kmedi.com** · `api.no1kmedi.com` 전용 — 혼용 금지)

---

## 재발 방지 (CF 토큰 · 2026-05-22 고정)

| 역할 | 환경 변수 | zone | 에이전트 금지 |
|------|-----------|------|----------------|
| mkmlife UV/Analytics | `MKM_MKMLIFE_CF_ANALYTICS_TOKEN` | mkmlife.com | jemaai apply 실패로 **mkmlife 토큰 재생성** 안내 금지 |
| jemaai 쇼룸 rulesets | `CLOUDFLARE_RULESETS_API_TOKEN` | jemaai.cloud | **`CLOUDFLARE_API_TOKEN` 덮어쓰기** 금지 |
| DNS/일반 | `CLOUDFLARE_API_TOKEN` | 다존 | jemaai 전용 토큰으로 **교체** 금지 |

**진단 SSOT (매번 먼저):** `py scripts/check_cloudflare_token_roles_v1.py` → `reports/cloudflare_token_roles_triage_v1_latest.json` · `recurrence_guard.agent_instruction_ko`

**판정:** `token_verify.success=true` 이고 rulesets phase **403·code 10000** → **만료 아님 · scope/키 분리**. **새 토큰 매일** 안내 금지.

**1회 수정:** secret JSON → `scripts/Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1` (**RULESETS 키만**).

**수동 완료 후:** 공개 autoverify 15/15면 API 재적용 **optional** — triage exit 2여도 사이트 정상일 수 있음.

---

## O-P23 판정 (서사 금지)

| 구분 | 판정 |
|------|------|
| 인프라 점검 루프 | smoke · topology · nginx `-t` · 저부하 probe **통과** |
| CF rulesets API 자동 생성 | **BLOCK** (인증/scope) — 본 문서 **수동**으로 대체 |
| 부하 probe 540/540 | **`not_media_scale`** — 10k RPS·언론급 **안전 승격 근거 아님** |

---

## 대시보드 장전 표 (정본)

| 규칙 분류 | Expression (권장 초안) | Action | Rationale |
|-----------|------------------------|--------|-----------|
| **Rate Limit** | `(http.host in {"jemaai.cloud" "www.jemaai.cloud" "api.jemaai.cloud"}) and (http.request.uri.path contains "/public_showroom" or http.request.uri.path contains "/showroom_")` | **Block** 60s · **100 req/min per IP** · characteristics: IP · (burst **200** if UI offers) | 단일 VPS origin CPU·스크래핑 완화 |
| **Cache Rules — HTML** | `(http.host in {"jemaai.cloud" "www.jemaai.cloud"}) and http.request.uri.path.extension eq "html" and http.request.uri.path contains "public_showroom"` | **Bypass cache** (권장) 또는 Edge TTL **≤ 5m** | 스테이징·배포 후 stale HTML 방지 |
| **Cache Rules — JSON** | `(http.host in {"jemaai.cloud" "www.jemaai.cloud" "api.jemaai.cloud"}) and (http.request.uri.path contains "showroom_" or http.request.uri.path contains "_slice_") and http.request.uri.path.extension eq "json"` | **Bypass cache** | origin `Cache-Control: no-store` (`jemaai_showroom_ui.conf`)와 정합 |
| **WAF** | Zone → Security → WAF | **Managed rulesets ON** (기본) | 1차 봇·취약점 스캔 컷; 커스텀 규칙은 최소 |

**Dashboard 경로 (2026 UI):**

| 할 일 | 링크 (같은 zone) |
|------|------------------|
| Zone 홈 | https://dash.cloudflare.com/646e42cf881ab43043c32430e99d9af4/jemaai.cloud |
| WAF | …/jemaai.cloud/security/waf |
| Rate limiting | …/jemaai.cloud/security/rate-limiting (또는 WAF 안 **Rate limiting rules**) |
| Cache Rules | …/jemaai.cloud/caching/cache-rules |

---

## 장전 후 검증 (로컬, exit code SSOT)

```powershell
py scripts/check_showroom_trust_viz_public_chain_v1.py
py scripts/build_showroom_static_load_probe_v1.py --requests 90 --workers 10
```

선택: `py scripts/ensure_jemaai_cloud_cf_edge_hardening_v1.py` (DNS·SSL만 자동; rulesets는 대시보드 반영 후에도 API scope 없으면 여전히 BLOCK일 수 있음)

**완료 신호 (지휘관):** 대시보드 스크린샷 또는 한 줄 — `CF jemaai showroom edge manual done` — 에이전트는 `MISSION_LOG` O-P24에만 기록.

---

## 자동화로 바꾸기 (권장 순서)

현재 `CLOUDFLARE_API_TOKEN`은 **DNS만** 되고 **Rulesets는 403**입니다. **별도 토큰**을 쓰면 대시보드 수동 없이 스크립트로 규칙을 넣을 수 있습니다.

### 1단계 — Cloudflare 토큰 (커스텀 빈 화면 **비권장**)

**지휘관 화면에 `Zone Read` / `WAF` / `Cache Rules`가 **아예 안 뜨면** — 레포 안내가 틀렸거나, **왼쪽 첫 칸(권한 그룹)** 을 `영역`으로 안 고른 상태입니다. **빈 커스텀 토큰을 더 채우지 말고** 아래 **A → B → C** 순으로 하세요.

#### A) **가장 빠름 — 이미 있는 토큰 편집** (권장)

1. https://dash.cloudflare.com/profile/api-tokens → 목록에서 **`MKM-mkmlab-zone-settings-dns-v1`** (또는 **Cache Rules + Zone WAF** 가 보이는 토큰) → **편집**
2. **Zone Resources**가 **`jemaai.cloud` 1개**인지 확인 (다른 zone이면 jemaai만 남기거나, jemaai용으로 복제)
3. **Roll / 재발급** → 값 **한 번만** 복사 → PC `CLOUDFLARE_RULESETS_API_TOKEN` (또는 기존 `CLOUDFLARE_API_TOKEN` 편집본) — **채팅·Git 금지**
4. `py scripts/check_jemaai_cloud_cf_rules_token_v1.py` → **exit 0**

> **새 이름 `MKM-jemaai-showroom-rulesets-v1` 빈 커스텀 토큰**은 A가 실패할 때만.

#### B) **API 포기 — 대시보드 수동** (이미 15/15면 충분)

본 문서 **「대시보드 장전 표」** + 링크(WAF · Rate limiting · Cache Rules)만 맞추면 됩니다. 토큰 UI와 **무관**.

#### C) **꼭 새 커스텀 토큰일 때만** — Cloudflare 공식 순서

공식: `developers.cloudflare.com/fundamentals/api/get-started/create-token/` — **6단계: 먼저 권한 그룹(Account / User / Zone)을 고른 뒤** 세부 권한·Read/Edit.

**Permissions** 표의 **왼쪽 칸 = jemaai zone이 아님** = **권한 그룹 종류(계정·사용자·영역)** 입니다. **아래 「Zone Resources」** 가 `jemaai.cloud` zone 지정입니다.

| # | 왼쪽 (권한 **그룹**) | 가운데 (세부 권한 — 검색) | 오른쪽 |
|---|---------------------|-------------------------|--------|
| 1 | **Zone** / **영역** | `Zone` → **Zone Read** (또는 `영역` + `읽기`) | Read |
| 2 | **Zone** / **영역** | `WAF` → **Zone WAF** → | **Edit** |
| 3 | **Zone** / **영역** | `Cache` → **Cache Rules** → (**Cache Settings** 만 있으면 그쪽 **Write/Edit** 도 시도) | **Edit** |
| 4 | **Account** / **계정** | `Rulesets` → **Account Rulesets** | **Edit** |

> Cache Rules API 공식: Zone Cache Rules Edit **+** Account Rulesets Edit (`developers.cloudflare.com/cache/how-to/cache-rules/create-api/`). **4행 없으면** apply가 막힐 수 있음.

**검색이 여전히 비면:** (1) 왼쪽을 **Account**로 두고 가운데 `Zone Read`를 찾지 않았는지 확인 (2) 프로필 **언어 EN** 후 동일 검색 (3) **A 또는 B**로 전환.

1. https://dash.cloudflare.com/profile/api-tokens → **Create Token** → **Create Custom Token**
2. **Token name:** `MKM-jemaai-showroom-rulesets-v1`
3. 위 표 **C**대로 Permissions 추가
4. **Zone Resources:** Include → **Specific zone** → **`jemaai.cloud`만**
5. **Client IP / TTL:** 필요 시만 제한
6. **Continue to summary** → **Create Token** → **값을 한 번만 복사** (채팅·Git·스크린샷 금지)

### 2단계 — PC에만 저장 (Windows)

**방법 A (권장):** 시스템 환경 변수

1. Windows 검색 → **환경 변수** → 사용자 변수 **새로 만들기**
2. 이름: `CLOUDFLARE_RULESETS_API_TOKEN`
3. 값: 방금 복사한 토큰
4. **Cursor 완전 재시작** (또는 Developer: Reload Window + 새 터미널)

**방법 B:** `C:\workspace\.env` (Git 커밋 금지)

```env
CLOUDFLARE_RULESETS_API_TOKEN=여기에_붙여넣기
```

그다음:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/sync_required_env_to_user.ps1
```

### 3단계 — 권한 점검 (exit 0이면 자동화 가능)

```powershell
cd C:\workspace
py scripts/check_jemaai_cloud_cf_rules_token_v1.py
```

- `automation_ready: true` → 다음 단계
- `exit 2` → 토큰 scope·zone 지정 다시 확인

### 4단계 — 규칙 자동 적용

```powershell
py scripts/apply_jemaai_cloud_showroom_cf_edge_rules_v1.py
```

또는 원클릭:

```powershell
powershell -File scripts/Invoke-ApplyJemaaiShowroomCfEdgeRules_v1.ps1
```

성공 시: `reports/jemaai_cloud_showroom_cf_edge_apply_v1_latest.json` → `"ok": true`

### 5단계 — 검증 (에이전트/지휘관 공통)

```powershell
powershell -File scripts/Invoke-JemaaiShowroomEdgeAutoverify_v1.ps1 -SkipApply
```

(`-SkipApply`는 이미 4단계에서 적용했을 때)

---

**주의 (토큰 전략):**

| 방식 | 적합 | 비고 |
|------|------|------|
| **기존 `CLOUDFLARE_API_TOKEN`에 WAF+Cache Rules Edit 추가** | 1인·소수 zone·귀찮음 최소화 | **권장(실무)** — 커스텀 토큰 **가운데 검색**으로 `Zone WAF`·`Cache Rules` **Edit** (트리 메뉴명과 다를 수 있음) |
| **`CLOUDFLARE_RULESETS_API_TOKEN` 분리** | 팀·토큰 유출 시 피해 최소화 | 보안 최우선일 때만 |

넓힐 때도 **Zone Resources → `jemaai.cloud`만** Include 하면 DNS 토큰보다 훨씬 안전합니다(전 계정 All zones 금지).

---

## Fact-Lock (격벽)

- 쇼룸·공개 전광판: **`[HYPO]`** · Track A·실매매·MS 본문 수치 **자동 합선 금지**.
- MS 상용 연대기 스코어: **역사 `text_blind` 4.3%만** (`logos_chronology_era_blind_eval_text_blind_v1_latest.json`).
- hardset 92.6% · gold_tags 78.7% · RAG harness 100% · **대외·MS 금지**.

---

**상태:** v1 고정 (2026-05-22). 토큰에 Rulesets Edit 추가 시에도 **본 수동 표를 먼저** 맞춘 뒤 자동화 검토.
