# jema12.com / jemaai.cloud — 도메인·배포 핸드오프 (2026-04-07)

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
