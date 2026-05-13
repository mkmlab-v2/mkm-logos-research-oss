# 로컬 PC vs VPS — 단 하나의 표준 (SSOT)

**한 줄:** **코드/전략 동기화는 계속 수행하고, 실전 주문 활성화(ON)는 별도 승인 게이트로 분리한다.**

---

## 왜 번거로워지나

로컬 Cursor와 SSH Cursor **양쪽에서 같은 파일을 직접 수정**하면, 어느 쪽이 진짜인지 매번 맞춰야 해서 피로가 쌓인다. 이 문서는 그걸 **역할 분리**로 끝낸다.

---

## 표준 결론 (이 문서가 단일 SSOT)

아래 2축 분리를 **항상 동시에** 지킨다.

1. **코드/전략 동기화 축**  
   로컬에서 개발한 전략/코드는 VPS 본선 트리에 계속 반영한다.  
   (반영이 멈추면 서버는 구버전 로직으로 동작)
2. **실전 주문 활성화 축**  
   주문 ON/OFF, 포지션 처리, 공격도 조절은 운영 리스크 게이트에서 별도 승인한다.  
   (동기화 성공과 주문 ON은 같은 결정이 아님)

이 문서 외 운영 문서는 **독립 정책을 정의하지 않고**, 이 원칙을 구현하는 절차/체크리스트만 담는다.

---

## 역할 표

| 구분 | 하는 일 | 하지 않는 일 |
|------|---------|----------------|
| **내 PC (로컬)** | 코드·테스트·커밋·`git push` | 서버 전용 비밀을 레포에 올리기 |
| **Git / GitHub** | 진실 한 벌(소스 + `.cursorrules` + `AGENTS.md` 등) | `.env` 같은 비밀 파일 넣기 |
| **VPS (SSH)** | `git pull` + **배포 런북에 적힌** nginx/PM2 등 | Cursor로 레포를 “연구실처럼” 계속 고치기 |
| **`.env`** | 각 기기(로컬·VPS) 금고에만 둔다 | Git에 커밋 |

---

## 비밀 키 (로컬 Windows / Linux VPS) — 권장 고정

**Fact-Lock:** 압축(Track A/B) 파이프라인은 **API 키 암·복호화 계약이 아님** — `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`(Security Agent / API 키 보강)와 혼동 금지.

| 환경 | 권장 저장 | 앱이 값을 읽는 순서(요지) |
|------|-----------|---------------------------|
| **로컬 Windows** | 민감값은 **`scripts/Invoke-EncryptedSecretStore.ps1`** 로 `%APPDATA%\MKM\secret_store_v1.json`(DPAPI)에 `set`; 개발 편의용은 **루트 `.env`(비추적)**. 브리지: `scripts/security_agent_manager.py`. | 스토어 → 환경 변수 → 루트 `.env` → JSON 폴백(CONSTITUTION §1.1.2 요지). |
| **VPS (대개 Linux)** | **DPAPI 스토어에 의존하지 않음.** `/etc/mkm/` 등 **레포 밖** 파일(`chmod 600`) 또는 **systemd `EnvironmentFile=`**, 또는 호스트 시크릿 관리. | **키 이름**은 `.env.example`과 맞추고, **저장 위치만 OS별**로 둔다. |
| **공통** | `.env` **커밋 금지**; 점검: `scripts/Verify-MonorepoSecretHygiene.ps1` — 원클릭 준비도: `scripts/Invoke-MkmSecretsHybridReadiness_v1.ps1`. | 엄격 서베이(선택): `run_workspace_automation_health.ps1 -IncludeSecretExposureSurvey`. |

**VPS env 템플릿(주석만):** `scripts/deploy/linux/mkm-monorepo-vps.env.example` — 채운 뒤 서버 경로에 두고 systemd/PM2가 `EnvironmentFile` 또는 `dotenv` 경로로 읽게 맞춘다.

---

## 단일 운영 표준표 (충돌 방지)

