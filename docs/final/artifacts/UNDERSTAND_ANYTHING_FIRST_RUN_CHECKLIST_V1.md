# Understand-Anything First Run Checklist v1

## 목적
- A/B/C 트랙(쇼룸/허브/코퍼스)을 최초 1회 시각화 실행하고 결과를 기준점으로 남긴다.

## 사전 조건
- 리포지토리 클론: `tools/Understand-Anything`
- 의존성 설치: `pnpm install` (완료)
- Cursor 자동 인식: `.cursor-plugin/plugin.json` 확인

## 실행 시나리오

### A) 쇼룸 트랙
- `/understand`
- `/understand-explain projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_board_minimal.html`
- `/understand-explain projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_event_gateway.py`
- `/understand-dashboard`

### B) 허브 트랙
- `/understand`
- `/understand-explain projects/no1kmedi/src/app/page.tsx`
- `/understand-explain projects/no1kmedi/marketing-site/public-copy.json`
- `/understand-domain`

### C) 코퍼스 트랙
- `/understand-knowledge docs/final/artifacts`
- `/understand-explain scripts/check_global_atom_corpus_profile_lock_v1.py`
- `/understand-explain scripts/build_global_atom_corpus_fact_brief_latest_v1.py`
- `/understand-dashboard`

## 완료 기준 (DoD)
- A/B/C 각각 핵심 파일 2개 이상 설명 결과 확보
- CTA 분기(허브)와 코퍼스 profile/anchor/current/delta 연결성 확인
- 결과 캡처/메모를 append-only로 기록

## 기록 필드
- `run_at_utc`:
- `operator`:
- `A_status/B_status/C_status`:
- `key_findings`:
- `follow_up_actions`:
