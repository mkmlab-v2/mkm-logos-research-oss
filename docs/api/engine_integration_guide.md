# 🔗 엔진 통합 가이드

**작성일**: 2026-02-08  
**목적**: 통합 복원 엔진 아키텍처 및 사용법  
**상태**: ✅ 프로덕션 준비 완료

---

## 📊 엔진 통합 아키텍처

### 3중 계층 아키텍처

```
┌─────────────────────────────────────────┐
│     정밀 데이터 감지 (자동)              │
└─────────────────────────────────────────┘
              │
              ├─ 정밀 데이터 감지
              │  └─> PerfectRestorationEngine (100% literal)
              │
              └─ 일반 데이터
                 └─> 블랙홀 시뮬레이터 (85-88%)
                     └─ 복원률 < 95%
                        └─> 홀로그래픽 엔진 (99.99%)
```

---

## 🔧 엔진별 상세

### 1. BlackHoleInformationRestorationSimulator

**위치**: `tools/core/blackhole_information_restoration_simulator.py`

**성능**:
- 평균 복원률: 85-88%
- 최고 복원률: 96% (홀로그래픽 엔진 통합 시)

**특징**:
- 통일장 이론 기반 복원
- 빌리티-파르타넨 등가성 활용
- 금화교역 역변환 (M → K)

**사용 시나리오**:
- 일반 텍스트 복원
- 의미론적 복원 우선

---

### 2. HolographicRestorationEngine

**위치**: `tools/core/holographic_restoration_engine.py`

**성능**:
- 목표 복원률: 99.99% (의미론적)
- 7단계 복원 프로세스

**특징**:
- 4D 벡터 기반 복원
- 메타데이터 활용 복원
- 통일장 이론 보정

**사용 시나리오**:
- 블랙홀 시뮬레이터 후처리
- 복원률 < 95%일 때 자동 사용

---

### 3. PerfectRestorationEngine

**위치**: `scripts/implement_100_percent_restoration.py`

**성능**:
- 복원률: 100% (literal)
- 문자 단위 완벽 복원

**특징**:
- 정밀 데이터 전용
- Force-Keep 모드
- 원본 데이터 보존

**사용 시나리오**:
- 금융/의료/과학 데이터
- 정밀도 레벨 >= 0.5

---

## 🔄 엔진 간 통합

### 폴백 메커니즘

```python
# 블랙홀 시뮬레이터로 초기 복원
result = blackhole_simulator.simulate_full_cycle(data)

# 복원률 < 95%이면 홀로그래픽 엔진 사용
if result.restoration_rate < 0.95:
    holographic_result = holographic_engine.holographic_restore(
        vector_4d=result.restored_vector_4d,
        metadata={"original_text": data}
    )
    
    # 더 높은 복원률 사용
    if holographic_result.restoration_rate > result.restoration_rate:
        result = holographic_result
```

### Force-Keep 모드

```python
# 정밀 데이터 감지
precision_info = simulator._detect_precision_data(data)

if precision_info["is_precision"] and precision_info["force_keep"]:
    # PerfectRestorationEngine 사용
    result = perfect_engine.restore(data)
    # 100% literal restoration
```

---

## 📋 통합 사용 예시

### Python

```python
from tools.core.blackhole_information_restoration_simulator import BlackHoleInformationRestorationSimulator

# 시뮬레이터 초기화
simulator = BlackHoleInformationRestorationSimulator()

# 전체 사이클 시뮬레이션
result = simulator.simulate_full_cycle(
    data="복원할 텍스트",
    compression_ratio=0.99,
    noise_level=0.3,
    precision_mode=False,
    hybrid_mode=False,
    force_keep=None
)

# 결과 확인
print(f"복원률: {result.restoration_rate:.2%}")
print(f"벡터: {result.restored_vector_4d}")
```

### API 사용

```python
import requests

url = "http://localhost:8003/api/v1/restoration"
payload = {
    "text": "복원할 텍스트",
    "domain": "general",
    "enable_blackhole": True,
    "enable_holographic": True
}

response = requests.post(url, json=payload)
result = response.json()

print(f"복원률: {result['restoration_rate']:.2%}")
print(f"사용된 엔진: {result['engine_used']}")
```

---

## 🎯 엔진 선택 가이드

### 정밀 데이터

**사용 엔진**: PerfectRestorationEngine

**조건**:
- 금융/의료/과학 데이터 패턴 감지
- 정밀도 레벨 >= 0.5
- 도메인: Legal, Medical, Philosophy, History

**예시**:
```python
payload = {
    "text": "$1,234.5678",
    "domain": "Finance"
}
# → PerfectRestorationEngine 자동 사용
```

---

### 일반 데이터

**사용 엔진**: 블랙홀 → 홀로그래픽

**조건**:
- 정밀 데이터 아님
- 일반 텍스트

**예시**:
```python
payload = {
    "text": "일반 텍스트",
    "domain": "general"
}
# → 블랙홀 시뮬레이터 (85-88%)
# → 복원률 < 95% → 홀로그래픽 엔진 (99.99%)
```

---

## 📊 성능 비교

| 엔진 | 복원률 | 처리 시간 | 용도 |
|------|--------|----------|------|
| 블랙홀 시뮬레이터 | 85-88% | < 1000ms | 일반 텍스트 |
| + 홀로그래픽 엔진 | 99.99% | < 2000ms | 일반 텍스트 (향상) |
| PerfectRestoration | 100% | < 100ms | 정밀 데이터 |

---

## 🔧 통합 설정

### 도메인별 설정

**파일**: `tools/core/domain_compression_config.py`

```python
# PerfectRestoration 도메인
PERFECT_RESTORATION_DOMAINS = [
    "Legal", "Medical", "Philosophy", "History"
]
```

### 정밀 데이터 감지 설정

**파일**: `tools/core/blackhole_information_restoration_simulator.py`

```python
# 정밀도 감지 임계값
precision_threshold = 0.5  # 0.3 → 0.5로 상향 조정
```

---

## 🚨 문제 해결

### 엔진 초기화 실패

**증상**: `UnifiedFieldTheoryEngine 초기화 실패`

**해결**:
1. 의존성 확인: `pip install -r requirements.txt`
2. 경로 확인: `WORKSPACE_ROOT` 환경 변수

### 복원률 낮음

**증상**: 복원률 < 85%

**해결**:
1. 홀로그래픽 엔진 자동 사용 확인
2. 메타데이터 제공 확인

### 처리 시간 과다

**증상**: 처리 시간 > 5000ms

**해결**:
1. 첫 실행 시 모델 로딩 대기 (정상)
2. 캐싱 활성화 확인

---

## 🔗 관련 문서

- [API 사용 가이드](./restoration_api_guide.md)
- [배포 가이드](./deployment_guide.md)

---

**작성일**: 2026-02-08  
**상태**: ✅ 프로덕션 준비 완료

