# 금융 예언 → SSH/VPS 실시간 비트코인 매매 반영 명령서 (v1.1)

**목적:** **Fact-Safe 금융 예언·거버넌스 산출물**을, **실제로 PM2가 돌리는** 비트코인 런타임이 읽는 `risk_profile_fact_safe_latest.json`에 쓰고, **단일 PM2 앱만** 재기동한다.

**적용 범위:** `projects/bitcoin-trading`이 참조하는 리스크 프로파일  
`projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json`  
(코드 근거: `src/daemon/bitcoin_trading_daemon.py`의 `risk_profile_candidates` 첫 후보, 트레이더는 `crypto_nitro_live_trader.py`의 동일 상대 경로 후보)

---

## 0. 혼동 방지 — 본선 레포는 PM2가 가리키는 디렉터리 하나

VPS에 모노레포 클론이 **여러 개** 있을 수 있다 (`/opt/mkm-lab-workspace-v2`, `/opt/mkm-destiny-*` 등). **어느 경로에서 `sync`를 돌리느냐가 곧 효력 범위이다.**

| 구분 | 내용 |
|------|------|
| **배포 SSOT (기본)** | `scripts/deploy/ship_to_vps.ps1`의 기본 `VpsRepoPath`는 **`/opt/mkm-lab-workspace-v2`**. 로컬에서 `ship_to_vps`로 맞추는 본선은 이 경로를 전제로 한다. |
| **절대 원칙** | **`pm2 show <PM2_NAME>`**으로 확인한 **`exec cwd`(또는 스크립트가 속한 모노레포 루트)** = 이 명령서 전체의 **`<REPO_ROOT>`**. 여기서만 `git pull` + `sync_fact_safe_risk_profile.py` + `memory/v2/risk/` 갱신을 한다. |
| **흔한 실수** | 다른 클론(예: destiny 전용 경로)에서만 `pull`/`sync`를 돌리고, PM2는 lab-workspace 쪽 `start_live_trading.py`를 실행하는 경우 → **JSON은 갱신되어도 본선 프로세스는 읽지 않거나, 예전 코드면 로그에 `risk_profile` 로드가 안 나온다.** |
| **코드 버전** | `crypto_nitro_live_trader.py`에 `_load_risk_profile` 등이 없는 **오래된 트리**면, 파일을 맞춰도 **런타임이 로드하지 않는다.** 그 경우 `<REPO_ROOT>`에서 `git pull`로 **본선과 동일 브랜치·커밋**을 맞춘 뒤 재시작한다. |

**필수 첫 명령 (SSH 접속 직후):**

```bash
pm2 show bitcoin-live
# 또는 팀 런북의 실제 앱 이름: pm2 show <PM2_NAME>
```

출력에서 **`exec cwd`** 와 **`script path`** 를 적어 두고, 그 모노레포 루트를 `<REPO_ROOT>`로 고정한다. 이후 절차는 **항상 `cd <REPO_ROOT>`에서만** 수행한다.

---

## 1. 준수 사항 (격벽 · SSOT)

1. **직접 브리지 금지**  
   B-track 스텁·`btrack_hypothesis_prophecy_*.json`·fusion shadow만으로 **주문 로직을 직접 바꾸지 않는다.** 루트 `AGENTS.md`의 **Track A/B direct-bridge 금지** 및 **통합 거버넌스 경유** 원칙을 따른다.

2. **승인된 반영 경로 (한 줄)**  
   `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`  
   + (선택) `docs/final/artifacts/integrated_governance_v1_latest.json`  
   → `scripts/sync_fact_safe_risk_profile.py`  
   → `<REPO_ROOT>/projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json`  
   → 런타임이 로드(해당 버전 코드가 있을 때).

3. **코드 수정 주체**  
   레포 변경은 **로컬에서 커밋·푸시** 후 VPS는 `git pull`만. `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`, `projects/bitcoin-trading/AGENTS.md` 참고.

4. **실거래 전제**  
   본 명령서는 **인프라·파일 동기화**이다. 실계좌·레버리지·키는 **런북·`.env`** 범위에서만 다룬다.

---

## 2. 선행 산출물

다음이 **최신**이어야 `sync_fact_safe_risk_profile.py`가 의미 있는 프로파일을 쓴다.

