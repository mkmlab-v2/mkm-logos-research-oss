# SSH Cursor — jema12.com 본선 배포 런북

**목적**: Cursor에서 **SSH Remote**로 프로덕션 호스트의 워크스페이스를 연 뒤, **같은 레포**로 nginx 스니펫 적용·검증까지 끝내는 절차를 한곳에 고정한다.  
**전제**: 본선에 **이 레포 클론**이 있고, 사용자에게 **sudo(nginx)** 권한이 있다. TLS·DNS는 이미 동작한다고 가정한다.

**관련 문서**: `docs/final/JEMA12_PUBLIC_DOMAIN_AND_DEPLOY_HANDOFF_2026-04-07.md` (도메인 fact-lock, §7 본선 절차, 검증 스냅샷).

---

## 1. 레포 안 핵심 경로 (워크스페이스 루트 = `REPO`)

| 구분 | 경로 |
|------|------|
| nginx 스니펫 원문(주석·대안) | `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/nginx_jema12_com_broadcast_studio.conf.example` |
| 본선 자동 적용 (Linux) | `scripts/deploy/linux/apply_jema12_nginx_snippet.sh` |
| 공개 URL 검증 (Linux) | `scripts/deploy/linux/check_jema12_public_routes.sh` |
| 공개 URL 검증 (Windows, 로컬 점검용) | `scripts/check_jema12_public_routes.ps1` |
| GO 번들 검증 (Windows) | `scripts/verify_war_prolongation_go_bundle.ps1` |
| GO 번들 매니페스트 | `docs/final/artifacts/war_prolongation_go_bundle_manifest_v1.json` |

`apply_jema12_nginx_snippet.sh` 동작 요약:

- `/etc/nginx/snippets/mkm12_jema12_public_routes.conf`에 `location = /studio` (301), `location = /broadcast` (302)를 기록한다.
- 인자로 넘긴 **사이트 파일**(`sites-enabled`의 jema12용)에서 `server_name`에 `jema12`가 있는 줄 **바로 다음**에 `include /etc/nginx/snippets/mkm12_jema12_public_routes.conf;` 한 줄을 삽입한다(이미 있으면 생략).
- `-y`를 붙이면 `nginx -t` 후 `reload`.

---

## 2. SSH Cursor에서 할 일 (순서)

### 2.1 원격 워크스페이스 열기

1. Cursor → **Remote** → **Connect to Host…** → 본선 SSH 호스트 선택(또는 `~/.ssh/config`의 Host).
2. **File → Open Folder** → 서버上的 레포 루트(예: `/opt/jemaai-mono/workspace` 또는 실제 클론 경로). 경로는 지휘관이 쓰는 표준만 쓴다.

### 2.2 최신 코드 받기

원격 터미널에서 레포 루트로 이동한 뒤:

```bash
cd /path/to/workspace   # 실제 REPO 루트
git pull origin main
```

`git`이 없거나 클론이 없으면, 본선에 레포를 한 번 클론한 뒤 이 런북을 따른다.

### 2.3 스크립트 실행 권한 (최초 1회)

```bash
chmod +x scripts/deploy/linux/apply_jema12_nginx_snippet.sh
chmod +x scripts/deploy/linux/check_jema12_public_routes.sh
```

### 2.4 jema12용 nginx 사이트 파일 경로 확인

배포 환경마다 다르다. 예:

```bash
sudo ls -la /etc/nginx/sites-enabled/
# 또는
sudo ls -la /etc/nginx/conf.d/
```

`jema12.com` 또는 `server_name`에 `jema12`가 들어간 파일을 고른다. 아래에서 이 경로를 `SITE`로 부른다.

### 2.5 스니펫 적용 + reload

```bash
cd /path/to/workspace
sudo bash scripts/deploy/linux/apply_jema12_nginx_snippet.sh -y SITE
```

예:

```bash
sudo bash scripts/deploy/linux/apply_jema12_nginx_snippet.sh -y /etc/nginx/sites-enabled/jema12.com
```

- `server_name` 줄에 `jema12`가 없으면 스크립트가 실패하고, 출력되는 `include` 줄을 **수동으로** 해당 `server { }` 안에 넣은 뒤 `sudo nginx -t && sudo systemctl reload nginx`를 실행한다.

### 2.6 검증

```bash
bash scripts/deploy/linux/check_jema12_public_routes.sh
# 또는
BASE_URL=https://www.jema12.com bash scripts/deploy/linux/check_jema12_public_routes.sh
```

기대(스니펫만 적용된 경우):

- `GET /broadcast` → **302** (또는 301)로 공개 쇼룸 쪽으로 이동.
- `GET /studio` → **301** to `/studio/` (스니펫 반영 시).

`/studio/`가 **여전히 500**이면, 스니펫만으로는 부족하고 **기존 `location /studio/`의 `root`/`alias`·파일 존재·권한** 문제다. 본선에서:

```bash
sudo tail -n 80 /var/log/nginx/error.log
```

해당 요청 시각 근처 5~10줄을 근거로 `root`/`alias`를 수정한다. 상세는 핸드오프 문서 §4·§8.

---

## 3. 로컬 Windows에서만 할 일 (선택)

SSH 없이 외부에서 상태만 볼 때:

```powershell
Set-Location C:\workspace
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_jema12_public_routes.ps1
```

---

## 4. 자주 나오는 이슈

| 증상 | 조치 |
|------|------|
| `nginx -t` 실패 | `include` 줄이 `server {}` 밖에 있거나 중복. 백업 파일(`*.bak.*`)과 비교해 수정. |
| `/broadcast` 여전히 404 | reload 미적용, 다른 `server_name` 블록이 응답, 또는 CDN 캐시. `curl -sSI`로 직접 확인. |
| `/studio/` 500 | 스니펫과 별개로 정적 경로 오류 가능성 큼 → `error.log` 필수. |
| NotebookLM `RESOURCE_EXHAUSTED` | 웹 nginx와 무관. `nlm login`, 배치 간격 확대, `run_notebooklm_mega_insight_batch.py`의 `--quota-retry-max` 사용. |

---

## 5. 보안·운영 주의

- 본 문서는 **경로·절차**만 담는다. 비밀번호·토큰·실제 서버 IP는 레포에 적지 않는다.
- `sudo`로 nginx를 바꾸기 전 **백업**은 스크립트가 사이트 파일에 대해 수행한다. 운영 표준이면 스냅샷·변경 기록을 별도 유지한다.
