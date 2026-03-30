#!/usr/bin/env python3
"""
시장 국면 탐지를 위한 특징 공학 모듈

기술적 지표 추출 및 PCA 차원 축소
- 로그 수익률, ATR, RSI, MACD, ADX 등
- PCA를 통한 차원 축소 (4개 주성분, 95% 설명력)
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
import logging
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RegimeFeatureEngine:
    """국면 탐지를 위한 특징 공학"""
    
    def __init__(self, n_components: int = 4):
        """
        Args:
            n_components: PCA 주성분 개수 (기본값: 4, 95% 설명력 목표)
        """
        self.n_components = n_components
        self.pca = PCA(n_components=n_components)
        self.scaler = StandardScaler()
        self.fitted = False
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        ATR (Average True Range) 계산
        
        Args:
            df: OHLCV 데이터프레임
            period: 기간 (기본값: 14)
        
        Returns:
            ATR 시리즈
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range 계산
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR = TR의 이동평균
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        RSI (Relative Strength Index) 계산
        
        Args:
            df: OHLCV 데이터프레임
            period: 기간 (기본값: 14)
        
        Returns:
            RSI 시리즈 (0-100)
        """
        close = df['close']
        delta = close.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(
        self,
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> pd.Series:
        """
        MACD (Moving Average Convergence Divergence) 계산
        
        Args:
            df: OHLCV 데이터프레임
            fast: 빠른 이동평균 기간
            slow: 느린 이동평균 기간
            signal: 시그널 라인 기간
        
        Returns:
            MACD 라인 (MACD - Signal)
        """
        close = df['close']
        
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        
        macd = macd_line - signal_line
        
        return macd
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        ADX (Average Directional Index) 계산
        
        Args:
            df: OHLCV 데이터프레임
            period: 기간 (기본값: 14)
        
        Returns:
            ADX 시리즈 (0-100, 높을수록 추세 강함)
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # +DM, -DM 계산
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # True Range
        tr = self.calculate_atr(df, period=1)
        
        # +DI, -DI 계산
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
        
        # DX 계산
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # ADX = DX의 이동평균
        adx = dx.rolling(window=period).mean()
        
        return adx.fillna(0)
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기술적 지표 추출
        
        Args:
            df: OHLCV 데이터프레임 (columns: open, high, low, close, volume)
        
        Returns:
            특징 데이터프레임
        """
        features = pd.DataFrame(index=df.index)
        
        # 로그 수익률
        features['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # 변동성 (ATR, 정규화)
        atr = self.calculate_atr(df, period=14)
        features['atr_normalized'] = atr / df['close']  # 가격 대비 변동성
        
        # 모멘텀 (RSI, MACD)
        features['rsi'] = self.calculate_rsi(df, period=14) / 100.0  # 0-1 정규화
        features['macd'] = self.calculate_macd(df)
        
        # 추세 강도 (ADX)
        adx = self.calculate_adx(df, period=14)
        features['adx'] = adx / 100.0  # 0-1 정규화
        
        # 거래량 변화율
        features['volume_change'] = df['volume'].pct_change()
        
        # 가격 모멘텀 (가격 변화율)
        features['price_momentum'] = df['close'].pct_change(periods=5)  # 5기간 모멘텀
        
        # 변동성 지표 (볼린저 밴드 폭 근사)
        rolling_std = df['close'].rolling(window=20).std()
        features['volatility_ratio'] = rolling_std / df['close']
        
        # 결측치 처리
        features = features.fillna(method='bfill').fillna(0)
        
        return features
    
    def pca_reduce(
        self,
        features: pd.DataFrame,
        fit: bool = True
    ) -> Tuple[np.ndarray, float]:
        """
        PCA 차원 축소 (95% 설명력 목표)
        
        Args:
            features: 특징 데이터프레임
            fit: 모델 학습 여부 (True: 학습, False: 변환만)
        
        Returns:
            (변환된 특징 배열, 설명력)
        """
        # 표준화
        if fit:
            features_scaled = self.scaler.fit_transform(features)
            features_pca = self.pca.fit_transform(features_scaled)
            self.fitted = True
        else:
            if not self.fitted:
                raise ValueError("PCA 모델이 학습되지 않았습니다. fit=True로 먼저 실행하세요.")
            features_scaled = self.scaler.transform(features)
            features_pca = self.pca.transform(features_scaled)
        
        explained_variance = self.pca.explained_variance_ratio_.sum()
        
        logger.info(f"✅ PCA 차원 축소 완료: {features.shape[1]}차원 → {self.n_components}차원")
        logger.info(f"   설명력: {explained_variance:.2%}")
        
        return features_pca, explained_variance
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        주성분별 특징 기여도 반환
        
        Returns:
            주성분별 기여도 딕셔너리
        """
        if not self.fitted:
            return {}
        
        importance = {}
        for i, component in enumerate(self.pca.components_):
            importance[f"PC{i+1}"] = {
                "explained_variance": float(self.pca.explained_variance_ratio_[i]),
                "components": component.tolist()
            }
        
        return importance

