# jema12.com / jemaai.cloud — 도메인·배포 핸드오프 (2026-04-07)

**SSH Cursor 절차(표준)**: `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md` — 레포 경로 표·`git pull`·`apply_jema12_nginx_snippet.sh`·검증 순서.

**목적**: SSH 본선에서 `broadcast` 404, `studio` 500, GO JSON 동기화 시 혼선을 줄이기 위한 **단일 참조**다. 레포에 `jema12.com` Next 앱 전체가 없으므로 **서버 경로는 플레이스홀더**로 두고, 적용 전 호스트에서 확인한다.

## 1. 도메인 (Fact-lock)

| 이름 | 역할 |
|------|------|
| `https://api.jemaai.cloud` | 공개 API·정적 쇼룸 UI (`/api/public-events/latest`, `public_showroom_poll.html` 등) **권장 SSOT** |
| `jema12.com` | 브랜드 허브; CTA·임베드는 `docs/final/artifacts/jema12_live_portal_cta_snippet.html` 참고 |
| `jema12.cloud` | **DNS/용도가 api와 동일하지 않을 수 있음**. 클라이언트·스크립트는 **`api.jemaai.cloud`로 고정**하고, 별도 호스트명이 필요하면 DNS 확정 후에만 사용한다. |

## 2. GO JSON 3종 (레포 SSOT)

매니페스트: `docs/final/artifacts/war_prolongation_go_bundle_manifest_v1.json`

- `aidc_kpi_gate_war_20260406.json` — `go_no_go.decision`
- `war_prolongation_promotion_ready_latest.json` — 승격 준비 플래그
- `war_prolongation_benchmark_bundle_20260406.json` — 근거 번들

