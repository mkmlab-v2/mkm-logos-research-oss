#!/usr/bin/env python3
"""
HMM-LSTM 하이브리드 파이프라인

HMM으로 과거 데이터 라벨링 → LSTM으로 미래 국면 예측
- 비지도 라벨링: HMM으로 과거 데이터 라벨링
- 시퀀스 학습: LSTM으로 국면 전환 패턴 학습
- 실시간 예측: 미래 국면 확률 출력
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from .market_regime_detector import MarketRegimeDetector
from .regime_feature_engine import RegimeFeatureEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RegimeLSTMPredictor:
    """
    LSTM 기반 국면 예측
    
    HMM으로 과거 데이터를 라벨링하고,
    LSTM으로 미래 국면을 예측하는 하이브리드 모델
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        n_regimes: int = 6,
        lstm_units: int = 64,
        dropout_rate: float = 0.2
    ):
        """
        Args:
            sequence_length: 시퀀스 길이 (과거 몇 개 캔들 사용)
            n_regimes: 국면 개수 (기본값: 6)
            lstm_units: LSTM 유닛 수
            dropout_rate: 드롭아웃 비율
        """
        self.sequence_length = sequence_length
        self.n_regimes = n_regimes
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        
        self.hmm_detector = MarketRegimeDetector(n_states=n_regimes)
        self.feature_engine = RegimeFeatureEngine()
        self.scaler = StandardScaler()
        self.lstm_model = None
        self.fitted = False
    
    def prepare_sequences(
        self,
        features: pd.DataFrame,
        labels: np.ndarray,
        sequence_length: int = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        시퀀스 데이터 준비
        
        Args:
            features: 특징 데이터프레임
            labels: 국면 라벨 배열
            sequence_length: 시퀀스 길이
        
        Returns:
            (X, y) 튜플
            - X: (n_samples, sequence_length, n_features) 형태의 시퀀스
            - y: (n_samples, n_regimes) 형태의 원-핫 인코딩된 라벨
        """
        if sequence_length is None:
            sequence_length = self.sequence_length
        
        X, y = [], []
        
        for i in range(sequence_length, len(features)):
            # 시퀀스 추출
            seq = features.iloc[i-sequence_length:i].values
            X.append(seq)
            
            # 라벨 (다음 시점의 국면)
            label = labels[i]
            y.append(label)
        
        X = np.array(X)
        y = np.array(y)
        
        # 원-핫 인코딩
        y_onehot = np.zeros((len(y), self.n_regimes))
        for i, label in enumerate(y):
            y_onehot[i, int(label)] = 1.0
        
        logger.info(
            f"✅ 시퀀스 데이터 준비 완료: "
            f"X shape={X.shape}, y shape={y_onehot.shape}"
        )
        
        return X, y_onehot
    
    def build_lstm_model(
        self,
        input_shape: Tuple[int, int],
        n_regimes: int = None
    ) -> keras.Model:
        """
        LSTM 모델 구축
        
        Args:
            input_shape: (sequence_length, n_features)
            n_regimes: 국면 개수
        
        Returns:
            컴파일된 Keras 모델
        """
        if n_regimes is None:
            n_regimes = self.n_regimes
        
        model = keras.Sequential([
            # LSTM 레이어 1
            layers.LSTM(
                self.lstm_units,
                return_sequences=True,
                input_shape=input_shape
            ),
            layers.Dropout(self.dropout_rate),
            
            # LSTM 레이어 2
            layers.LSTM(self.lstm_units, return_sequences=False),
            layers.Dropout(self.dropout_rate),
            
            # Dense 레이어
            layers.Dense(32, activation='relu'),
            layers.Dropout(self.dropout_rate),
            
            # 출력 레이어 (국면 확률)
            layers.Dense(n_regimes, activation='softmax')
        ])
        
        # 모델 컴파일
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        logger.info("✅ LSTM 모델 구축 완료")
        model.summary()
        
        return model
    
    def train(
        self,
        historical_data: pd.DataFrame,
        epochs: int = 50,
        batch_size: int = 32,
        validation_split: float = 0.2
    ):
        """
        HMM 라벨링 + LSTM 학습
        
        Args:
            historical_data: 과거 OHLCV 데이터
            epochs: 학습 에포크 수
            batch_size: 배치 크기
            validation_split: 검증 데이터 비율
        """
        logger.info("🚀 HMM-LSTM 하이브리드 모델 학습 시작...")
        
        # 1. HMM으로 과거 데이터 라벨링
        logger.info("📊 Step 1: HMM으로 과거 데이터 라벨링...")
        self.hmm_detector.fit(historical_data)
        
        # 각 시점의 국면 탐지
        labels = []
        for i in range(len(historical_data)):
            current_data = historical_data.iloc[:i+1]
            if len(current_data) < 20:  # 최소 데이터 필요
                labels.append(0)  # 기본값
                continue
            
            regime_result = self.hmm_detector.detect_regime(
                current_data,
                return_probabilities=False
            )
            labels.append(regime_result['dominant_state'])
        
        labels = np.array(labels)
        logger.info(f"✅ HMM 라벨링 완료: {len(labels)}개 샘플")
        
        # 2. 특징 추출
        logger.info("📊 Step 2: 특징 추출...")
        features = self.feature_engine.extract_features(historical_data)
        
        # PCA 차원 축소 (HMM과 동일한 모델 사용)
        features_pca, _ = self.feature_engine.pca_reduce(features, fit=True)
        
        # 표준화
        features_scaled = self.scaler.fit_transform(features_pca)
        features_df = pd.DataFrame(
            features_scaled,
            index=historical_data.index
        )
        
        logger.info(f"✅ 특징 추출 완료: {features_df.shape}")
        
        # 3. 시퀀스 데이터 준비
        logger.info("📊 Step 3: 시퀀스 데이터 준비...")
        X, y = self.prepare_sequences(features_df, labels)
        
        if len(X) == 0:
            raise ValueError("시퀀스 데이터가 생성되지 않았습니다. 데이터가 부족합니다.")
        
        # 4. LSTM 모델 구축
        logger.info("📊 Step 4: LSTM 모델 구축...")
        input_shape = (X.shape[1], X.shape[2])
        self.lstm_model = self.build_lstm_model(input_shape)
        
        # 5. 모델 학습
        logger.info("📊 Step 5: LSTM 모델 학습...")
        history = self.lstm_model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=1,
            shuffle=True
        )
        
        self.fitted = True
        
        # 학습 결과 로깅
        final_accuracy = history.history['accuracy'][-1]
        final_val_accuracy = history.history.get('val_accuracy', [0])[-1]
        
        logger.info(f"✅ LSTM 모델 학습 완료")
        logger.info(f"   최종 정확도: {final_accuracy:.2%}")
        logger.info(f"   검증 정확도: {final_val_accuracy:.2%}")
    
    def predict_regime(
        self,
        current_data: pd.DataFrame,
        return_probabilities: bool = True
    ) -> Dict[str, Any]:
        """
        미래 국면 확률 예측
        
        Args:
            current_data: 현재 시장 데이터 (최근 N개 캔들)
            return_probabilities: 확률 분포 반환 여부
        
        Returns:
            국면 예측 정보 딕셔너리
        """
        if not self.fitted:
            raise ValueError("LSTM 모델이 학습되지 않았습니다. train() 메서드를 먼저 실행하세요.")
        
        # 1. 특징 추출
        features = self.feature_engine.extract_features(current_data)
        
        # PCA 변환 (학습된 모델 사용)
        features_pca, _ = self.feature_engine.pca_reduce(features, fit=False)
        
        # 표준화
        features_scaled = self.scaler.transform(features_pca)
        
        # 2. 시퀀스 준비 (최근 sequence_length개만 사용)
        if len(features_scaled) < self.sequence_length:
            # 데이터 부족 시 패딩
            padding = np.zeros((self.sequence_length - len(features_scaled), features_scaled.shape[1]))
            features_scaled = np.vstack([padding, features_scaled])
        
        sequence = features_scaled[-self.sequence_length:].reshape(1, self.sequence_length, -1)
        
        # 3. LSTM 예측
        predictions = self.lstm_model.predict(sequence, verbose=0)
        regime_probs = predictions[0]
        
        # 4. 결과 구성
        dominant_state = int(np.argmax(regime_probs))
        dominant_regime = self.hmm_detector.REGIME_NAMES[dominant_state]
        
        result = {
            "dominant_regime": dominant_regime,
            "dominant_state": dominant_state,
            "confidence": float(regime_probs[dominant_state])
        }
        
        if return_probabilities:
            regime_probs_dict = {
                self.hmm_detector.REGIME_NAMES[i]: float(regime_probs[i])
                for i in range(self.n_regimes)
            }
            result["probabilities"] = regime_probs_dict
        
        return result
    
    def predict_next_n_regimes(
        self,
        current_data: pd.DataFrame,
        n_steps: int = 3
    ) -> List[Dict[str, Any]]:
        """
        향후 N단계 국면 예측
        
        Args:
            current_data: 현재 시장 데이터
            n_steps: 예측 단계 수
        
        Returns:
            향후 N단계 국면 예측 리스트
        """
        predictions = []
        
        # 현재 데이터로 시작
        data = current_data.copy()
        
        for step in range(n_steps):
            # 현재 시점 예측
            prediction = self.predict_regime(data, return_probabilities=True)
            predictions.append({
                "step": step + 1,
                "regime": prediction["dominant_regime"],
                "confidence": prediction["confidence"],
                "probabilities": prediction.get("probabilities", {})
            })
            
            # 다음 시점을 위한 데이터 업데이트 (간단한 시뮬레이션)
            # 실제로는 더 정교한 방법이 필요할 수 있음
            last_price = data['close'].iloc[-1]
            last_volume = data['volume'].iloc[-1]
            
            # 가격 변화 시뮬레이션 (간단한 랜덤 워크)
            price_change = np.random.randn() * 0.01
            new_price = last_price * (1 + price_change)
            
            # 새로운 캔들 추가 (간단한 시뮬레이션)
            new_row = pd.DataFrame({
                'open': [last_price],
                'high': [max(last_price, new_price)],
                'low': [min(last_price, new_price)],
                'close': [new_price],
                'volume': [last_volume * (1 + np.random.randn() * 0.1)]
            }, index=[data.index[-1] + pd.Timedelta(hours=1)])
            
            data = pd.concat([data, new_row])
        
        return predictions

