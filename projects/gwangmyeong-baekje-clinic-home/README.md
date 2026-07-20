# 광명백제한의원 · 얇은 자체 홈 v1

**Status:** `COMMANDER_APPROVED_SCAFFOLD` · `SEND_GATE: HOLD`  
**as_of:** 2026-07-20  
**decision:** `docs/final/artifacts/gwangmyeong_baekje_thin_home_decision_v1_latest.json`

## 범위
- 자체 1페이지 홈 + 네이버 블로그 병행 (`blog.naver.com/gmbaekje`)
- 연락처 SSOT: 송부 영수증 (`02-2688-7700`)
- **한의학 묻다:** 링크 아웃 → `https://jema-ai.com/ask` (새 탭, L0 교육·참고 Q&A) · 레거시 `no1kmedi.com/ask`는 301
- **비범위:** 프로덕션 DNS 배포 · 블로그 URL 이전 · 1215건 이전 · clinic_trust CTA · iframe LLM 임베드

## 한의학 묻다 · 가성비
- 클리닉 홈은 **링크 전용** — LLM API 호출 없음 (비용 0)
- Q&A는 동일 Next 앱 `projects/no1kmedi` `/ask` · Host `jema-ai.com` · `audience: km_national` (`guardian-chat-lane-policy.ts`)
- API는 `maxOutputTokens: 2048` 고정 — 별도 env tier 없음; prod 변경 없이 유지
- 사전 문진 `/intake` (`jema-ai.com/intake`)는 DRAFT 보조 링크 — 예약 연동 HOLD
- Domain migration Phase 1: `docs/final/artifacts/no1kmedi_domain_deprecation_consolidation_proposal_v1.md`

## 로컬 미리보기
```powershell
cd C:\workspace\projects\gwangmyeong-baekje-clinic-home
py -m http.server 18766 --bind 127.0.0.1
```
→ http://127.0.0.1:18766/

## 공개 전
원장 검수 · (필요 시) 한의협 창구에 시안 확인 · `robots` noindex 제거 · 도메인 연결
