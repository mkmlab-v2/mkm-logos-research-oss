## 변경 내용

- 

## 변경 이유

- 

## 검증

- [ ] 로컬 검증 완료 (`npm --prefix ./projects/no1kmedi run check:public-opsec` 해당 시)
- [ ] 공개 표면 금칙어/내부 용어 누출 없음

## 필수 체크 (모두 Green 전 병합 금지)

- [ ] `PR Merge Gate`
- [ ] `no1kmedi-marketing-copy`
- [ ] `no1kmedi-web-build`
- [ ] `no1kmedi Guardian Contract Gate`

## 선택 체크 (운영 정책별)

- [ ] `no1kmedi-api-smoke` (릴리스 정책상 필요 시)

## 리스크 / 롤백

- **리스크:** 
- **롤백:** 병합 후 모니터링/필수 체크 이슈 발생 시 본 PR 리버트