| 산출물 | 기본 경로 (모노레포 루트 기준) |
|--------|--------------------------------|
| 월간 Fact-Safe 예언 (KOSPI/BTC) | `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json` |
| 통합 거버넌스 (캡·veto 브리지) | `docs/final/artifacts/integrated_governance_v1_latest.json` |

**통합 거버넌스 파일이 VPS에 없으면:** 스크립트는 해당 경로를 빈 문서로 취급해 **`governance_bridge`가 붙지 않는다** (`--integrated-governance ""`와 동일 효과). 캡 브리지까지 쓰려면 로컬에서 생성한 파일을 **`<REPO_ROOT>/docs/final/artifacts/`** 에 반입한 뒤 sync를 다시 실행한다.

생성 루틴 예시(Windows 로컬):  
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_waiting_queue_monthly_check.ps1`

---

## 3. VPS 절차 — `<REPO_ROOT>` = `pm2 show`로 확정한 루트

`<PM2_NAME>`은 `pm2 list`·런북의 **본선 앱 이름 한 개**로 치환한다.

### 3.1 저장소 동기화

```bash
cd <REPO_ROOT>
git status
git pull --ff-only
```

의도하지 않은 로컬 수정이 있으면 **중단**한다.

### 3.2 산출물 반입 (필요 시)

로컬에서만 갱신된 아티팩트를 **`<REPO_ROOT>`** 아래 동일 상대 경로로 복사한다 (`scp` 등).

- `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`
- `docs/final/artifacts/integrated_governance_v1_latest.json` (선택)

### 3.3 리스크 프로파일 동기화 (필수)

```bash
cd <REPO_ROOT>
python3 scripts/sync_fact_safe_risk_profile.py \
  --prophecy docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json \
  --output projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json \
  --integrated-governance docs/final/artifacts/integrated_governance_v1_latest.json
```

- **거버넌스 브리지 끄기:** `--integrated-governance ""`
- **메타데이터:** 기본 `--mode shadow`, `--source fact_safe_prophecy.trinity_governor` — 운영 정책에 맞게 조정.
- **n8n 태그 충돌:** 기존 프로파일이 `n8n.*`인데 Fact-Safe로 덮을 때 거부되면 `--allow-metadata-downgrade` 또는 레거시 규약(`--n8n-source`)·**기본 Git SSOT**(`--repo-source`)를 런북과 맞춘다.

### 3.4 반영 확인

```bash
python3 -c "import json; p='projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json'; d=json.load(open(p,encoding='utf-8')); print(d.get('source'), d.get('mode'), d.get('generated_at'))"
```

### 3.5 런타임 재기동 (단일 앱만)

```bash
pm2 restart <PM2_NAME>
```

**금지:** `pm2 restart all` (런북 예외 없이 사용하지 않음).

### 3.6 건강 확인

```bash
pm2 logs <PM2_NAME> --lines 80
```

코드가 최신이면 `risk_profile` 관련 로그가 나올 수 있다. **안 나오면** (1) 다른 클론에서 sync 하지 않았는지, (2) 이 트리가 `_load_risk_profile` 포함 커밋인지 확인한다.  
거래소 API 오류(예: `leverage` 미전송)는 **본 절차와 별도**로 엔드포인트·환경변수·심볼 설정을 점검한다.

---

## 4. Windows 로컬만 갱신한 뒤 VPS에 옮길 때

로컬에서 `sync_fact_safe_risk_profile.py`로 만든  
`projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json`를  
**`<REPO_ROOT>`의 동일 상대 경로**로 덮어쓴 뒤 **3.5~3.6**만 실행한다.  
복사 대상 경로는 **반드시 `pm2 show`로 잡은 본선 루트** 기준이다.

---

## 5. 롤백

1. 백업해 둔 `risk_profile_fact_safe_latest.json`을 동일 경로에 복원하거나  
2. 이전에 알려진 좋은 예언 JSON으로 `sync_fact_safe_risk_profile.py`를 다시 실행한 뒤  
3. `pm2 restart <PM2_NAME>` 한 번.

---

## 6. 이 명령서가 하지 않는 것

- B-track을 **주문 신호로 직접 매핑**하지 않는다.
- 일반 예언(B 레일) 레지스트리는 **별도 SSOT**이다.

---

## 7. 참조 SSOT

- 로컬 vs VPS: `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`
- bitcoin-trading·VPS 경로: `projects/bitcoin-trading/AGENTS.md`
- 배포 스크립트 기본 VPS 경로: `scripts/deploy/ship_to_vps.ps1` (`VpsRepoPath`)
- 리스크 동기화: `scripts/sync_fact_safe_risk_profile.py`
- 히트율 vs 안정권 우선순위 요약: **§9**

---

## 8. SSH Cursor 에이전트용 프롬프트 (복사용)

아래 블록을 SSH 세션에서 Cursor에 **첫 메시지로 붙여 넣거나**, Cursor **User Rules / 프로젝트 규칙**에 넣어 두면 본선 경로 혼동을 줄일 수 있다.

### 8.1 풀 버전 (권장)

```text
[VPS / 비트코인 본선 — 경로 고정 규칙]

