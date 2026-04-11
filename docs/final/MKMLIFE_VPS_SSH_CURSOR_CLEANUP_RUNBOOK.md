# mkmlife.com VPS · SSH Cursor 정리 런북

**목적:** Hostinger VPS에서 `mkmlife` 본선 트리를 **Git 한 곳**으로 정렬하고, **Windows 공유 드라이브(G: 등)·아티팩트 폴더를 배포 소스로 오인**하지 않게 한다.

**SSOT:** `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` (§3 PM2 `exec cwd`, §9.2 stash)

**원칙 (공유 폴더)**

- `G:\공유 드라이브\MKM_DATA_VAULT\...` 및 로컬 `vault` 동기화 경로는 **B-track 아티팩트·백업·검증용**이다.
- **VPS 본선 앱 소스는 항상 `pm2 describe mkmlife`의 `exec cwd` 아래 Git 트리**다. 공유 폴더에서 직접 복사해 덮어쓰는 방식으로 본선을 맞추지 않는다(드리프트·재현 불가).

---

## 1) SSH Cursor에게 그대로 붙여 넣을 명령 블록 (읽기 전용 점검)

아래는 **배포/풀 없이** 상태만 기록한다. 먼저 실행해 스크린샷 또는 로그로 남긴다.

```bash
# 0) 어디에 붙었는지
hostname
date -u
whoami
pwd

# 1) 본선 PM2 실측 (SSOT 고정값과 문자열 비교만, 추측 금지)
pm2 describe mkmlife | sed -n '1,120p'

# 2) exec cwd로 이동 가능한지 확인 후 Git 식별
MKMLIFE_ROOT="$(pm2 describe mkmlife 2>/dev/null | awk -F': ' '/exec cwd/{print $2; exit}')"
echo "MKMLIFE_ROOT=${MKMLIFE_ROOT}"
test -n "$MKMLIFE_ROOT" && cd "$MKMLIFE_ROOT" || { echo "ERROR: cannot resolve exec cwd"; exit 1; }
pwd
git rev-parse --is-inside-work-tree
git remote -v
git status -sb
git rev-parse HEAD
git rev-parse origin/main 2>/dev/null || true
```

**판정:** `exec cwd`가 `/var/www/mkmlife_runtime/mkm-life` 등 **단일 Git 루트**이고, `git status`가 깨끗하거나(stash 가능한 로컬 변경만) 의도된 상태면 1차 OK.

---

## 2) Git 정렬(풀) — 스크립트 사용 (권장)

모노레포에 있는 스크립트를 **VPS 본선 루트에 복사해 두었거나**, `curl`로 가져온 최신본을 쓴다. 원본은 항상:

`scripts/mkmlife_vps_git_align_safe.sh` (저장소 `mkmlab-v2/mkm-destiny-ai-41e38ec6`)

**VPS에서 (본선 루트 = `exec cwd`):**

```bash
cd /var/www/mkmlife_runtime/mkm-life   # pm2 describe 실측값으로 맞출 것
export MKMLIFE_GIT_ALIGN_DRY_RUN=1
bash ./scripts/mkmlife_vps_git_align_safe.sh .
# 출력 확인 후 실제 실행:
unset MKMLIFE_GIT_ALIGN_DRY_RUN
bash ./scripts/mkmlife_vps_git_align_safe.sh .
```

스크립트는 **stash(-u) → `git pull --ff-only`** 만 수행한다. `reset --hard` / `clean -fd`는 없다. stash 목록은 `git stash list`로 확인 후 필요 시 `pop`은 **지휘관 판단**.

**원격:** 본선은 `mkmlab-hq/mkmlife-com`과 동일 원격이어야 한다. `git remote -v`가 다르면 **먼저 원격 확정 후** 정렬한다.

---

## 3) 보조 클론·중복 트리 (정리 시 주의)

SSOT §3.1에 따라, `/opt/mkm-sync-check` 등 **참고용 클론**이 있으면 본선 SHA와 다를 수 있다. **삭제는 “그 경로가 무엇에 쓰이는지” 확인 후**만. 불필요하면 SSOT의 절차대로 `pm2 describe`로 본선이 해당 경로가 아님을 확인한 뒤 제거.

---

## 4) 배포 후 최소 검증

```bash
pm2 describe mkmlife | grep -E 'exec cwd|status'
# pm2 restart는 ecosystem·runbook에 맞게만 (restart all 금지 — bitcoin-trading 운영 원칙과 동일 주의)
```

HTTP는 호스트·환경에 맞게 `curl -sS -o /dev/null -w '%{http_code}' https://mkmlife.com/` 등으로 확인.

---

## 5) 로컬(Windows)과의 역할 분리

| 위치 | 역할 |
|------|------|
| `C:\workspace\projects\mkm\mkm-life` | 서브모듈 — **편집·커밋·푸시** (`mkmlife-com` 원격) |
| `G:\...\MKM_DATA_VAULT\...` | 아티팩트·검증 번들 — **본선 소스 SSOT 아님** |
| VPS `exec cwd` | **실행 중 빌드·PM2** — `git pull`은 위 2절 |

**정리:** “공유 폴더에서 많이 작업했다”는 내용은 **아티팩트·연구**로 두고, **mkmlife.com 라이브 코드**는 **GitHub `mkmlife-com` → VPS pull** 한 줄로만 맞춘다.
