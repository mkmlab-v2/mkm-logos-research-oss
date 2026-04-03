# 📊 Compression/Restoration Dashboard API 문서

**버전**: 1.0.0  
**작성일**: 2026-02-03  
**상태**: ✅ 상용화 준비 완료

---

## 📋 목차

1. [개요](#개요)
2. [빠른 시작](#빠른-시작)
3. [REST API 엔드포인트](#rest-api-엔드포인트)
4. [WebSocket API](#websocket-api)
5. [응답 형식](#응답-형식)
6. [사용 예제](#사용-예제)

---

## 개요

**Compression/Restoration Dashboard API**는 압축/복원 성능을 실시간으로 모니터링하는 대시보드 API입니다.

### 주요 특징

- ✅ **REST API**: 대시보드 데이터 제공
- ✅ **WebSocket**: 실시간 업데이트 (5초마다)
- ✅ **HTML 대시보드**: 웹 브라우저에서 바로 사용 가능
- ✅ **Chart.js 시각화**: 도메인별 성공률 차트
- ✅ **알림 시스템**: 임계값 기반 알림

---

## 빠른 시작

### 서버 실행

```bash
cd api-services/compression_restoration_dashboard_api
python main.py
```

또는:

```bash
uvicorn main:app --host 0.0.0.0 --port 8005
```

### 대시보드 접속

브라우저에서 `http://localhost:8005` 접속

### API 문서 확인

- Swagger UI: `http://localhost:8005/docs` (자동 생성)
- ReDoc: `http://localhost:8005/redoc` (자동 생성)

---

## REST API 엔드포인트

### `GET /`

대시보드 HTML 페이지를 반환합니다.

**응답**: HTML 페이지

**예제**:
```bash
curl http://localhost:8005/
```

---

### `GET /api/dashboard`

대시보드 데이터를 반환합니다.

**응답**:
```json
{
  "timestamp": "2026-02-03T12:00:00",
  "summary": {
    "total_requests": 1000,
    "total_success": 1000,
    "overall_success_rate": 1.0,
    "avg_restoration_accuracy": 1.0,
    "avg_compression_ratio": 0.95,
    "avg_compression_time_ms": 266.68,
    "avg_restoration_time_ms": 150.0
  },
  "domain_metrics": {
    "general": {
      "domain": "general",
      "total_requests": 100,
      "success_count": 100,
      "success_rate": 1.0,
      "avg_compression_ratio": 0.95,
      "avg_restoration_accuracy": 1.0,
      "avg_compression_time_ms": 266.68,
      "avg_restoration_time_ms": 150.0,
      "error_rate": 0.0
    }
  },
  "alerts": []
}
```

**예제**:
```bash
curl http://localhost:8005/api/dashboard
```

**Python 예제**:
```python
import requests

response = requests.get("http://localhost:8005/api/dashboard")
data = response.json()

print(f"전체 성공률: {data['summary']['overall_success_rate']:.2%}")
print(f"평균 복원 정확도: {data['summary']['avg_restoration_accuracy']:.2%}")
```

---

### `GET /api/metrics/domain/{domain}`

특정 도메인의 메트릭을 반환합니다.

**파라미터**:
- `domain` (path): 도메인 이름 (`general`, `legal`, `medical` 등)

**응답**:
```json
{
  "domain": "general",
  "total_requests": 100,
  "success_count": 100,
  "failure_count": 0,
  "success_rate": 1.0,
  "avg_compression_ratio": 0.95,
  "avg_restoration_accuracy": 1.0,
  "avg_compression_time_ms": 266.68,
  "avg_restoration_time_ms": 150.0,
  "error_rate": 0.0
}
```

**예제**:
```bash
curl http://localhost:8005/api/metrics/domain/general
```

**Python 예제**:
```python
import requests

response = requests.get("http://localhost:8005/api/metrics/domain/general")
metrics = response.json()

print(f"성공률: {metrics['success_rate']:.2%}")
print(f"평균 압축률: {metrics['avg_compression_ratio']:.2%}")
```

---

### `GET /api/metrics/summary`

메트릭 요약을 반환합니다.

**응답**:
```json
{
  "summary": {
    "total_requests": 1000,
    "total_success": 1000,
    "overall_success_rate": 1.0,
    "avg_restoration_accuracy": 1.0,
    "avg_compression_ratio": 0.95,
    "avg_compression_time_ms": 266.68,
    "avg_restoration_time_ms": 150.0
  },
  "domain_count": 9,
  "alert_count": 0
}
```

**예제**:
```bash
curl http://localhost:8005/api/metrics/summary
```

---

### `GET /health`

헬스 체크 엔드포인트입니다.

**응답**:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-03T12:00:00",
  "metrics_collector_available": true
}
```

**예제**:
```bash
curl http://localhost:8005/health
```

---

## WebSocket API

### `WS /ws/dashboard`

실시간 대시보드 업데이트를 위한 WebSocket 연결입니다.

**연결**:
```javascript
const ws = new WebSocket('ws://localhost:8005/ws/dashboard');
```

**메시지 형식**:
- 서버 → 클라이언트: JSON 형식의 대시보드 데이터 (5초마다)
- 클라이언트 → 서버: 없음 (단방향)

**업데이트 주기**: 5초마다 자동 갱신

**예제**:
```javascript
const ws = new WebSocket('ws://localhost:8005/ws/dashboard');

ws.onopen = () => {
    console.log('WebSocket 연결 성공');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('대시보드 데이터:', data);
    
    // UI 업데이트
    updateDashboard(data);
};

ws.onclose = () => {
    console.log('WebSocket 연결 종료');
};

ws.onerror = (error) => {
    console.error('WebSocket 오류:', error);
};
```

**Python 예제**:
```python
import asyncio
import websockets
import json

async def listen_dashboard():
    uri = "ws://localhost:8005/ws/dashboard"
    async with websockets.connect(uri) as websocket:
        while True:
            data = await websocket.recv()
            dashboard_data = json.loads(data)
            print(f"전체 성공률: {dashboard_data['summary']['overall_success_rate']:.2%}")

asyncio.run(listen_dashboard())
```

---

## 응답 형식

### Summary 구조

```python
{
    "total_requests": int,              # 총 요청 수
    "total_success": int,               # 총 성공 수
    "overall_success_rate": float,      # 전체 성공률 (0.0 ~ 1.0)
    "avg_restoration_accuracy": float,  # 평균 복원 정확도 (0.0 ~ 1.0)
    "avg_compression_ratio": float,     # 평균 압축률 (0.0 ~ 1.0)
    "avg_compression_time_ms": float,   # 평균 압축 시간 (ms)
    "avg_restoration_time_ms": float    # 평균 복원 시간 (ms)
}
```

### DomainMetrics 구조

```python
{
    "domain": str,                      # 도메인 이름
    "total_requests": int,              # 총 요청 수
    "success_count": int,               # 성공 수
    "failure_count": int,               # 실패 수
    "success_rate": float,              # 성공률 (0.0 ~ 1.0)
    "avg_compression_ratio": float,     # 평균 압축률
    "avg_restoration_accuracy": float,  # 평균 복원 정확도
    "avg_compression_time_ms": float,   # 평균 압축 시간
    "avg_restoration_time_ms": float,   # 평균 복원 시간
    "error_rate": float                 # 에러율 (0.0 ~ 1.0)
}
```

### Alert 구조

```python
{
    "type": str,        # 알림 타입 ("success_rate", "restoration_accuracy" 등)
    "message": str,     # 알림 메시지
    "severity": str     # 심각도 ("warning", "error")
}
```

---

## 사용 예제

### 예제 1: 대시보드 데이터 수집

```python
import requests
import time
from datetime import datetime

def collect_dashboard_data(interval=60):
    """주기적으로 대시보드 데이터 수집"""
    while True:
        try:
            response = requests.get("http://localhost:8005/api/dashboard")
            data = response.json()
            
            # 데이터 저장 또는 처리
            print(f"[{datetime.now()}] 전체 성공률: {data['summary']['overall_success_rate']:.2%}")
            
            time.sleep(interval)
        except Exception as e:
            print(f"오류 발생: {e}")
            time.sleep(interval)

# 실행
collect_dashboard_data(interval=60)  # 60초마다 수집
```

### 예제 2: 도메인별 성능 모니터링

```python
import requests

def monitor_domain(domain: str):
    """특정 도메인의 성능 모니터링"""
    response = requests.get(f"http://localhost:8005/api/metrics/domain/{domain}")
    metrics = response.json()
    
    print(f"도메인: {domain}")
    print(f"  성공률: {metrics['success_rate']:.2%}")
    print(f"  평균 압축률: {metrics['avg_compression_ratio']:.2%}")
    print(f"  평균 복원 정확도: {metrics['avg_restoration_accuracy']:.2%}")
    print(f"  평균 압축 시간: {metrics['avg_compression_time_ms']:.2f}ms")
    print(f"  에러율: {metrics['error_rate']:.2%}")

# 모든 도메인 모니터링
domains = ["general", "legal", "medical", "finance", "security"]
for domain in domains:
    monitor_domain(domain)
    print()
```

### 예제 3: 실시간 알림 감지

```python
import requests
import time

def check_alerts():
    """알림 확인"""
    response = requests.get("http://localhost:8005/api/dashboard")
    data = response.json()
    
    alerts = data.get("alerts", [])
    if alerts:
        print("⚠️ 알림 발생:")
        for alert in alerts:
            print(f"  [{alert['severity']}] {alert['type']}: {alert['message']}")
    else:
        print("✅ 알림 없음")

# 주기적으로 확인
while True:
    check_alerts()
    time.sleep(30)  # 30초마다 확인
```

---

## 추가 리소스

- [Unified Compression API 문서](./UNIFIED_COMPRESSION_API_DOCUMENTATION_2026-02-03.md)
- [Python SDK 가이드](./PYTHON_SDK_GUIDE_2026-02-03.md)
- [상용화 로드맵](../guides/COMMERCIALIZATION_ROADMAP_2026-02-03.md)

---

**작성일**: 2026-02-03  
**버전**: 1.0.0  
**상태**: ✅ 상용화 준비 완료