로컬 검증: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_war_prolongation_go_bundle.ps1`

서버로 복사할 때는 동일 상대 경로(`docs/final/artifacts/`)를 유지하거나, 본선 정책 폴더 한 곳으로만 모은 뒤 문서에 경로를 명시한다.

## 3. `/broadcast` 404

**원인 후보**: Next에 `app/broadcast/page.tsx`(또는 페이지) 미배포, 혹은 빌드 산출물에 해당 라우트 없음.

**대응**:

1. 소스에서 라우트 추가 후 재빌드·재배포.
2. 당장 완화: nginx에서 `/broadcast` → 동작 중인 공개 UI로 **302** (예시는 `jemaai-cloud-mvp/nginx_jema12_com_broadcast_studio.conf.example`).

## 4. `/studio/` 500

**원인 후보**: `alias` + `try_files` 조합으로 **리다이렉트 루프** 또는 실제 빌드 경로와 `location` 불일치.

**대응**: `root` + `location /studio/ { try_files ... }` 패턴을 우선 검토 (예시 파일 동일). 배포 경로는 서버의 실제 `out`/`dist`에 맞출 것.

## 5. nginx 스니펫

레포 예시: `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/nginx_jema12_com_broadcast_studio.conf.example`

공개 쇼룸 전체 프록시 참고: 동 디렉터리 `nginx_public_showroom_full.conf.example`.

## 6. 잔여 리스크

- 본선 `risk_profile_mode`가 KPI에 즉시 반영되지 않으면 **데몬 재기동**이 필요할 수 있다. 실거래 호스트에서는 지휘관 승인 후 수행.
- 이 문서는 **외부 URL 가용성을 매 시점 검증하지 않는다**. 배포 후 `curl -sSI`로 확인한다.

## 7. 본선 배포 (A-Track) — 지휘관 승인 후 SSH에서 수행

**전제**: 아래는 **프로덕션 호스트 셸**에서 실행한다. 로컬 워크스페이스(Cursor)는 본선 nginx에 직접 접속하지 않는다.

1. **백업** (경로는 호스트의 실제 `sites-enabled` / `conf.d`에 맞출 것):

```bash
sudo cp -a /etc/nginx/sites-enabled/jema12.com "/etc/nginx/sites-enabled/jema12.com.bak.$(date -u +%Y%m%dT%H%M%SZ)"
```

2. **스니펫 병합**: `nginx_jema12_com_broadcast_studio.conf.example` 내용을 `jema12.com`의 `server { ... }` 블록 안에 붙인다. `/studio/`는 실제 빌드 디렉터리를 확인한 뒤 `root`/`alias` 중 하나로만 고정한다 (§4).

3. **검증·재로드**:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

(systemd가 아니면 `sudo nginx -s reload` 등 호스트 표준에 따른다.)

4. **대중망 스모크**:

```bash
curl -sSI "https://jema12.com/broadcast" | head -n 5
curl -sSI "https://jema12.com/studio/" | head -n 5
```

기대: `/broadcast`는 예시대로라면 **302** 및 `Location:`이 공개 쇼룸 쪽으로 향함. `/studio/`는 **200** 또는 정적 자산 경로에 맞는 응답(호스트 설정에 따름).

5. **GO JSON 이송(선택)**: 레포의 `docs/final/artifacts/` 세 파일을 본선이 읽는 경로로 `scp`/`rsync`한다. 매니페스트는 `war_prolongation_go_bundle_manifest_v1.json`.

6. **데몬 재기동(선택, KPI 미반영 시만)**: 해당 호스트의 트레이딩/옵스 데몬 기동 방식(PM2, systemd, `ensure_daemon_running.ps1`의 **원격 대응 절차**)에 따라 **한 번에** 재기동하고, `latest_kpi.json`·리스크 프로필을 재확인한다.

### 자동화 (레포)

- **공개 URL 점검 (로컬/CI)**: `scripts/check_jema12_public_routes.ps1` (Windows), `scripts/deploy/linux/check_jema12_public_routes.sh` (bash).
- **본선 nginx (스니펫 + include)**: `scripts/deploy/linux/apply_jema12_nginx_snippet.sh` — root로 실행; `/etc/nginx/snippets/mkm12_jema12_public_routes.conf` 작성 후 `sites-enabled`의 `server_name … jema12` 줄 다음에 `include` 한 줄 삽입(가능할 때). 완료 후 `sudo bash … -y /path/to/site` 로 `nginx -t`·reload.

## 8. 공개 URL 확인 스냅샷 (2026-04-07, 외부 `curl` 기준)

| URL | 상태 |
|-----|------|
| `https://jema12.com/` | **200** |
| `https://jema12.com/broadcast` · `.../broadcast/` | **404** |
| `https://jema12.com/studio` | **404** |
| `https://jema12.com/studio/` | **500** |
| `https://www.jema12.com/...` | `/broadcast` **404**, `/studio/` **500** (동일 경향) |

**해석:** 루트는 정상이나 **§7(nginx 병합·reload)이 아직 반영되지 않았거나**, `/broadcast`용 `location`이 없고 `/studio/`는 **설정·경로·upstream 오류**로 500이 나는 상태로 보는 것이 타당하다. `/studio` vs `/studio/`가 다르게 동작하는 것은 **트레일링 슬래시·별도 `location`** 미정리일 때 흔하다 — 예시 스니펫에 리다이렉트 보강 참고.

**500 원인 좁히기 (본선에서 한 번만 실행해 로그 일부 공유 가능):**

```bash
sudo tail -n 80 /var/log/nginx/error.log
# sites별 로그를 쓰는 경우:
# sudo tail -n 80 /var/log/nginx/jema12.com-error.log
```

`rewrite`/`alias`/`proxy_pass` 한 줄과 함께 **해당 요청 시각 근처** 5~10줄이면 원인 특정이 빨라진다.

---

## 9. NotebookLM CLI — `RESOURCE_EXHAUSTED` (별도 이슈)

터미널에 `error code 8: RESOURCE_EXHAUSTED`가 반복되면 **계정·쿼터·프로그래매틱 호출 제한** 가능성이 크다. 대응: `nlm login` 재인증, **호출 간격·배치 크기 축소**, 장시간 루프는 **일시 중지 후 수 시간 뒤 재시도**, 필요 시 다른 Google 프로필. 900초 대기 루프가 계속이면 쿼터 회복 전까지는 **중단**하는 편이 안전하다.