| 구분 | 기본값 | 예외/승인 |
|------|--------|-----------|
| 코드/전략 동기화 | **상시 진행** (`git pull` 기준 본선 반영) | 없음(장애 시 복구 후 재개) |
| 실전 주문 활성화 | **보수 기본값**(필요 시 observe/shadow) | 운영 리스크 승인 시에만 ON |
| PM2 재시작 | 앱 단일 재시작 | `restart all`은 런북 명시 시만 |
| VPS 수정 방식 | 로컬 커밋→푸시→VPS pull | VPS 직접 수정 금지(비상 핫픽스는 즉시 역반영) |
| 경로 기준 | `pm2 show <앱>`의 `exec cwd` | 이름 추측 금지, 실측값 우선 |

---

## 24h 보수 운영 하드라인 (Fact-Lock v1)

아래 임계치는 실전 `LIVE`에서 **즉시 신규주문 차단(cooldown)** 기준이다.  
기본 모드는 `OBSERVE_ONLY`이며, 재개는 승인 게이트를 분리한다.

- 일중 `max_drawdown <= -3.0%`
- 연속 손실 `>= 4회`
- 체결 슬리피지 실측 `> 기대치 2.0배` 5건 연속
- 주문 ACK 지연 `p95 > 1500ms` 10분 지속
- 거래소 요청 실패율 `> 5%` 5분 지속
- 포지션/주문/신호 `state mismatch` 1건 이상
- 주요 렌즈 불일치(가격 엔진 vs 보조 렌즈) 3틱 연속

재개 조건(자동 재개 금지):

- cooldown 최소 30분 경과
- health 지표 15분 연속 정상
- 미체결/유령주문 정리 확인
- 승인 플래그 없으면 `OBSERVE_ONLY` 유지

---

## VPS 배치 (권장): 모노레포 클론 하나

VPS에 **비트코인만 잘린 폴더**만 두지 말고, **모노레포 전체를 한 번 클론**한 뒤 실행은 **`projects/bitcoin-trading`만** 쓴다. `git pull` 한 번에 **래퍼(`start_live_trading.py`)·데몬·`AGENTS.md`**가 같이 따라오고, 레포 밖 단독 나무(`/opt/bitcoin-trading`만)와 **파일 누락·경로 불일치**가 반복되지 않는다.

1. VPS에 모노레포 클론 (이미 있으면 그 경로 사용). **여러 클론이 있으면** 로컬 `scripts/deploy/ship_to_vps.ps1` 기본 `VpsRepoPath`는 **`/opt/mkm-lab-workspace-v2`** 이다. 그래도 **최종 본선은 `pm2 show <앱이름>`의 `exec cwd`(모노레포 루트)** 로 확정한다 — destiny 등 **다른 경로**에서만 `git pull`/`sync` 하면 본선 프로세스와 파일이 어긋난다. Fact-Safe 리스크 JSON 반영 절차: `docs/final/FINANCIAL_PROPHECY_VPS_LIVE_TRADING_DIRECTIVE_V1.md`.
2. 예전 **단독 `/opt/bitcoin-trading` 트리**에만 있던 것 중 레포에 없는 것만 이식: **`config/trading_config.yaml`** 커스텀, **`.env`**(비밀). **모노레포 PM2(`cwd`=레포 루트)** 이면 `projects/bitcoin-trading/scripts/start_24h_daemon.py`가 **우선 `…/workspace/.env`** 를 읽는다(파일이 없을 때만 레거시 `projects/.env`). **단독 클론**으로 `cwd`가 `projects/bitcoin-trading`만이면 그 트리의 `.env`가 우선이다. 팀은 **“어느 `.env`가 진짜인지”**를 한 번 정해 두고, `pm2 show`의 cwd와 항상 같이 검증한다.
3. **PM2:** **`cwd`** = **모노레포 루트**, **`script`** = **`projects/bitcoin-trading/start_live_trading.py`**.
4. 기동 확인 후 옛 단독 트리는 **백업만 남기고 중지**(혼선 방지).

