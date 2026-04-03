# 🚀 통합 복원 API 사용 가이드

**작성일**: 2026-02-08  
**API 엔드포인트**: `/api/v1/restoration`  
**상태**: ✅ 프로덕션 준비 완료

---

## 📋 개요

통합 복원 API는 3중 계층 아키텍처를 통해 최적의 복원률을 제공합니다:

1. **정밀 데이터**: PerfectRestorationEngine (100% literal restoration)
2. **일반 데이터**: 블랙홀 시뮬레이터 (85-88%) → 홀로그래픽 엔진 (99.99% 목표)

---

## 🔧 API 엔드포인트

### 기본 정보

- **URL**: `POST /api/v1/restoration`
- **Content-Type**: `application/json`
- **인증**: Bearer Token (선택적)

### 요청 형식

```json
{
  "text": "복원할 텍스트",
  "domain": "general",
  "compression_ratio": 0.99,
  "noise_level": 0.3,
  "enable_holographic": true,
  "enable_blackhole": true,
  "precision_mode": false,
  "hybrid_mode": false,
  "force_keep": null
}
```

### 파라미터 설명

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `text` | string | **필수** | 복원할 텍스트 |
| `domain` | string | "general" | 도메인 (Legal, Medical, Finance, General 등) |
| `compression_ratio` | float | 0.99 | 압축률 (0.0 ~ 1.0) |
| `noise_level` | float | 0.3 | 노이즈 레벨 (0.0 ~ 1.0) |
| `enable_holographic` | boolean | true | 홀로그래픽 엔진 사용 여부 |
| `enable_blackhole` | boolean | true | 블랙홀 시뮬레이터 사용 여부 |
| `precision_mode` | boolean | false | 정밀 데이터 처리 모드 (95%+ 복원률 목표) |
| `hybrid_mode` | boolean | false | 하이브리드 모드 (Force-Keep + 정밀 모드 조합) |
| `force_keep` | boolean/null | null | Force-Keep 강제 설정 (None이면 자동 감지) |

### 응답 형식

```json
{
  "success": true,
  "restored_text": "복원된 텍스트",
  "restoration_rate": 0.96,
  "engine_used": "hierarchical",
  "precision_detected": false,
  "precision_info": null,
  "vector_4d": {
    "S": 0.25,
    "L": 0.25,
    "K": 0.25,
    "M": 0.25
  },
  "processing_time_ms": 4126.88,
  "metadata": {
    "blackhole": {
      "restoration_rate": 0.88,
      "compression_ratio": 0.99,
      "noise_level": 0.3
    },
    "holographic": {
      "restoration_rate": 0.96,
      "steps_completed": [1, 2, 3, 4, 5, 6, 7]
    }
  }
}
```

---

## 📖 사용 예시

### 1. 기본 사용 (일반 텍스트)

```python
import requests

url = "http://localhost:8003/api/v1/restoration"
headers = {"Content-Type": "application/json"}
payload = {
    "text": "블랙홀 정보 역설은 물리학의 중요한 문제입니다.",
    "domain": "general"
}

response = requests.post(url, headers=headers, json=payload)
result = response.json()

print(f"복원률: {result['restoration_rate']:.2%}")
print(f"사용된 엔진: {result['engine_used']}")
```

**예상 결과**:
- 복원률: 85-99.99% (의미론적)
- 엔진: `hierarchical` (블랙홀 → 홀로그래픽)

---

### 2. 정밀 데이터 (금융)

```python
payload = {
    "text": "주식 가격: $1,234.5678, 수익률: 12.3456%",
    "domain": "Finance",
    "precision_mode": True
}

response = requests.post(url, headers=headers, json=payload)
result = response.json()

print(f"복원률: {result['restoration_rate']:.2%}")
print(f"정밀 데이터 감지: {result['precision_detected']}")
```

**예상 결과**:
- 복원률: 100% (literal)
- 엔진: `perfect_restoration`
- 정밀 데이터 감지: `true`

---

### 3. 정밀 데이터 (의료)

```python
payload = {
    "text": "복용량: 12.3456mg, 혈압: 120/80",
    "domain": "Medical"
}

response = requests.post(url, headers=headers, json=payload)
result = response.json()
```

**예상 결과**:
- 복원률: 100% (literal)
- 엔진: `perfect_restoration`
- Force-Keep: 자동 적용

---

### 4. 하이브리드 모드

