#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 10초 선점 전략 벤치마크

목적: 일반 AI 봇 대비 10초 선점 전략의 실제 성능 측정
비교: 일반 AI 봇 (30~60초) vs MKM 엔진 (2~5초)

작성일: 2026-01-11
상태: ✅ 구현 완료
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List
import json
from pathlib import Path

from projects.bitcoin_trading.src.strategy.strike_pipeline_10sec import TenSecondStrikePipeline


class TenSecondBenchmark:
    """
    10초 선점 전략 벤치마크
    
    측정 항목:
    1. 뉴스 수집 시간
    2. 4D 위상 분석 시간
    3. 고전 지혜 필터 시간
    4. 유동성 체크 시간
    5. 고래 추적 시간
    6. 감정 필터 시간
    7. 총 소요 시간
    """
    
    def __init__(self):
        """초기화"""
        self.pipeline = TenSecondStrikePipeline(
            use_classical_wisdom=True,
            use_liquidity_check=True,
            use_whale_tracker=True,
            use_sentiment_filter=True
        )
        
        self.results = []
    
    async def benchmark_single_strike(
        self,
        news_url: str,
        symbol: str = "BTCUSDT",
        order_size_usd: float = 1000.0
    ) -> Dict[str, Any]:
        """
        단일 타격 벤치마크
        
        Args:
            news_url: 뉴스 URL
            symbol: 거래 심볼
            order_size_usd: 주문 크기 (USD)
        
        Returns:
            벤치마크 결과
        """
        total_start = time.time()
        
        result = await self.pipeline.execute_strike(
            news_url=news_url,
            symbol=symbol,
            order_size_usd=order_size_usd
        )
        
        total_latency = (time.time() - total_start) * 1000
        
        benchmark_result = {
            "news_url": news_url,
            "success": result.get("success", False),
            "approved": result.get("approved", False),
            "total_latency_ms": total_latency,
            "stage_latencies": result.get("stage_latencies", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        self.results.append(benchmark_result)
        
        return benchmark_result
    
    async def benchmark_multiple_strikes(
        self,
        news_urls: List[str],
        symbol: str = "BTCUSDT",
        order_size_usd: float = 1000.0
    ) -> Dict[str, Any]:
        """
        다중 타격 벤치마크
        
        Args:
            news_urls: 뉴스 URL 리스트
            symbol: 거래 심볼
            order_size_usd: 주문 크기 (USD)
        
        Returns:
            통합 벤치마크 결과
        """
        print(f"🚀 벤치마크 시작: {len(news_urls)}개 뉴스 URL")
        
        start_time = time.time()
        
        # 병렬 실행 (최대 5개 동시)
        tasks = []
        for url in news_urls:
            task = self.benchmark_single_strike(url, symbol, order_size_usd)
            tasks.append(task)
            
            # 5개씩 배치로 실행
            if len(tasks) >= 5:
                await asyncio.gather(*tasks)
                tasks = []
        
        # 남은 작업 실행
        if tasks:
            await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # 통계 계산
        successful_strikes = [r for r in self.results if r.get("success", False)]
        approved_strikes = [r for r in successful_strikes if r.get("approved", False)]
        
        latencies = [r["total_latency_ms"] for r in successful_strikes]
        
        return {
            "total_urls": len(news_urls),
            "successful_strikes": len(successful_strikes),
            "approved_strikes": len(approved_strikes),
            "rejected_strikes": len(successful_strikes) - len(approved_strikes),
            "total_time_seconds": total_time,
            "average_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
            "min_latency_ms": min(latencies) if latencies else 0.0,
            "max_latency_ms": max(latencies) if latencies else 0.0,
            "median_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0.0,
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0,
            "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0.0,
            "results": self.results
        }
    
    def compare_with_standard_ai(
        self,
        benchmark_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        일반 AI 봇과 비교
        
        일반 AI 봇 가정:
        - 뉴스 수집: 10초 (중개 서버 거침)
        - LLM 분석: 20초 (클라우드 LLM 대기)
        - 매매 신호 생성: 10초
        - 거래소 전송: 5초
        - 총 소요 시간: 45초 (평균)
        
        Returns:
            비교 결과
        """
        mkm_avg_latency = benchmark_result.get("average_latency_ms", 0.0) / 1000.0  # 초 단위
        standard_ai_latency = 45.0  # 초 (일반 AI 봇 평균)
        
        speedup = standard_ai_latency / mkm_avg_latency if mkm_avg_latency > 0 else 0.0
        time_advantage = standard_ai_latency - mkm_avg_latency
        
        return {
            "mkm_avg_latency_seconds": mkm_avg_latency,
            "standard_ai_latency_seconds": standard_ai_latency,
            "speedup": speedup,
            "time_advantage_seconds": time_advantage,
            "time_advantage_percentage": (time_advantage / standard_ai_latency) * 100 if standard_ai_latency > 0 else 0.0
        }
    
    def save_results(self, output_file: str = "benchmark_10sec_results.json"):
        """결과 저장"""
        output_path = Path(__file__).parent.parent.parent.parent / "data" / "benchmarks" / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "benchmark_results": self.results,
                "statistics": self.pipeline.get_statistics()
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 벤치마크 결과 저장: {output_path}")
        return output_path


async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🏛️ 10초 선점 전략 벤치마크")
    print("=" * 80)
    print()
    
    benchmark = TenSecondBenchmark()
    
    # 테스트용 뉴스 URL (실제 뉴스 URL로 교체 필요)
    test_urls = [
        "https://www.coindesk.com/tech/2024/01/01/bitcoin-news-example-1",
        "https://www.coindesk.com/tech/2024/01/01/bitcoin-news-example-2",
        "https://www.coindesk.com/tech/2024/01/01/bitcoin-news-example-3"
    ]
    
    print("📊 벤치마크 실행 중...")
    result = await benchmark.benchmark_multiple_strikes(
        news_urls=test_urls,
        symbol="BTCUSDT",
        order_size_usd=1000.0
    )
    
    print()
    print("=" * 80)
    print("📊 벤치마크 결과")
    print("=" * 80)
    print(f"총 URL: {result['total_urls']}개")
    print(f"성공한 타격: {result['successful_strikes']}개")
    print(f"승인된 타격: {result['approved_strikes']}개")
    print(f"거부된 타격: {result['rejected_strikes']}개")
    print()
    print(f"평균 지연 시간: {result['average_latency_ms']:.1f}ms ({result['average_latency_ms']/1000:.2f}초)")
    print(f"최소 지연 시간: {result['min_latency_ms']:.1f}ms ({result['min_latency_ms']/1000:.2f}초)")
    print(f"최대 지연 시간: {result['max_latency_ms']:.1f}ms ({result['max_latency_ms']/1000:.2f}초)")
    print(f"중간 지연 시간: {result['median_latency_ms']:.1f}ms ({result['median_latency_ms']/1000:.2f}초)")
    print(f"P95 지연 시간: {result['p95_latency_ms']:.1f}ms ({result['p95_latency_ms']/1000:.2f}초)")
    print(f"P99 지연 시간: {result['p99_latency_ms']:.1f}ms ({result['p99_latency_ms']/1000:.2f}초)")
    print()
    
    # 일반 AI 봇과 비교
    comparison = benchmark.compare_with_standard_ai(result)
    print("=" * 80)
    print("⚖️ 일반 AI 봇과 비교")
    print("=" * 80)
    print(f"MKM 엔진 평균: {comparison['mkm_avg_latency_seconds']:.2f}초")
    print(f"일반 AI 봇 평균: {comparison['standard_ai_latency_seconds']:.2f}초")
    print(f"속도 향상: {comparison['speedup']:.1f}배")
    print(f"시간 우위: {comparison['time_advantage_seconds']:.2f}초 ({comparison['time_advantage_percentage']:.1f}%)")
    print()
    
    # 결과 저장
    benchmark.save_results()
    
    print("✅ 벤치마크 완료")


if __name__ == "__main__":
    asyncio.run(main())
