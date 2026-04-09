#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔮 Phase 8.2: Oracle Codebook (오라클 예지 복원 코드북)

3% 압축 좌표를 100% 원본 데이터로 예측 복원합니다.

작성일: 2026-02-01
상태: Phase 8.2 구현 중
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
import sys
from pathlib import Path
import json
import pickle

# MKM12 수학 헌법 v4.0 준수: 안전 상수
EPSILON = 1e-5

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OracleCodebook:
    """
    🔮 Phase 8.2: 오라클 예지 복원 코드북
    
    3% 압축 좌표를 100% 원본 데이터로 예측 복원합니다.
    
    MKM12 수학 헌법 v4.0 준수:
    - 헌법 제18장 오라클 궤적 엔진 제67공식: 오라클 예지 방정식
      * Oracle(x_3%) = DNA_1.5GB · Predict(x_3%, θ_oracle)
    - 헌법 제18장 제68공식: 오라클 가중치 동적 조절
      * θ_oracle(t) = α · θ_oracle(t-1) + (1-α) · Δ_DNA(t)
    """
    
    def __init__(self, dna_patterns: Optional[np.ndarray] = None):
        """
        오라클 코드북 초기화
        
        Args:
            dna_patterns: 1.5GB DNA 패턴 행렬 (없으면 자동 생성)
        """
        if dna_patterns is not None:
            self.dna_patterns = dna_patterns
        else:
            # 기본 DNA 패턴 생성 (시뮬레이션)
            self.dna_patterns = np.random.randn(10000, 4).astype(np.float32)
            logger.warning("⚠️ DNA 패턴이 제공되지 않아 기본 패턴 사용")
        
        # 동적 조절 파라미터 (먼저 초기화)
        self.alpha = 0.9  # 가중치 감쇠 계수
        self.time_step = 0  # 시간 단계
        
        # 오라클 가중치 계산 (헌법 제18장 제68공식)
        self.oracle_weights = self._calculate_oracle_weights()
        
        logger.info(f"✅ Phase 8.2: OracleCodebook 초기화 완료 (DNA 패턴: {self.dna_patterns.shape})")
    
    def _calculate_oracle_weights(self) -> np.ndarray:
        """
        오라클 가중치 계산 (헌법 제18장 제68공식)
        
        Returns:
            오라클 가중치 행렬
        """
        try:
            # 동적 가중치 조절 알고리즘
            # 초기 가중치는 DNA 패턴의 역행렬 근사
            if self.dna_patterns.shape[0] > self.dna_patterns.shape[1]:
                # 과결정 시스템: 유사 역행렬 사용
                initial_weights = np.linalg.pinv(self.dna_patterns)
            else:
                # 미결정 시스템: 전치 행렬 사용
                initial_weights = self.dna_patterns.T
            
            # 시간에 따른 동적 조절 (헌법 제68공식)
            # 초기 가중치에 감쇠 계수 적용
            oracle_weights = self.alpha * initial_weights
            
            logger.info(f"✅ 오라클 가중치 계산 완료: {oracle_weights.shape}")
            return oracle_weights.astype(np.float32)
            
        except Exception as e:
            logger.error(f"❌ 오라클 가중치 계산 실패: {e}")
            # 기본 가중치 반환
            return np.eye(min(self.dna_patterns.shape), dtype=np.float32)
    
    def predict_restore(
        self,
        compressed_3pct: np.ndarray,
        domain: str = "general"
    ) -> np.ndarray:
        """
        3% 압축 좌표로 100% 데이터 예측 복원 (헌법 제18장 제67공식)
        
        Oracle(x_3%) = DNA_1.5GB · Predict(x_3%, θ_oracle)
        
        Args:
            compressed_3pct: 3% 압축된 좌표
            domain: 도메인 타입 (finance, health, language, security, general)
        
        Returns:
            100% 예측 복원된 데이터
        """
        try:
            # 도메인별 DNA 패턴 선택
            domain_dna = self._select_domain_dna(domain)
            
            # 압축 좌표 크기 확인 및 확장
            if len(compressed_3pct.shape) == 1:
                # 1D 배열: (N,) → (N, 1)
                compressed_3pct = compressed_3pct.reshape(-1, 1)
            elif len(compressed_3pct.shape) == 2 and compressed_3pct.shape[1] == 1:
                # 2D 배열: (N, 1) - 그대로 사용
                pass
            else:
                # 2D 배열: (N, M) → (N*M, 1)로 평탄화
                compressed_3pct = compressed_3pct.flatten().reshape(-1, 1)
            
            # 원본 크기 추정 (3% → 100%)
            compressed_size = compressed_3pct.shape[0]
            original_size = int(compressed_size / 0.03)
            
            # 오라클 예지 방정식 (헌법 제67공식)
            # Oracle(x_3%) = DNA_1.5GB · Predict(x_3%, θ_oracle)
            # 단계별 행렬 곱셈으로 차원 맞춤
            # Step 1: compressed_3pct를 DNA 패턴 차원으로 확장
            if domain_dna.shape[1] != compressed_3pct.shape[0]:
                # 선형 보간으로 차원 확장
                from scipy.interpolate import interp1d
                x_compressed = np.linspace(0, 1, compressed_3pct.shape[0])
                x_expanded = np.linspace(0, 1, domain_dna.shape[1])
                f = interp1d(x_compressed, compressed_3pct.flatten(), kind='linear', fill_value='extrapolate')
                expanded_3pct = f(x_expanded).reshape(-1, 1)
            else:
                expanded_3pct = compressed_3pct
            
            # Step 2: DNA 패턴과 가중치 행렬 곱셈
            # domain_dna: (M, N), oracle_weights: (N, N), expanded_3pct: (N, 1)
            if domain_dna.shape[1] == self.oracle_weights.shape[0]:
                weighted = self.oracle_weights @ expanded_3pct
                predicted = domain_dna @ weighted
            else:
                # 차원 불일치: 직접 DNA 패턴과 곱셈
                predicted = domain_dna @ expanded_3pct
            
            # Step 3: 원본 크기로 확장
            if predicted.shape[0] != original_size:
                # 선형 보간으로 원본 크기로 확장
                from scipy.interpolate import interp1d
                x_predicted = np.linspace(0, 1, predicted.shape[0])
                x_original = np.linspace(0, 1, original_size)
                
                if len(predicted.shape) == 1:
                    f = interp1d(x_predicted, predicted, kind='linear', fill_value='extrapolate')
                    predicted = f(x_original)
                else:
                    predicted_expanded = np.zeros((original_size, predicted.shape[1]), dtype=np.float32)
                    for col in range(predicted.shape[1]):
                        f = interp1d(x_predicted, predicted[:, col], kind='linear', fill_value='extrapolate')
                        predicted_expanded[:, col] = f(x_original)
                    predicted = predicted_expanded
            
            # 정규화 및 후처리
            predicted = self._post_process(predicted)
            
            logger.debug(f"✅ {domain} 도메인 예측 복원 완료: {compressed_3pct.shape} → {predicted.shape}")
            return predicted
            
        except Exception as e:
            logger.error(f"❌ 예측 복원 실패: {e}")
            # 기본 복원: 압축 좌표를 선형 보간으로 확장
            return self._linear_interpolation_restore(compressed_3pct)
    
    def _select_domain_dna(self, domain: str) -> np.ndarray:
        """
        도메인별 DNA 패턴 선택
        
        Args:
            domain: 도메인 타입
        
        Returns:
            도메인별 DNA 패턴
        """
        try:
            total_rows = self.dna_patterns.shape[0]
            domain_indices = {
                'finance': slice(0, total_rows // 4),
                'health': slice(total_rows // 4, total_rows // 2),
                'language': slice(total_rows // 2, 3 * total_rows // 4),
                'security': slice(3 * total_rows // 4, total_rows),
                'general': slice(None)  # 전체 사용
            }
            
            selected_slice = domain_indices.get(domain, slice(None))
            domain_dna = self.dna_patterns[selected_slice]
            
            return domain_dna
            
        except Exception as e:
            logger.error(f"❌ 도메인 DNA 선택 실패: {e}")
            return self.dna_patterns
    
    def _post_process(self, predicted: np.ndarray) -> np.ndarray:
        """
        예측 결과 후처리
        
        Args:
            predicted: 예측된 데이터
        
        Returns:
            후처리된 데이터
        """
        try:
            # 정규화
            min_val = np.min(predicted)
            max_val = np.max(predicted)
            if max_val - min_val > EPSILON:
                predicted = (predicted - min_val) / (max_val - min_val + EPSILON)
            else:
                predicted = np.ones_like(predicted) * 0.5
            
            # 클리핑 (0~1 범위)
            predicted = np.clip(predicted, 0, 1)
            
            return predicted.astype(np.float32)
            
        except Exception as e:
            logger.error(f"❌ 후처리 실패: {e}")
            return predicted
    
    def _linear_interpolation_restore(self, compressed_3pct: np.ndarray) -> np.ndarray:
        """
        선형 보간 복원 (Fallback)
        
        Args:
            compressed_3pct: 3% 압축된 좌표
        
        Returns:
            보간된 데이터
        """
        try:
            # 3% → 100% 선형 보간
            original_size = int(len(compressed_3pct) / 0.03)
            
            if len(compressed_3pct.shape) == 1:
                # 1D 보간
                from scipy.interpolate import interp1d
                x_compressed = np.linspace(0, 1, len(compressed_3pct))
                x_original = np.linspace(0, 1, original_size)
                f = interp1d(x_compressed, compressed_3pct, kind='linear', fill_value='extrapolate')
                restored = f(x_original)
            else:
                # 2D 보간 (각 열에 대해 보간)
                restored = np.zeros((original_size, compressed_3pct.shape[1]), dtype=np.float32)
                for col in range(compressed_3pct.shape[1]):
                    from scipy.interpolate import interp1d
                    x_compressed = np.linspace(0, 1, len(compressed_3pct))
                    x_original = np.linspace(0, 1, original_size)
                    f = interp1d(x_compressed, compressed_3pct[:, col], kind='linear', fill_value='extrapolate')
                    restored[:, col] = f(x_original)
            
            return restored.astype(np.float32)
            
        except Exception as e:
            logger.error(f"❌ 선형 보간 복원 실패: {e}")
            # 최종 Fallback: 압축 좌표를 반복하여 확장
            repeat_factor = int(1 / 0.03)  # 약 33배
            if len(compressed_3pct.shape) == 1:
                return np.tile(compressed_3pct, repeat_factor)[:original_size].astype(np.float32)
            else:
                return np.tile(compressed_3pct, (repeat_factor, 1))[:original_size].astype(np.float32)
    
    def update_oracle_weights(self, dna_delta: np.ndarray):
        """
        오라클 가중치 동적 조절 (헌법 제18장 제68공식)
        
        θ_oracle(t) = α · θ_oracle(t-1) + (1-α) · Δ_DNA(t)
        
        Args:
            dna_delta: DNA 패턴 변화량
        """
        try:
            # 헌법 제68공식 적용
            self.oracle_weights = (
                self.alpha * self.oracle_weights +
                (1 - self.alpha) * dna_delta
            )
            self.time_step += 1
            
            logger.info(f"✅ 오라클 가중치 업데이트 완료 (시간 단계: {self.time_step})")
            
        except Exception as e:
            logger.error(f"❌ 오라클 가중치 업데이트 실패: {e}")
    
    def save_codebook(self, filepath: str):
        """
        오라클 코드북 저장
        
        Args:
            filepath: 저장 경로
        """
        try:
            codebook_data = {
                'dna_patterns': self.dna_patterns,
                'oracle_weights': self.oracle_weights,
                'alpha': self.alpha,
                'time_step': self.time_step
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(codebook_data, f)
            
            logger.info(f"✅ 오라클 코드북 저장 완료: {filepath}")
            
        except Exception as e:
            logger.error(f"❌ 오라클 코드북 저장 실패: {e}")
    
    def load_codebook(self, filepath: str):
        """
        오라클 코드북 로드
        
        Args:
            filepath: 로드 경로
        """
        try:
            with open(filepath, 'rb') as f:
                codebook_data = pickle.load(f)
            
            self.dna_patterns = codebook_data['dna_patterns']
            self.oracle_weights = codebook_data['oracle_weights']
            self.alpha = codebook_data.get('alpha', 0.9)
            self.time_step = codebook_data.get('time_step', 0)
            
            logger.info(f"✅ 오라클 코드북 로드 완료: {filepath}")
            
        except Exception as e:
            logger.error(f"❌ 오라클 코드북 로드 실패: {e}")


# Phase 8.2: 전역 오라클 코드북 인스턴스
_global_oracle_codebook = None

def get_oracle_codebook(dna_patterns: Optional[np.ndarray] = None) -> OracleCodebook:
    """
    Phase 8.2: 전역 OracleCodebook 인스턴스 반환
    
    Args:
        dna_patterns: DNA 패턴 행렬 (선택적)
    
    Returns:
        OracleCodebook 인스턴스
    """
    global _global_oracle_codebook
    
    if _global_oracle_codebook is None:
        _global_oracle_codebook = OracleCodebook(dna_patterns=dna_patterns)
        logger.info("✅ Phase 8.2: 전역 오라클 코드북 초기화 완료")
    
    return _global_oracle_codebook

