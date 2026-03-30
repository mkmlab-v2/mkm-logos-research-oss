#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 진화 모니터링 대시보드 (Auto Evolution Dashboard)

목적: 자동화 상태 실시간 모니터링
- 자동화 상태 실시간 모니터링
- 파라미터 변경 이력 추적
- 성능 개선 효과 측정

작성일: 2026-01-23
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging

# 프로젝트 루트 경로 추가
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "projects" / "bitcoin-trading"))
sys.path.insert(0, str(WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "src"))

from src.evolution.auto_evolution_engine import AutoEvolutionEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoEvolutionDashboard:
    """
    자동 진화 모니터링 대시보드
    
    핵심 기능:
    - 자동화 상태 실시간 모니터링
    - 파라미터 변경 이력 추적
    - 성능 개선 효과 측정
    """
    
    def __init__(self, evolution_engine: Optional[AutoEvolutionEngine] = None):
        """
        초기화
        
        Args:
            evolution_engine: AutoEvolutionEngine 인스턴스 (선택적)
        """
        self.evolution_engine = evolution_engine or AutoEvolutionEngine()
        self.data_dir = self.evolution_engine.data_dir
    
    def get_automation_status(self) -> Dict[str, Any]:
        """
        자동화 상태 조회
        
        Returns:
            자동화 상태 딕셔너리
        """
        try:
            # 성능 기록 로드
            performance_history = self.evolution_engine.performance_history
            parameter_history = self.evolution_engine.parameter_history
            
            # 최근 성능
            latest_performance = performance_history[-1] if performance_history else None
            
            # 최근 파라미터 변경
            latest_parameter_change = parameter_history[-1] if parameter_history else None
            
            # 자동화 통계
            total_checks = len(performance_history)
            total_adjustments = len(parameter_history)
            
            # 성능 추세
            if len(performance_history) >= 2:
                recent_performances = performance_history[-5:]
                win_rates = [p.get("statistics", {}).get("win_rate", 0.0) for p in recent_performances]
                avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0.0
            else:
                avg_win_rate = 0.0
            
            return {
                "status": "active",
                "total_checks": total_checks,
                "total_adjustments": total_adjustments,
                "latest_performance": latest_performance,
                "latest_parameter_change": latest_parameter_change,
                "average_win_rate": avg_win_rate,
                "automation_enabled": self.evolution_engine.config["evolution"]["enabled"],
                "parameter_adjustment_enabled": self.evolution_engine.config["evolution"]["parameter_adjustment"]["enabled"]
            }
            
        except Exception as e:
            logger.error(f"❌ 자동화 상태 조회 실패: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_parameter_change_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        파라미터 변경 이력 조회
        
        Args:
            limit: 최대 조회 개수
        
        Returns:
            파라미터 변경 이력 리스트
        """
        try:
            history = self.evolution_engine.parameter_history
            return history[-limit:] if len(history) > limit else history
            
        except Exception as e:
            logger.error(f"❌ 파라미터 변경 이력 조회 실패: {e}")
            return []
    
    def get_performance_improvement(self) -> Dict[str, Any]:
        """
        성능 개선 효과 측정
        
        Returns:
            성능 개선 효과 딕셔너리
        """
        try:
            performance_history = self.evolution_engine.performance_history
            
            if len(performance_history) < 2:
                return {
                    "status": "insufficient_data",
                    "message": "성능 데이터가 부족합니다."
                }
            
            # 초기 성능 (처음 5개 평균)
            initial_performances = performance_history[:5] if len(performance_history) >= 5 else performance_history[:len(performance_history)]
            initial_win_rate = sum(
                p.get("statistics", {}).get("win_rate", 0.0)
                for p in initial_performances
            ) / len(initial_performances) if initial_performances else 0.0
            
            initial_sharpe = sum(
                p.get("statistics", {}).get("sharpe_ratio", 0.0)
                for p in initial_performances
            ) / len(initial_performances) if initial_performances else 0.0
            
            # 최근 성능 (마지막 5개 평균)
            recent_performances = performance_history[-5:] if len(performance_history) >= 5 else performance_history[-len(performance_history):]
            recent_win_rate = sum(
                p.get("statistics", {}).get("win_rate", 0.0)
                for p in recent_performances
            ) / len(recent_performances) if recent_performances else 0.0
            
            recent_sharpe = sum(
                p.get("statistics", {}).get("sharpe_ratio", 0.0)
                for p in recent_performances
            ) / len(recent_performances) if recent_performances else 0.0
            
            # 개선 효과
            win_rate_improvement = recent_win_rate - initial_win_rate
            sharpe_improvement = recent_sharpe - initial_sharpe
            
            return {
                "status": "success",
                "initial_performance": {
                    "win_rate": initial_win_rate,
                    "sharpe_ratio": initial_sharpe
                },
                "recent_performance": {
                    "win_rate": recent_win_rate,
                    "sharpe_ratio": recent_sharpe
                },
                "improvement": {
                    "win_rate": win_rate_improvement,
                    "sharpe_ratio": sharpe_improvement
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 성능 개선 효과 측정 실패: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def generate_dashboard_report(self) -> str:
        """
        대시보드 리포트 생성
        
        Returns:
            리포트 문자열
        """
        try:
            status = self.get_automation_status()
            improvement = self.get_performance_improvement()
            parameter_history = self.get_parameter_change_history(limit=5)
            
            report = f"""
================================================================================
📊 자동 진화 모니터링 대시보드
================================================================================
생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔧 자동화 상태:
   - 상태: {status.get('status', 'unknown')}
   - 총 체크 횟수: {status.get('total_checks', 0)}회
   - 총 조정 횟수: {status.get('total_adjustments', 0)}회
   - 자동화 활성화: {status.get('automation_enabled', False)}
   - 파라미터 조정 활성화: {status.get('parameter_adjustment_enabled', False)}

📈 최근 성능:
"""
            
            latest_perf = status.get('latest_performance', {})
            if latest_perf:
                stats = latest_perf.get('statistics', {})
                report += f"""   - 승률: {stats.get('win_rate', 0):.2%}
   - 총 수익률: {stats.get('total_return', 0):.2%}
   - 최대 낙폭: {stats.get('max_drawdown', 0):.2%}
   - Sharpe Ratio: {stats.get('sharpe_ratio', 0):.2f}
"""
            else:
                report += "   - 데이터 없음\n"
            
            if improvement.get('status') == 'success':
                report += f"""
📊 성능 개선 효과:
   - 승률 개선: {improvement.get('improvement', {}).get('win_rate', 0):+.2%}
   - Sharpe Ratio 개선: {improvement.get('improvement', {}).get('sharpe_ratio', 0):+.2f}
"""
            
            if parameter_history:
                report += f"""
📝 최근 파라미터 변경 ({len(parameter_history)}개):
"""
                for change in parameter_history[-3:]:  # 최근 3개만
                    date = change.get('date', 'N/A')
                    adjustments = change.get('adjustments', {})
                    report += f"   - {date}: {adjustments}\n"
            
            report += "================================================================================\n"
            
            return report
            
        except Exception as e:
            logger.error(f"❌ 대시보드 리포트 생성 실패: {e}")
            return f"리포트 생성 실패: {e}"


# === 사용 예시 ===

if __name__ == "__main__":
    # AutoEvolutionDashboard 초기화
    dashboard = AutoEvolutionDashboard()
    
    # 대시보드 리포트 생성
    print(dashboard.generate_dashboard_report())
    
    print("\n✅ 자동 진화 모니터링 대시보드 테스트 완료!")

