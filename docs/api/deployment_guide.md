# 🚀 통합 복원 API 배포 가이드

**작성일**: 2026-02-08  
**목적**: 통합 복원 API 프로덕션 배포  
**상태**: ✅ 배포 준비 완료

---

## 📋 배포 전 준비사항

### 1. 환경 변수 설정

**필수 환경 변수**:
```bash
WORKSPACE_ROOT=C:/workspace
ATHENA_HTTP_PORT=8003
```

**선택적 환경 변수**:
```bash
LOG_LEVEL=INFO
ENABLE_CACHE=true
```

---

### 2. 의존성 설치

```bash
cd C:\workspace
pip install -r requirements.txt
```

**주요 의존성**:
- FastAPI
- uvicorn
- numpy
- pydantic

---

## 🐳 Docker 배포 (권장)

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

CMD ["uvicorn", "mcp-servers.athena_gateway_http:app", "--host", "0.0.0.0", "--port", "8003"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  restoration-api:
    build: .
    ports:
      - "8003:8003"
    environment:
      - WORKSPACE_ROOT=/app
      - ATHENA_HTTP_PORT=8003
    volumes:
      - ./:/app
    restart: unless-stopped
```

### 배포 실행

```bash
docker-compose up -d
```

---

## 🔧 로컬 배포

### 개발 모드

```bash
cd C:\workspace
python -m uvicorn mcp-servers.athena_gateway_http:app --reload --host 0.0.0.0 --port 8003
```

### 프로덕션 모드

```bash
cd C:\workspace
python -m uvicorn mcp-servers.athena_gateway_http:app --host 0.0.0.0 --port 8003 --workers 4
```

---

## 🌐 VPS 배포

### 1. 파일 업로드

```bash
# SSH로 VPS 접속
ssh root@148.230.97.246

# 디렉토리 생성
mkdir -p /opt/restoration-api

# 파일 업로드 (로컬에서)
scp -r mcp-servers/athena_gateway_http.py root@148.230.97.246:/opt/restoration-api/
scp -r tools/ root@148.230.97.246:/opt/restoration-api/
```

### 2. 의존성 설치

```bash
# VPS에서
cd /opt/restoration-api
pip install -r requirements.txt
```

### 3. PM2로 실행

```bash
# PM2 설정 파일 생성
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'restoration-api',
    script: 'python',
    args: '-m uvicorn mcp-servers.athena_gateway_http:app --host 0.0.0.0 --port 8003',
    cwd: '/opt/restoration-api',
    env: {
      WORKSPACE_ROOT: '/opt/restoration-api',
      ATHENA_HTTP_PORT: '8003'
    },
    restart_delay: 30000,
    max_restarts: 20
  }]
}
EOF

# PM2로 시작
pm2 start ecosystem.config.js
pm2 save
```

---

## 📊 배포 확인

### Health Check

```bash
curl http://localhost:8003/health
```

**예상 응답**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### API 문서 확인

```bash
# 브라우저에서
http://localhost:8003/docs
```

---

## 🔐 보안 설정

### 1. API Key 인증 (선택적)

```python
# athena_gateway_http.py에 추가
API_KEY = os.getenv("API_KEY", "your-secret-key")

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path.startswith("/api/v1/restoration"):
        api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
        if api_key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"}
            )
    return await call_next(request)
```

### 2. CORS 설정

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📈 모니터링

### 로그 확인

```bash
# PM2 로그
pm2 logs restoration-api

# 또는 직접 실행 시
tail -f logs/restoration_api.log
```

### 성능 모니터링

```bash
# PM2 모니터링
pm2 monit
```

---

## 🚨 문제 해결

### 포트 충돌

**증상**: `Address already in use`

**해결**:
```bash
# 포트 사용 중인 프로세스 확인
lsof -i :8003  # Linux/Mac
netstat -ano | findstr :8003  # Windows

# 프로세스 종료
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

### 메모리 부족

**증상**: `MemoryError`

**해결**:
1. 워커 수 감소: `--workers 2`
2. 배치 크기 감소
3. 캐싱 활성화

### 엔진 초기화 실패

**증상**: `UnifiedFieldTheoryEngine 초기화 실패`

**해결**:
1. 의존성 재설치
2. 경로 확인
3. 권한 확인

---

## ✅ 배포 체크리스트

### 배포 전

- [ ] 환경 변수 설정 확인
- [ ] 의존성 설치 확인
- [ ] 테스트 실행 확인
- [ ] 로그 디렉토리 생성

### 배포 후

- [ ] Health Check 확인
- [ ] API 문서 접근 확인
- [ ] 샘플 요청 테스트
- [ ] 로그 확인
- [ ] 성능 모니터링

---

## 🔗 관련 문서

- [API 사용 가이드](./restoration_api_guide.md)
- [엔진 통합 문서](./engine_integration_guide.md)

---

**작성일**: 2026-02-08  
**상태**: ✅ 배포 준비 완료