너는 SSH로 접속한 VPS에서만 돕는다. 모노레포 경로는 이름으로 추측하지 않는다.

1) 작업 전 필수: `pm2 show bitcoin-live`(또는 런북의 본선 앱 이름)로 exec cwd와 script path를 확인한다. 그 cwd가 모노레포 루트(REPO_ROOT)다. 이후 모든 `cd`, `git pull`, `sync_fact_safe_risk_profile.py`는 REPO_ROOT에서만 실행한다.

2) VPS에 클론이 여러 개 있을 수 있다(/opt/mkm-lab-workspace-v2, /opt/mkm-destiny-* 등). 로컬 `ship_to_vps.ps1` 기본은 `/opt/mkm-lab-workspace-v2`이지만, 항상 1)의 PM2 cwd가 본선이다. 다른 디렉터리에서만 pull/sync 하면 본선 프로세스는 그 JSON·코드를 읽지 않는다.

3) Fact-Safe 리스크 반영은 `scripts/sync_fact_safe_risk_profile.py`를 REPO_ROOT에서 실행하고, 출력은 `projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json`이다. B-track·스텁을 주문에 직접 붙이지 않는다.

4) `pm2 restart`는 런북에 적힌 앱 한 개만. `pm2 restart all`은 하지 않는다.

5) 절차·격벽 SSOT: `docs/final/FINANCIAL_PROPHECY_VPS_LIVE_TRADING_DIRECTIVE_V1.md`, `projects/bitcoin-trading/AGENTS.md`, `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`.

시작할 때: REPO_ROOT를 `pm2 show` 근거와 함께 한 줄로 보고한 뒤 사용자 요청을 수행한다.
```

### 8.2 한 줄 (세션 시작용)

```text
VPS 작업: 먼저 `pm2 show bitcoin-live`로 exec cwd=REPO_ROOT 확정 후, 그 루트에서만 git pull·sync·pm2 restart. 다른 /opt/mkm-* 클론은 본선이 아닐 수 있음. SSOT: docs/final/FINANCIAL_PROPHECY_VPS_LIVE_TRADING_DIRECTIVE_V1.md
```

---

## 9. 금융 히트율 vs 매매 안정권 (우선순위 참고)

이 절은 **운영 판단용 요약**이다. B-track 방향 히트율 등 **오프라인 지표**와 **실전 손실·장애·리스크 한도**는 같은 축이 아니다.

| 층 | 내용 |
|----|------|
| **오프라인 신호** | `eval_prophecy_hit_rate_v1.py` 등으로 측정하는 금융 B-track 히트율·점수 — **연구·가설 품질** 지표로 쓴다. |
| **본선과 맞닿는 층** | Fact-Safe 산출물 → `sync_fact_safe_risk_profile.py` → `risk_profile_fact_safe_latest.json`·통합 거버넌스 브리지(§1·§2). **주문에 B-track을 직접 붙이지 않는다.** |
| **실행·인프라** | PM2 `cwd`·거래소 API(레버리지 등)·본선 트리의 코드 버전 — 여기가 깨지면 히트율을 올려도 **안정권으로 가지 않는다.** |

**우선순위 감각 (충돌 없이 쌓기):** (1) 본선 경로·프로세스·API 오류 없음 → (2) 리스크·거버넌스·Fact-Safe 브리지 → (3) 금융 히트율·월간 체인 품질을 지속 개선.

**레포 근거:** 루트 `AGENTS.md` — B-track 실험 결과를 **승인 없이** 실거래·프로덕션 게이트에 **자동 반영하지 않는다** (직접 브리지 금지와 같은 방향).

**문서 끝.**
