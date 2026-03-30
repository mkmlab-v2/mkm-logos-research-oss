#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 GPU 훈련 모델 예측기

GPU 훈련된 PMI-Nitro Signal Predictor 모델을 로드하고 예측 수행
"""

import sys
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "scripts" / "gpu_training"))

# Logger 초기화 (import 전에)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Phase 1 모델 import
MODEL_AVAILABLE = False
PMINitroSignalPredictor = None
try:
    # 경로 1: scripts/gpu_training/models
    sys.path.insert(0, str(workspace_root / "scripts" / "gpu_training" / "models"))
    from pmi_nitro_signal_predictor import PMINitroSignalPredictor
    MODEL_AVAILABLE = True
except ImportError:
    try:
        # 경로 2: 상대 경로
        from scripts.gpu_training.models.pmi_nitro_signal_predictor import PMINitroSignalPredictor
        MODEL_AVAILABLE = True
    except ImportError:
        try:
            # 경로 3: 직접 경로
            import importlib.util
            model_path = workspace_root / "scripts" / "gpu_training" / "models" / "pmi_nitro_signal_predictor.py"
            if model_path.exists():
                spec = importlib.util.spec_from_file_location("pmi_nitro_signal_predictor", model_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                PMINitroSignalPredictor = module.PMINitroSignalPredictor
                MODEL_AVAILABLE = True
            else:
                MODEL_AVAILABLE = False
        except Exception as e:
            MODEL_AVAILABLE = False
            logger.warning(f"⚠️ Phase 1 모델 import 실패: {e}")

if not MODEL_AVAILABLE:
    PMINitroSignalPredictor = None
    logger.warning("⚠️ Phase 1 모델을 import할 수 없습니다.")

# 특징 추출기 import
PMIFeatureExtractor = None
try:
    # 경로 1: scripts/gpu_training/data
    sys.path.insert(0, str(workspace_root / "scripts" / "gpu_training" / "data"))
    from feature_extractor import PMIFeatureExtractor
except ImportError:
    try:
        # 경로 2: 상대 경로
        from scripts.gpu_training.data.feature_extractor import PMIFeatureExtractor
    except ImportError:
        try:
            # 경로 3: 직접 경로
            import importlib.util
            extractor_path = workspace_root / "scripts" / "gpu_training" / "data" / "feature_extractor.py"
            if extractor_path.exists():
                spec = importlib.util.spec_from_file_location("feature_extractor", extractor_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                PMIFeatureExtractor = module.PMIFeatureExtractor
            else:
                PMIFeatureExtractor = None
        except Exception as e:
            PMIFeatureExtractor = None
            logger.warning(f"⚠️ 특징 추출기 import 실패: {e}")

if PMIFeatureExtractor is None:
    logger.warning("⚠️ 특징 추출기를 import할 수 없습니다.")

logger = logging.getLogger(__name__)


class Phase1ModelPredictor:
    """
    Phase 1 GPU 훈련 모델 예측기
    
    기능:
    - 모델 로드 (best_model.pt)
    - 입력 데이터 전처리 (15개 특징, 60개 시퀀스)
    - 신호 예측 (BUY/SELL/HOLD + confidence)
    """
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        device: Optional[torch.device] = None,
        seq_len: int = 60,
        input_features: int = 15
    ):
        """
        Args:
            model_path: 모델 파일 경로 (None이면 기본 경로 사용)
            device: GPU 장치 (None이면 자동 감지)
            seq_len: 시퀀스 길이 (기본값: 60)
            input_features: 입력 특징 수 (기본값: 15)
        """
        self.seq_len = seq_len
        self.input_features = input_features
        
        # GPU 장치 설정
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = device
        
        # 모델 경로 설정
        if model_path is None:
            # 경로 1: scripts/gpu_training/models/phase1_pmi_nitro/best_model.pt
            default_path = workspace_root / "scripts" / "gpu_training" / "models" / "phase1_pmi_nitro" / "best_model.pt"
            if default_path.exists():
                model_path = default_path
            else:
                # 경로 2: final_model.pt 시도
                final_path = workspace_root / "scripts" / "gpu_training" / "models" / "phase1_pmi_nitro" / "final_model.pt"
                if final_path.exists():
                    model_path = final_path
                else:
                    # 경로 3: 상대 경로 시도
                    alt_path = Path(__file__).parent.parent.parent / "scripts" / "gpu_training" / "models" / "phase1_pmi_nitro" / "best_model.pt"
                    if alt_path.exists():
                        model_path = alt_path
                    else:
                        model_path = None
        
        self.model_path = model_path
        self.model = None
        self.model_loaded = False
        
        # 특징 추출기
        if PMIFeatureExtractor is not None:
            self.feature_extractor = PMIFeatureExtractor()
        else:
            self.feature_extractor = None
            logger.warning("⚠️ 특징 추출기 없음, 모델 사용 불가")
        
        # 모델 로드
        if MODEL_AVAILABLE and model_path and model_path.exists():
            try:
                self._load_model()
            except Exception as e:
                logger.error(f"❌ 모델 로드 실패: {e}")
                self.model_loaded = False
        else:
            logger.warning(f"⚠️ 모델 파일 없음: {model_path}")
            self.model_loaded = False
    
    def _load_model(self):
        """모델 로드"""
        if not MODEL_AVAILABLE:
            logger.error("❌ 모델 클래스 사용 불가")
            return
        
        try:
            # 모델 초기화 (훈련 시와 동일한 구조)
            self.model = PMINitroSignalPredictor(
                input_features=self.input_features,
                seq_len=self.seq_len,
                d_model=256,
                nhead=8,
                num_layers=8,
                dropout=0.1,
                use_harmonic=True
            ).to(self.device)
            
            # 가중치 로드
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # 체크포인트 형식 확인
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            elif isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['state_dict'])
            else:
                # 직접 state_dict인 경우
                self.model.load_state_dict(checkpoint)
            
            self.model.eval()  # 평가 모드
            self.model_loaded = True
            logger.info(f"✅ Phase 1 모델 로드 완료: {self.model_path}")
            
        except Exception as e:
            logger.error(f"❌ 모델 로드 실패: {e}")
            self.model_loaded = False
            raise
    
    def _prepare_sequence(
        self,
        price_data: pd.DataFrame,
        current_time: datetime
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        입력 시퀀스 준비
        
        Args:
            price_data: OHLCV 데이터프레임
            current_time: 현재 시간
        
        Returns:
            (features_seq, day_indices)
            - features_seq: (seq_len, input_features) 특징 시퀀스
            - day_indices: (seq_len,) 일자 인덱스
        """
        if self.feature_extractor is None:
            raise ValueError("특징 추출기 없음")
        
        # 최소 데이터 요구사항 확인
        if len(price_data) < self.seq_len:
            raise ValueError(f"데이터 부족: {len(price_data)} < {seq_len}")
        
        # 최근 seq_len개 데이터 사용
        recent_data = price_data.iloc[-self.seq_len:].copy()
        
        # 시작일 계산 (하모닉 주기용)
        start_date = recent_data.index[0]
        base_date = datetime(2020, 1, 1)  # 기준일 (훈련 시와 동일)
        days_since_base = (start_date - base_date).days if isinstance(start_date, datetime) else 0
        
        # 특징 시퀀스 생성
        features_list = []
        day_indices_list = []
        
        for i in range(self.seq_len):
            # 각 시점의 데이터
            window_data = recent_data.iloc[:i+1] if i < len(recent_data) else recent_data
            
            # 일자 인덱스 계산
            current_date = recent_data.index[i] if i < len(recent_data) else recent_data.index[-1]
            if isinstance(current_date, datetime):
                day_index = (current_date - base_date).days
            else:
                day_index = days_since_base + i
            
            # 특징 추출
            features = self.feature_extractor.extract_features(
                df=window_data,
                day_index=day_index,
                window=20
            )
            
            features_list.append(features)
            day_indices_list.append(day_index)
        
        # 배열 변환
        features_seq = np.array(features_list, dtype=np.float32)  # (seq_len, input_features)
        day_indices = np.array(day_indices_list, dtype=np.float32)  # (seq_len,)
        
        return features_seq, day_indices
    
    def predict(
        self,
        price_data: pd.DataFrame,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        매매 신호 예측
        
        Args:
            price_data: OHLCV 데이터프레임 (최소 seq_len개 필요)
            current_time: 현재 시간 (None이면 자동)
        
        Returns:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "confidence": float (0.0 ~ 1.0),
                "probabilities": {
                    "BUY": float,
                    "SELL": float,
                    "HOLD": float
                },
                "model_used": bool
            }
        """
        if not self.model_loaded:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "probabilities": {"BUY": 0.0, "SELL": 0.0, "HOLD": 1.0},
                "model_used": False,
                "error": "모델 로드 실패"
            }
        
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # 입력 시퀀스 준비
            features_seq, day_indices = self._prepare_sequence(price_data, current_time)
            
            # 텐서 변환
            features_tensor = torch.FloatTensor(features_seq).unsqueeze(0).to(self.device)  # (1, seq_len, input_features)
            day_indices_tensor = torch.FloatTensor(day_indices).unsqueeze(0).to(self.device)  # (1, seq_len)
            
            # 예측 수행
            with torch.no_grad():
                outputs = self.model(features_tensor, day_indices_tensor)  # (1, 3)
                probabilities = torch.softmax(outputs, dim=1).cpu().numpy()[0]  # (3,)
            
            # 신호 결정
            signal_idx = np.argmax(probabilities)
            signal_map = {0: "BUY", 1: "SELL", 2: "HOLD"}
            signal = signal_map[signal_idx]
            
            # 신뢰도 계산 (최대 확률)
            confidence = float(probabilities[signal_idx])
            
            return {
                "signal": signal,
                "confidence": confidence,
                "probabilities": {
                    "BUY": float(probabilities[0]),
                    "SELL": float(probabilities[1]),
                    "HOLD": float(probabilities[2])
                },
                "model_used": True
            }
            
        except Exception as e:
            logger.error(f"❌ 예측 실패: {e}")
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "probabilities": {"BUY": 0.0, "SELL": 0.0, "HOLD": 1.0},
                "model_used": False,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """모델 사용 가능 여부"""
        return self.model_loaded and self.model is not None


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    # 더미 데이터 생성
    dates = pd.date_range('2024-01-01', periods=100, freq='1H')
    test_data = pd.DataFrame({
        'open': np.random.randn(100) * 100 + 50000,
        'high': np.random.randn(100) * 100 + 50100,
        'low': np.random.randn(100) * 100 + 49900,
        'close': np.random.randn(100) * 100 + 50000,
        'volume': np.random.rand(100) * 1000
    }, index=dates)
    
    # 예측기 초기화
    predictor = Phase1ModelPredictor()
    
    if predictor.is_available():
        # 예측 수행
        result = predictor.predict(test_data)
        print(f"예측 결과: {result}")
    else:
        print("⚠️ 모델 사용 불가")

