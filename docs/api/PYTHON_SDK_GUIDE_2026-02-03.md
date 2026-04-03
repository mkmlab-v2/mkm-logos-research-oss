# 🐍 Python SDK 가이드

**버전**: 1.0.0  
**작성일**: 2026-02-03  
**상태**: ✅ 상용화 준비 완료

---

## 📋 목차

1. [설치](#설치)
2. [기본 사용법](#기본-사용법)
3. [고급 사용법](#고급-사용법)
4. [베스트 프랙티스](#베스트-프랙티스)
5. [문제 해결](#문제-해결)

---

## 설치

### 방법 1: pip 설치 (권장)

```bash
pip install -r requirements.txt
```

### 방법 2: 직접 설치

```bash
# 저장소 클론
git clone <repository-url>
cd workspace

# 의존성 설치
pip install fastapi uvicorn websockets
```

---

## 기본 사용법

### 예제 1: 간단한 압축/복원

```python
from tools.core.unified_compression_api import UnifiedCompressionAPI
import asyncio

async def simple_example():
    # API 초기화
    api = UnifiedCompressionAPI()
    
    # 텍스트 압축
    text = "이것은 압축할 텍스트입니다."
    result = await api.compress(text)
    
    # 결과 확인
    print(f"압축률: {result.metrics['compression_ratio']:.2%}")
    print(f"언어: {result.language}")
    
    # 복원
    restored = await api.restore(result.compressed_data, result.residual_patch)
    print(f"복원 정확도: {result.metrics['restoration_accuracy']:.2%}")

asyncio.run(simple_example())
```

### 예제 2: 압축 모드 선택

```python
async def compression_modes():
    api = UnifiedCompressionAPI()
    text = "매우 긴 텍스트..." * 100
    
    # 최고 압축률 모드
    max_result = await api.compress(text, compression_mode="max_compression")
    print(f"최고 압축률: {max_result.metrics['compression_ratio']:.2%}")
    
    # 균형 모드
    hybrid_result = await api.compress(text, compression_mode="hybrid")
    print(f"균형 모드: {hybrid_result.metrics['compression_ratio']:.2%}")
    
    # 완벽 복원 모드
    perfect_result = await api.compress(text, compression_mode="perfect_restoration")
    print(f"완벽 복원: {perfect_result.metrics['compression_ratio']:.2%}")

asyncio.run(compression_modes())
```

---

## 고급 사용법

### 예제 1: 배치 처리

```python
async def batch_compress(texts: list):
    """여러 텍스트를 배치로 압축"""
    api = UnifiedCompressionAPI()
    results = []
    
    for text in texts:
        result = await api.compress(text)
        results.append(result)
    
    return results

# 사용
texts = ["텍스트 1", "텍스트 2", "텍스트 3"]
results = await batch_compress(texts)
```

### 예제 2: 에러 처리

```python
async def safe_compress(text: str):
    """안전한 압축 (에러 처리 포함)"""
    api = UnifiedCompressionAPI()
    
    try:
        result = await api.compress(text)
        return result
    except RuntimeError as e:
        print(f"압축 실패: {e}")
        return None
    except ValueError as e:
        print(f"잘못된 파라미터: {e}")
        return None

# 사용
result = await safe_compress("텍스트")
if result:
    print(f"압축 성공: {result.metrics['compression_ratio']:.2%}")
```

### 예제 3: 메트릭 수집

```python
from tools.core.compression_restoration_metrics_collector import get_metrics_collector

async def compress_with_metrics(text: str):
    """메트릭 수집과 함께 압축"""
    api = UnifiedCompressionAPI()
    collector = get_metrics_collector()
    
    # 압축
    result = await api.compress(text)
    
    # 메트릭 확인
    dashboard_data = collector.get_dashboard_data()
    print(f"전체 성공률: {dashboard_data['summary']['overall_success_rate']:.2%}")
    
    return result

# 사용
result = await compress_with_metrics("텍스트")
```

---

## 베스트 프랙티스

### 1. 압축 모드 선택 가이드

```python
def select_compression_mode(use_case: str) -> str:
    """사용 사례에 따른 압축 모드 선택"""
    mode_map = {
        "llm_api": "max_compression",        # LLM API 호출
        "general": "hybrid",                 # 일반적인 용도
        "legal": "perfect_restoration",      # 법률 문서
        "medical": "perfect_restoration",    # 의료 문서
        "storage": "max_compression"         # 저장 공간 절약
    }
    return mode_map.get(use_case, "hybrid")

# 사용
mode = select_compression_mode("llm_api")
result = await api.compress(text, compression_mode=mode)
```

### 2. 짧은 텍스트 처리

```python
async def smart_compress(text: str, min_length: int = 100):
    """짧은 텍스트는 압축하지 않음"""
    api = UnifiedCompressionAPI()
    
    # 최소 길이 체크
    if len(text.encode('utf-8')) < min_length:
        print("텍스트가 너무 짧아 압축하지 않습니다.")
        return None
    
    return await api.compress(text, min_length=min_length)
```

### 3. 비동기 처리 최적화

```python
import asyncio

async def parallel_compress(texts: list):
    """여러 텍스트를 병렬로 압축"""
    api = UnifiedCompressionAPI()
    
    tasks = [api.compress(text) for text in texts]
    results = await asyncio.gather(*tasks)
    
    return results

# 사용
texts = ["텍스트 1", "텍스트 2", "텍스트 3"]
results = await parallel_compress(texts)
```

---

## 문제 해결

### 문제 1: "사용 가능한 압축 파이프라인이 없습니다"

**원인**: 필요한 파이프라인 모듈이 로드되지 않음

**해결**:
```python
# 의존성 확인
try:
    from tools.core.k_pivot_compression_pipeline import KPivotCompressionPipeline
    print("✅ K-Pivot 파이프라인 사용 가능")
except ImportError:
    print("❌ K-Pivot 파이프라인 로드 실패")

try:
    from tools.core.global_pivot_compression_pipeline import GlobalPivotCompressionPipeline
    print("✅ Global-Pivot 파이프라인 사용 가능")
except ImportError:
    print("❌ Global-Pivot 파이프라인 로드 실패")
```

### 문제 2: 압축률이 낮음

**원인**: 텍스트가 너무 짧거나, 압축 모드가 적절하지 않음

**해결**:
```python
# 텍스트 길이 확인
text_size = len(text.encode('utf-8'))
if text_size < 100:
    print("텍스트가 너무 짧습니다. 최소 100 bytes 이상 필요합니다.")

# 압축 모드 변경
result = await api.compress(text, compression_mode="max_compression")
```

### 문제 3: 복원 정확도가 낮음

**원인**: `max_compression` 모드 사용 시 리터럴 복원 포기

**해결**:
```python
# 완벽 복원 모드 사용
result = await api.compress(text, compression_mode="perfect_restoration")
# 또는 균형 모드
result = await api.compress(text, compression_mode="hybrid")
```

---

## 추가 리소스

- [Unified Compression API 문서](./UNIFIED_COMPRESSION_API_DOCUMENTATION_2026-02-03.md)
- [Dashboard API 문서](./COMPRESSION_RESTORATION_DASHBOARD_API_DOCUMENTATION_2026-02-03.md)
- [상용화 로드맵](../guides/COMMERCIALIZATION_ROADMAP_2026-02-03.md)

---

**작성일**: 2026-02-03  
**버전**: 1.0.0  
**상태**: ✅ 상용화 준비 완료

