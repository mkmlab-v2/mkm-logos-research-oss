# 로컬 PC vs VPS — 단 하나의 원칙

**한 줄:** **코드와 규칙은 Git 한 곳에서만 고치고, VPS에서는 “가져오기 + 런북에 적힌 재시작”만 한다.**

---

## 왜 번거로워지나

로컬 Cursor와 SSH Cursor **양쪽에서 같은 파일을 직접 수정**하면, 어느 쪽이 진짜인지 매번 맞춰야 해서 피로가 쌓인다. 이 문서는 그걸 **역할 분리**로 끝낸다.

---

## 역할 표

| 구분 | 하는 일 | 하지 않는 일 |
|------|---------|----------------|
| **내 PC (로컬)** | 코드·테스트·커밋·`git push` | 서버 전용 비밀을 레포에 올리기 |
| **Git / GitHub** | 진실 한 벌(소스 + `.cursorrules` + `AGENTS.md` 등) | `.env` 같은 비밀 파일 넣기 |
| **VPS (SSH)** | `git pull` + **배포 런북에 적힌** nginx/PM2 등 | Cursor로 레포를 “연구실처럼” 계속 고치기 |
| **`.env`** | 각 기기(로컬·VPS) 금고에만 둔다 | Git에 커밋 |

---

## VPS 배치 (권장): 모노레포 클론 하나

VPS에 **비트코인만 잘린 폴더**만 두지 말고, **모노레포 전체를 한 번 클론**한 뒤 실행은 **`projects/bitcoin-trading`만** 쓴다. `git pull` 한 번에 **래퍼(`start_live_trading.py`)·데몬·`AGENTS.md`**가 같이 따라오고, 레포 밖 단독 나무(`/opt/bitcoin-trading`만)와 **파일 누락·경로 불일치**가 반복되지 않는다.

1. VPS에 모노레포 클론 (이미 있으면 그 경로 사용; 예: `/opt/mkm-destiny-ai` — **실측 `pwd`·런북**이 우선).
2. 예전 **단독 `/opt/bitcoin-trading` 트리**에만 있던 것 중 레포에 없는 것만 이식: **`config/trading_config.yaml`** 커스텀, **`.env`**(비밀) — 클론 루트 또는 `projects/bitcoin-trading/` **한 곳**만 팀 규칙으로 고정.
3. **PM2:** **`cwd`** = **모노레포 루트**, **`script`** = **`projects/bitcoin-trading/start_live_trading.py`**.
4. 기동 확인 후 옛 단독 트리는 **백업만 남기고 중지**(혼선 방지).

**차선(비추천):** 레포 밖에 디렉터리만 만들고 래퍼 파일만 복사하는 **최소 패치**는 다음 `pull`과 금방 어긋난다.

**한 줄:** 모노레포 클론 1개 + PM2가 **`projects/bitcoin-trading/start_live_trading.py`** 를 가리키게 맞춘다.

---

**bitcoin-trading 본선:** 배치는 위 **「VPS 배치 (권장)」**를 따른다. 모노레포 안에서는 `projects/bitcoin-trading/AGENTS.md`와 같은 디렉터리의 `로컬_VPS_운영원칙.txt`에 **PM2 앱명·`restart all` 금지·`.env` 위치**를 한 장으로 적어 두었다. VPS에만 있던 문단은 **반드시 여기로도 `push`** 해야 “서버만 최신”이 되지 않는다.

## VPS에 SSH로 들어갔을 때 (순서 고정)

1. **레포 루트로 이동** (`cd` 경로는 런북·실측 `pwd` 기준).
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

이 네 가지만 지키면 “로컬 Cursor vs SSH Cursor 맞추기”는 **Git 한 줄**로 줄어든다.