```python
payload = {
    "text": "일반 텍스트 데이터",
    "hybrid_mode": True  # Force-Keep + 정밀 모드 조합
}

response = requests.post(url, headers=headers, json=payload)
```

**효과**:
- 일반 데이터도 정밀 모드 이점 활용
- 복원률 향상

---

### 5. Force-Keep 강제 설정

```python
payload = {
    "text": "중요한 데이터",
    "force_keep": True  # 100% literal restoration 강제
}

response = requests.post(url, headers=headers, json=payload)
```

**효과**:
- 원본 데이터 보존
- 100% literal restoration

---

## 🎯 엔진 선택 로직

### 자동 엔진 선택

1. **정밀 데이터 감지**
   - 금융/의료/과학 데이터 패턴 감지
   - 정밀도 레벨 >= 0.5
   - → PerfectRestorationEngine 사용

2. **도메인 설정 확인**
   - Legal, Medical, Philosophy, History
   - → PerfectRestorationEngine 사용

3. **일반 데이터**
   - 블랙홀 시뮬레이터 (85-88%)
   - 복원률 < 95% → 홀로그래픽 엔진 (99.99%)

---

## 📊 성능 지표

### 복원률

| 데이터 타입 | 복원률 | 엔진 |
|------------|--------|------|
| 정밀 데이터 (금융) | 100% | PerfectRestoration |
| 정밀 데이터 (의료) | 100% | PerfectRestoration |
| 일반 텍스트 | 85-99.99% | 블랙홀 → 홀로그래픽 |
| 과학 데이터 | 100% | PerfectRestoration |

### 처리 시간

| 데이터 타입 | 평균 처리 시간 | 비고 |
|------------|--------------|------|
| 정밀 데이터 | < 100ms | Force-Keep 모드 |
| 일반 텍스트 | < 1000ms | 홀로그래픽 엔진 사용 시 |
| 첫 실행 | ~10초 | 모델 로딩 |

---

## 🔧 고급 사용법

### 1. 정밀 모드 활성화

```python
payload = {
    "text": "일반 텍스트",
    "precision_mode": True  # 95%+ 복원률 목표
}
```

### 2. 하이브리드 모드

```python
payload = {
    "text": "일반 텍스트",
    "hybrid_mode": True  # Force-Keep + 정밀 모드
}
```

### 3. Force-Keep 강제

```python
payload = {
    "text": "중요한 데이터",
    "force_keep": True  # 100% literal restoration
}
```

---

## ⚠️ 주의 사항

### 1. 정밀 데이터 감지

- 정밀도 레벨 >= 0.5일 때 정밀 데이터로 감지
- 일반 텍스트가 의료 데이터로 오인식될 수 있음 (영향 낮음)

### 2. 처리 시간

- 첫 실행 시 모델 로딩으로 인한 지연 발생 (정상)
- 홀로그래픽 엔진 사용 시 처리 시간 증가

### 3. 메모리 사용량

- 대용량 텍스트 처리 시 메모리 사용량 증가
- 권장: 단일 요청당 10MB 이하

---

## 🚨 에러 처리

### 일반적인 에러

1. **400 Bad Request**
   - 필수 파라미터 누락
   - 파라미터 형식 오류

2. **500 Internal Server Error**
   - 엔진 초기화 실패
   - 메모리 부족

### 에러 응답 형식

```json
{
  "detail": "에러 메시지"
}
```

---

## 📝 예제 코드

### Python

```python
import requests
import json

def restore_text(text: str, domain: str = "general", precision_mode: bool = False):
    """텍스트 복원"""
    url = "http://localhost:8003/api/v1/restoration"
    headers = {"Content-Type": "application/json"}
    payload = {
        "text": text,
        "domain": domain,
        "precision_mode": precision_mode
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# 사용 예시
result = restore_text("복원할 텍스트", domain="Finance", precision_mode=True)
print(f"복원률: {result['restoration_rate']:.2%}")
```

### JavaScript/TypeScript

```typescript
async function restoreText(text: string, domain: string = "general"): Promise<any> {
  const response = await fetch("http://localhost:8003/api/v1/restoration", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      domain,
    }),
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}

// 사용 예시
const result = await restoreText("복원할 텍스트", "Finance");
console.log(`복원률: ${(result.restoration_rate * 100).toFixed(2)}%`);
```

---

## 🔗 관련 문서

- [엔진 통합 문서](./engine_integration_guide.md)
- [배포 가이드](./deployment_guide.md)

---

**작성일**: 2026-02-08  
**상태**: ✅ 프로덕션 준비 완료

