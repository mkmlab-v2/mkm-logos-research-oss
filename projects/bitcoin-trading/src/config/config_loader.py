#!/usr/bin/env python3
"""
설정 파일 로더

YAML 설정 파일 로드 및 환경 변수 오버라이드 지원
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    설정 파일 로더

    기능:
    - YAML 설정 파일 로드
    - 환경 변수 오버라이드 지원
    - 설정 검증
    """

    def __init__(self, config_file: Optional[Path] = None):
        """
        Args:
            config_file: 설정 파일 경로 (None이면 기본 경로 사용)
        """
        if config_file is None:
            project_root = Path(__file__).parent.parent.parent
            config_file = project_root / "config" / "trading_config.yaml"

        self.config_file = config_file
        self.config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if not self.config_file.exists():
                logger.warning(f"⚠️ 설정 파일 없음: {self.config_file}, 기본값 사용")
                return self._get_default_config()

            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}

            self._apply_env_overrides()
            self._validate_config()

            logger.info(f"✅ 설정 파일 로드 완료: {self.config_file}")
            return self.config

        except Exception as e:
            logger.error(f"❌ 설정 파일 로드 실패: {e}")
            logger.warning("⚠️ 기본값 사용")
            return self._get_default_config()

    def _apply_env_overrides(self):
        """환경 변수 오버라이드 적용"""
        env_mappings = {
            "BTC_SYMBOL": ("symbol", str),
            "BTC_INITIAL_CAPITAL": ("initial_capital", float),
            "BTC_LEVERAGE": ("leverage", int),
            "BTC_TESTNET": ("testnet", lambda x: x.lower() == "true"),
            "BTC_ENABLE_LIVE_TRADING": ("enable_live_trading", lambda x: x.lower() == "true"),
            "BTC_MAX_DRAWDOWN": ("risk_management.max_drawdown", float),
            "BTC_MAX_DAILY_LOSS": ("risk_management.max_daily_loss", float),
            "BTC_CHECK_INTERVAL": ("trading.check_interval_seconds", int),
            "BTC_MAX_TRADES_PER_DAY": ("trading.max_trades_per_day", int),
            "BTC_LOG_LEVEL": ("logging.level", str),
            "BTC_14B_4D_NATIVE_PATH": ("llm_14b.adapter_4d_native_path", str),
            "BTC_14B_INFERENCE_SCRIPT": ("llm_14b.inference_script_path", str),
        }

        for env_key, (config_path, converter) in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value:
                try:
                    value = converter(env_value)
                    self._set_nested_value(self.config, config_path, value)
                    logger.debug(f"✅ 환경 변수 오버라이드: {env_key} = {value}")
                except Exception as e:
                    logger.warning(f"⚠️ 환경 변수 변환 실패: {env_key} = {env_value}, {e}")

    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any):
        keys = path.split(".")
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _validate_config(self):
        required_fields = ["symbol", "initial_capital", "leverage", "testnet", "enable_live_trading"]

        for field in required_fields:
            if field not in self.config:
                logger.warning(f"⚠️ 필수 설정 필드 없음: {field}, 기본값 사용")

        if "risk_management" in self.config:
            rm = self.config["risk_management"]
            if "max_drawdown" in rm and not (0 < rm["max_drawdown"] <= 1):
                logger.warning(f"⚠️ max_drawdown 범위 오류: {rm['max_drawdown']}, 기본값 사용")
                rm["max_drawdown"] = 0.22

            if "max_daily_loss" in rm and not (0 < rm["max_daily_loss"] <= 1):
                logger.warning(f"⚠️ max_daily_loss 범위 오류: {rm['max_daily_loss']}, 기본값 사용")
                rm["max_daily_loss"] = 0.05

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            "symbol": "BTCUSDT",
            "initial_capital": 10000.0,
            "leverage": 2,
            "testnet": True,
            "enable_live_trading": False,
            "risk_management": {
                "max_drawdown": 0.22,
                "max_daily_loss": 0.05,
                "max_position_size": 0.3,
                "stop_loss_ratio": 0.02,
                "take_profit_ratio": 0.04,
            },
            "trading": {
                "check_interval_seconds": 300,
                "max_trades_per_day": 10,
                "price_data_update_interval": 86400,
                "min_price_data_points": 20,
            },
            "strategy": {"use_great_trunk_filter": True, "min_confidence": 0.6},
            "logging": {
                "level": "INFO",
                "enable_json": True,
                "enable_performance_metrics": True,
                "log_rotation_max_bytes": 10485760,
                "log_rotation_backup_count": 5,
            },
            "monitoring": {"enable_monitoring": True, "check_interval": 60},
            "circuit_breaker": {
                "failure_threshold": 5,
                "reset_timeout": 300,
                "half_open_max_calls": 3,
            },
            "retry": {"max_retries": 3, "initial_delay": 1.0, "backoff_factor": 2.0},
            "llm_14b": {
                "enabled": False,
                "adapter_4d_native_path": None,
                "inference_script_path": None,
            },
        }


def load_config(config_file: Optional[Path] = None) -> Dict[str, Any]:
    loader = ConfigLoader(config_file)
    return loader.load()