**차선(비추천):** 레포 밖에 디렉터리만 만들고 래퍼 파일만 복사하는 **최소 패치**는 다음 `pull`과 금방 어긋난다.

**한 줄:** 모노레포 클론 1개 + PM2가 **`projects/bitcoin-trading/start_live_trading.py`** 를 가리키게 맞춘다.

**실매매(메인넷 주문)만 추가로:** 사람 승인 후, 루트 `.env`에 **`TESTNET=false`**, **`ENABLE_TRADING=true`** — 미설정이면 `projects/bitcoin-trading/config/trading_config.yaml`의 `testnet` / `enable_live_trading` 기본값을 따른다. 기동 로그는 `start_24h_daemon.py`가 최종 판정에 가깝다. 로컬/VPS에서 비밀 출력 없이 점검: `powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/scripts/preflight_live_trading_readiness.ps1` — PM2 cwd가 **라이브 전용 트리**(예: `/opt/bitcoin-trading-live`)인지 **실측**으로 고정한다(`projects/bitcoin-trading/ops/v2/ssh/VPS_PM2_HEALTH_SSH_CURSOR_RUNBOOK.md`).

---

**bitcoin-trading 본선:** 배치는 위 **「VPS 배치 (권장)」**를 따른다. 모노레포 안에서는 `projects/bitcoin-trading/AGENTS.md`와 같은 디렉터리의 `로컬_VPS_운영원칙.txt`에 **PM2 앱명·`restart all` 금지·`.env` 위치**를 한 장으로 적어 두었다. VPS에만 있던 문단은 **반드시 여기로도 `push`** 해야 “서버만 최신”이 되지 않는다.

## VPS에 SSH로 들어갔을 때 (순서 고정)

1. **레포 루트로 이동** (`cd` 경로는 런북·실측 `pwd` 기준; **여러 클론이면 `pm2 show`의 exec cwd**가 본선).
2. **`git status`** — 예상치 못한 수정이 있으면, 로컬과 맞춘 뒤에만 진행한다.
3. **`git pull`** (또는 팀이 정한 브랜치 동기화 방식). **선택:** 레포 루트에서 `bash scripts/vps_git_worktree_clean.sh --dry-run`으로 미리보기 후, 동일 스크립트(옵션 없음)로 `fetch` + `pull --ff-only` + 알려진 추적 파일 드리프트 복구.
4. **런북대로만** 서비스 재로드 — 예: jema12 본선은 `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md`. mkmlife/no1kmedi는 `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md`와 **절차 혼용 금지**.

> PM2나 앱 이름은 프로젝트마다 다르다. **`pm2 restart all` 같은 일괄 명령은 런북에 있을 때만** 쓴다.

---

## Cursor 규칙은 두 번 설치할 필요 없음

`AGENTS.md`, `.cursor/rules`, `.cursorrules`는 **레포에 있으면** VPS에서 `git pull` 할 때 **같이 내려온다.**  
**User Rules**(Cursor 설정에만 있는 문구)만 각 PC에서 따로 관리된다 — 팀 기준은 **가능하면 레포 규칙으로 옮긴다.**

---

## 마지막 점검 (월 1회면 충분)

- [ ] VPS에서 `git status`가 깨끗한가 (또는 의도된 변경만 있는가).
- [ ] 로컬에서 푸시한 브랜치와 VPS가 같은가.
- [ ] `.env`는 여전히 Git에 안 올라가 있는가.
- [ ] (Windows 로컬) `scripts/Invoke-MkmSecretsHybridReadiness_v1.ps1` exit 0 — DPAPI 스토어는 키가 필요할 때만 `Invoke-EncryptedSecretStore.ps1 -Action set` 으로 채운다.
- [ ] (Linux VPS) 레포 밖 비밀 파일 경로·`EnvironmentFile=` 이 `pm2 show` / 런북과 일치하는가(`scripts/deploy/linux/mkm-monorepo-vps.env.example` 참고).

이 네 가지만 지키면 “로컬 Cursor vs SSH Cursor 맞추기”는 **Git 한 줄**로 줄어든다.
