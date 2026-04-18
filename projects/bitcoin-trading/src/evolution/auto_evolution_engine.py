#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자율진화 엔진 (Auto Evolution Engine)

목적: 성능 모니터링 및 자동 파라미터 조정
- 일일 성능 분석
- 파라미터 자동 조정
- 중간 체크 및 알림

작성일: 2026-01-18
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import yaml
import shutil

# 프로젝트 루트 경로 추가
# __file__: projects/bitcoin-trading/src/evolution/auto_evolution_engine.py
# .parent.parent.parent = projects/bitcoin-trading
# .parent.parent.parent.parent = projects
# .parent.parent.parent.parent.parent = workspace root
_current_file = Path(__file__).resolve()
# projects/bitcoin-trading/src/evolution/... -> repo root is five parents up
WORKSPACE_ROOT = _current_file.parents[4]
if not (WORKSPACE_ROOT / "scripts").is_dir():
    _alt = os.getenv("WORKSPACE_ROOT") or os.getenv("MKM_WORKSPACE_ROOT")
    if _alt:
        WORKSPACE_ROOT = Path(_alt).expanduser().resolve()

sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "projects" / "bitcoin-trading"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoEvolutionEngine:
    """
    자율진화 엔진
    
    핵심 기능:
    - 일일 성능 분석
    - 파라미터 자동 조정
    - 중간 체크 및 알림
    """
    
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        config_file: Optional[Path] = None,
        trading_config_path: Optional[Path] = None
    ):
        """
        초기화
        
        Args:
            data_dir: 데이터 디렉토리 경로
            config_file: 설정 파일 경로
            trading_config_path: 거래 설정 파일 경로 (YAML)
        """
        self.data_dir = data_dir or (WORKSPACE_ROOT / "data" / "evolution")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = config_file or (self.data_dir / "evolution_config.json")
        self.load_config()
        
        # 거래 설정 파일 경로 (YAML)
        if trading_config_path:
            self.trading_config_path = Path(trading_config_path)
        else:
            # 기본 경로: projects/bitcoin-trading/config/trading_config.yaml
            # 여러 경로 시도
            possible_paths = [
                WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "config" / "trading_config.yaml",
                _current_file.parent.parent.parent / "config" / "trading_config.yaml",  # projects/bitcoin-trading/config
                Path(__file__).parent.parent.parent.parent / "config" / "trading_config.yaml"  # 직접 계산
            ]
            
            self.trading_config_path = None
            for path in possible_paths:
                if path.exists():
                    self.trading_config_path = path
                    break
            
            if self.trading_config_path is None:
                # 존재하지 않으면 첫 번째 경로 사용 (나중에 생성될 수 있음)
                self.trading_config_path = possible_paths[0]
        
        # 성능 기록
        self.performance_history: List[Dict[str, Any]] = []
        
        # 파라미터 조정 이력
        self.parameter_history: List[Dict[str, Any]] = []
    
    def load_config(self):
        """설정 파일 로드"""
        default_config = {
            "evolution": {
                "enabled": True,
                "check_interval_hours": 6,  # 6시간마다 체크
                "min_trades_for_analysis": 10,  # 최소 거래 횟수
                "performance_threshold": {
                    "min_win_rate": 0.50,  # 최소 승률 50%
                    "min_sharpe_ratio": 1.0,  # 최소 Sharpe Ratio 1.0
                    "max_drawdown": 0.22  # 최대 낙폭 22%
                },
                "parameter_adjustment": {
                    "enabled": True,
                    "adjustment_rate": 0.1,  # 10% 조정
                    "min_confidence": 0.6,  # 최소 신뢰도 60%
                    "max_confidence": 0.8  # 최대 신뢰도 80%
                }
            },
            "monitoring": {
                "enabled": True,
                "alert_on_issues": True,
                "daily_report": True
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"✅ 설정 파일 로드 완료: {self.config_file}")
            except Exception as e:
                logger.warning(f"⚠️ 설정 파일 로드 실패: {e}. 기본 설정 사용.")
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 설정 파일 저장 완료: {self.config_file}")
        except Exception as e:
            logger.error(f"❌ 설정 파일 저장 실패: {e}")
    
    def analyze_daily_performance(
        self,
        trades: List[Dict[str, Any]],
        start_balance: float,
        end_balance: float
    ) -> Dict[str, Any]:
        """
        일일 성능 분석
        
        Args:
            trades: 거래 내역 리스트
            start_balance: 시작 잔고
            end_balance: 종료 잔고
        
        Returns:
            성능 분석 결과
        """
        try:
            if not trades:
                return {
                    "status": "no_trades",
                    "message": "거래 내역이 없습니다."
                }
            
            # 기본 통계
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.get('net_pnl', 0) > 0)
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            
            # 수익률
            total_return = (end_balance - start_balance) / start_balance * 100
            
            # 손익비
            total_profit = sum(t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) > 0)
            total_loss = abs(sum(t.get('net_pnl', 0) for t in trades if t.get('net_pnl', 0) < 0))
            profit_loss_ratio = total_profit / total_loss if total_loss > 0 else 0.0
            
            # 최대 낙폭 (MDD)
            balances = [start_balance]
            for trade in trades:
                balances.append(balances[-1] + trade.get('net_pnl', 0))
            
            if balances:
                peak = balances[0]
                max_drawdown = 0.0
                for balance in balances:
                    if balance > peak:
                        peak = balance
                    drawdown = (peak - balance) / peak if peak > 0 else 0.0
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
            else:
                max_drawdown = 0.0
            
            # Sharpe Ratio (간단화)
            returns = [t.get('net_pnl', 0) / start_balance for t in trades]
            if len(returns) > 1:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0.0
            else:
                sharpe_ratio = 0.0
            
            # 성능 평가
            performance_threshold = self.config["evolution"]["performance_threshold"]
            performance_status = "good"
            issues = []
            
            if win_rate < performance_threshold["min_win_rate"]:
                performance_status = "warning"
                issues.append(f"승률 낮음: {win_rate:.2%} < {performance_threshold['min_win_rate']:.2%}")
            
            if sharpe_ratio < performance_threshold["min_sharpe_ratio"]:
                performance_status = "warning"
                issues.append(f"Sharpe Ratio 낮음: {sharpe_ratio:.2f} < {performance_threshold['min_sharpe_ratio']:.2f}")
            
            if max_drawdown > performance_threshold["max_drawdown"]:
                performance_status = "critical"
                issues.append(f"낙폭 초과: {max_drawdown:.2%} > {performance_threshold['max_drawdown']:.2%}")
            
            result = {
                "date": datetime.now().isoformat(),
                "status": performance_status,
                "statistics": {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": win_rate,
                    "total_return": total_return,
                    "profit_loss_ratio": profit_loss_ratio,
                    "max_drawdown": max_drawdown,
                    "sharpe_ratio": sharpe_ratio,
                    "start_balance": start_balance,
                    "end_balance": end_balance
                },
                "issues": issues,
                "recommendations": self._generate_recommendations(
                    win_rate, sharpe_ratio, max_drawdown, total_trades
                )
            }
            
            # 성능 기록 저장
            self.performance_history.append(result)
            self._save_performance_history()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 일일 성능 분석 실패: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _generate_recommendations(
        self,
        win_rate: float,
        sharpe_ratio: float,
        max_drawdown: float,
        total_trades: int
    ) -> List[str]:
        """권장 사항 생성"""
        recommendations = []
        
        if win_rate < 0.50:
            recommendations.append("승률이 낮습니다. 신호 필터링 강화 권장")
        
        if sharpe_ratio < 1.0:
            recommendations.append("Sharpe Ratio가 낮습니다. 리스크 관리 강화 권장")
        
        if max_drawdown > 0.20:
            recommendations.append("낙폭이 큽니다. 포지션 크기 감소 권장")
        
        if total_trades < 10:
            recommendations.append("거래 횟수가 적습니다. 더 많은 데이터 수집 필요")
        
        if not recommendations:
            recommendations.append("현재 성능이 양호합니다. 현재 설정 유지 권장")
        
        return recommendations
    
    def adjust_parameters(
        self,
        performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        파라미터 자동 조정
        
        Args:
            performance: 성능 분석 결과
        
        Returns:
            조정된 파라미터
        """
        try:
            if not self.config["evolution"]["parameter_adjustment"]["enabled"]:
                return {"status": "disabled", "message": "파라미터 조정이 비활성화되어 있습니다."}
            
            stats = performance.get("statistics", {})
            win_rate = stats.get("win_rate", 0.5)
            sharpe_ratio = stats.get("sharpe_ratio", 1.0)
            max_drawdown = stats.get("max_drawdown", 0.0)
            
            adjustment_rate = self.config["evolution"]["parameter_adjustment"]["adjustment_rate"]
            min_confidence = self.config["evolution"]["parameter_adjustment"]["min_confidence"]
            max_confidence = self.config["evolution"]["parameter_adjustment"]["max_confidence"]
            
            # 현재 파라미터 로드 (전략 설정 파일에서)
            current_params = self._load_current_parameters()
            
            # 조정 로직
            adjustments = {}
            
            # 승률이 낮으면 신뢰도 임계값 상향
            if win_rate < 0.50:
                current_confidence = current_params.get("min_confidence", 0.7)
                new_confidence = min(
                    max_confidence,
                    current_confidence + adjustment_rate
                )
                adjustments["min_confidence"] = new_confidence
                logger.info(f"📊 신뢰도 임계값 상향: {current_confidence:.2%} → {new_confidence:.2%}")
            
            # Sharpe Ratio가 낮으면 리스크 관리 강화
            if sharpe_ratio < 1.0:
                current_position_size = current_params.get("max_position_size", 0.3)
                new_position_size = max(
                    0.1,  # 최소 10%
                    current_position_size - adjustment_rate
                )
                adjustments["max_position_size"] = new_position_size
                logger.info(f"📊 포지션 크기 감소: {current_position_size:.2%} → {new_position_size:.2%}")
            
            # 낙폭이 크면 포지션 크기 추가 감소
            if max_drawdown > 0.20:
                current_position_size = adjustments.get("max_position_size", current_params.get("max_position_size", 0.3))
                new_position_size = max(
                    0.05,  # 최소 5%
                    current_position_size - adjustment_rate * 2
                )
                adjustments["max_position_size"] = new_position_size
                logger.info(f"📊 낙폭 대응: 포지션 크기 감소: {current_position_size:.2%} → {new_position_size:.2%}")
            
            # 조정 사항이 있으면 적용
            if adjustments:
                self._apply_parameter_adjustments(adjustments)
                self.parameter_history.append({
                    "date": datetime.now().isoformat(),
                    "adjustments": adjustments,
                    "reason": performance.get("issues", [])
                })
                self._save_parameter_history()
                
                return {
                    "status": "adjusted",
                    "adjustments": adjustments,
                    "message": "파라미터가 자동 조정되었습니다."
                }
            else:
                return {
                    "status": "no_adjustment",
                    "message": "조정이 필요하지 않습니다."
                }
                
        except Exception as e:
            logger.error(f"❌ 파라미터 조정 실패: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _load_current_parameters(self) -> Dict[str, Any]:
        """
        현재 파라미터 로드 (YAML 설정 파일에서)
        
        Returns:
            현재 파라미터 딕셔너리
        """
        try:
            if not self.trading_config_path.exists():
                logger.warning(f"⚠️ 거래 설정 파일이 없습니다: {self.trading_config_path}. 기본값 사용.")
                return {
                    "min_confidence": 0.6,
                    "max_position_size": 0.3,
                    "signal_threshold": 0.01
                }
            
            with open(self.trading_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 파라미터 추출
            strategy_config = config.get("strategy", {})
            risk_config = config.get("risk_management", {})
            
            params = {
                "min_confidence": strategy_config.get("min_confidence", 0.6),
                "max_position_size": risk_config.get("max_position_size", 0.3),
                "signal_threshold": 0.01,  # 기본값 (설정 파일에 없을 수 있음)
                "max_drawdown": risk_config.get("max_drawdown", 0.22),
                "max_daily_loss": risk_config.get("max_daily_loss", 0.05),
                "stop_loss_ratio": risk_config.get("stop_loss_ratio", 0.02),
                "take_profit_ratio": risk_config.get("take_profit_ratio", 0.04)
            }
            
            logger.info(f"✅ 파라미터 로드 완료: {self.trading_config_path}")
            return params
            
        except Exception as e:
            logger.error(f"❌ 파라미터 로드 실패: {e}. 기본값 사용.")
            return {
                "min_confidence": 0.6,
                "max_position_size": 0.3,
                "signal_threshold": 0.01
            }
    
    def _apply_parameter_adjustments(self, adjustments: Dict[str, Any]):
        """
        파라미터 조정 적용 (YAML 설정 파일에 저장)
        
        Args:
            adjustments: 조정할 파라미터 딕셔너리
        """
        try:
            if not self.trading_config_path.exists():
                logger.error(f"❌ 거래 설정 파일이 없습니다: {self.trading_config_path}")
                return
            
            # 백업 생성
            backup_path = self.trading_config_path.with_suffix('.yaml.backup')
            shutil.copy2(self.trading_config_path, backup_path)
            logger.info(f"📦 설정 파일 백업 생성: {backup_path}")
            
            # 현재 설정 로드
            with open(self.trading_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 파라미터 매핑 (adjustments 키 → YAML 경로)
            param_mapping = {
                "min_confidence": ("strategy", "min_confidence"),
                "max_position_size": ("risk_management", "max_position_size"),
                "max_drawdown": ("risk_management", "max_drawdown"),
                "max_daily_loss": ("risk_management", "max_daily_loss"),
                "stop_loss_ratio": ("risk_management", "stop_loss_ratio"),
                "take_profit_ratio": ("risk_management", "take_profit_ratio")
            }
            
            # 조정 적용
            for param_key, (section, field) in param_mapping.items():
                if param_key in adjustments:
                    if section not in config:
                        config[section] = {}
                    config[section][field] = adjustments[param_key]
                    logger.info(f"📝 {section}.{field} 업데이트: {adjustments[param_key]}")
            
            # 파라미터 검증 및 자동 수정
            validation_errors = self._validate_parameters(config)
            if validation_errors:
                logger.warning(f"⚠️ 파라미터 검증 경고: {validation_errors}")
                # 범위 초과 값 자동 수정
                config = self._fix_parameter_ranges(config)
                logger.info("✅ 파라미터 범위 자동 수정 완료")
            
            # 설정 파일 저장
            with open(self.trading_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            logger.info(f"✅ 파라미터 조정 적용 완료: {self.trading_config_path}")
            logger.info(f"   조정 사항: {adjustments}")
            
        except Exception as e:
            logger.error(f"❌ 파라미터 조정 적용 실패: {e}")
            # 롤백 시도
            if backup_path.exists():
                try:
                    shutil.copy2(backup_path, self.trading_config_path)
                    logger.info(f"🔄 롤백 완료: {backup_path} → {self.trading_config_path}")
                except Exception as rollback_error:
                    logger.error(f"❌ 롤백 실패: {rollback_error}")
            raise
    
    def _validate_parameters(self, config: Dict[str, Any]) -> List[str]:
        """
        파라미터 검증
        
        Args:
            config: 설정 딕셔너리
        
        Returns:
            검증 오류 리스트 (빈 리스트면 검증 통과)
        """
        errors = []
        
        # strategy 검증
        strategy = config.get("strategy", {})
        min_confidence = strategy.get("min_confidence", 0.6)
        if not (0.0 <= min_confidence <= 1.0):
            errors.append(f"min_confidence 범위 오류: {min_confidence} (0.0 ~ 1.0)")
        
        # risk_management 검증
        risk = config.get("risk_management", {})
        max_position_size = risk.get("max_position_size", 0.3)
        if not (0.0 < max_position_size <= 1.0):
            errors.append(f"max_position_size 범위 오류: {max_position_size} (0.0 < x <= 1.0)")
        
        max_drawdown = risk.get("max_drawdown", 0.22)
        if not (0.0 < max_drawdown <= 1.0):
            errors.append(f"max_drawdown 범위 오류: {max_drawdown} (0.0 < x <= 1.0)")
        
        max_daily_loss = risk.get("max_daily_loss", 0.05)
        if not (0.0 < max_daily_loss <= 1.0):
            errors.append(f"max_daily_loss 범위 오류: {max_daily_loss} (0.0 < x <= 1.0)")
        
        return errors
    
    def _fix_parameter_ranges(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        파라미터 범위 자동 수정
        
        Args:
            config: 설정 딕셔너리
        
        Returns:
            수정된 설정 딕셔너리
        """
        # strategy 수정
        if "strategy" not in config:
            config["strategy"] = {}
        
        min_confidence = config["strategy"].get("min_confidence", 0.6)
        if min_confidence < 0.0:
            config["strategy"]["min_confidence"] = 0.0
            logger.info(f"📝 min_confidence 자동 수정: {min_confidence} → 0.0")
        elif min_confidence > 1.0:
            config["strategy"]["min_confidence"] = 1.0
            logger.info(f"📝 min_confidence 자동 수정: {min_confidence} → 1.0")
        
        # risk_management 수정
        if "risk_management" not in config:
            config["risk_management"] = {}
        
        max_position_size = config["risk_management"].get("max_position_size", 0.3)
        if max_position_size <= 0.0:
            config["risk_management"]["max_position_size"] = 0.01
            logger.info(f"📝 max_position_size 자동 수정: {max_position_size} → 0.01")
        elif max_position_size > 1.0:
            config["risk_management"]["max_position_size"] = 1.0
            logger.info(f"📝 max_position_size 자동 수정: {max_position_size} → 1.0")
        
        max_drawdown = config["risk_management"].get("max_drawdown", 0.22)
        if max_drawdown <= 0.0:
            config["risk_management"]["max_drawdown"] = 0.01
            logger.info(f"📝 max_drawdown 자동 수정: {max_drawdown} → 0.01")
        elif max_drawdown > 1.0:
            config["risk_management"]["max_drawdown"] = 1.0
            logger.info(f"📝 max_drawdown 자동 수정: {max_drawdown} → 1.0")
        
        max_daily_loss = config["risk_management"].get("max_daily_loss", 0.05)
        if max_daily_loss <= 0.0:
            config["risk_management"]["max_daily_loss"] = 0.01
            logger.info(f"📝 max_daily_loss 자동 수정: {max_daily_loss} → 0.01")
        elif max_daily_loss > 1.0:
            config["risk_management"]["max_daily_loss"] = 1.0
            logger.info(f"📝 max_daily_loss 자동 수정: {max_daily_loss} → 1.0")
        
        return config
    
    def _save_performance_history(self):
        """성능 기록 저장"""
        try:
            history_file = self.data_dir / "performance_history.json"
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.performance_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 성능 기록 저장 실패: {e}")
    
    def _save_parameter_history(self):
        """파라미터 조정 이력 저장"""
        try:
            history_file = self.data_dir / "parameter_history.json"
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.parameter_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 파라미터 조정 이력 저장 실패: {e}")
    
    def generate_daily_report(self) -> str:
        """일일 리포트 생성"""
        try:
            if not self.performance_history:
                return "성능 기록이 없습니다."
            
            latest = self.performance_history[-1]
            stats = latest.get("statistics", {})
            
            report = f"""
================================================================================
📊 JEMA-12 자율진화 일일 리포트
================================================================================
날짜: {latest.get('date', 'N/A')}
상태: {latest.get('status', 'N/A')}

📈 성능 통계:
   - 총 거래: {stats.get('total_trades', 0)}회
   - 승률: {stats.get('win_rate', 0):.2%}
   - 수익률: {stats.get('total_return', 0):.2%}
   - Sharpe Ratio: {stats.get('sharpe_ratio', 0):.2f}
   - 최대 낙폭: {stats.get('max_drawdown', 0):.2%}

⚠️ 이슈:
{chr(10).join(f'   - {issue}' for issue in latest.get('issues', [])) if latest.get('issues') else '   없음'}

💡 권장 사항:
{chr(10).join(f'   - {rec}' for rec in latest.get('recommendations', []))}
================================================================================
"""
            return report
            
        except Exception as e:
            logger.error(f"❌ 일일 리포트 생성 실패: {e}")
            return f"리포트 생성 실패: {e}"

