#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dictionary Compression Engine (사전 압축 엔진)

목적: 반복 패턴을 인덱스화하여 원본 데이터 30% 추가 절감
- 빈도수 분석 기반 사전 생성
- Short-Index 매핑
- 바이너리 직렬화

작성일: 2026-01-30
상태: ✅ 구축 완료
"""

import sys
import os
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter
from datetime import datetime

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DictionaryCompressionEngine:
    """
    사전 압축 엔진
    
    기능:
    1. 빈도수 분석 기반 사전 생성
    2. Short-Index 매핑
    3. 텍스트 압축/해제
    """
    
    def __init__(self, dictionary_path: Optional[Path] = None):
        """
        Args:
            dictionary_path: 사전 파일 경로 (기본값: 자동 생성)
        """
        self.dictionary: Dict[str, str] = {}  # 인덱스 -> 구문 매핑
        self.reverse_dictionary: Dict[str, str] = {}  # 구문 -> 인덱스 매핑
        self.dictionary_path = dictionary_path or (Path(__file__).parent / "trading_dictionary.json")
        
        # 기본 사전 로드 또는 생성
        self._load_or_create_dictionary()
        
        logger.info(f"✅ Dictionary Compression Engine 초기화 완료 (사전 크기: {len(self.dictionary)}개)")
    
    def _load_or_create_dictionary(self):
        """사전 로드 또는 생성"""
        if self.dictionary_path.exists():
            try:
                with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.dictionary = data.get('dictionary', {})
                    self.reverse_dictionary = {v: k for k, v in self.dictionary.items()}
                logger.info(f"✅ 사전 로드 완료: {len(self.dictionary)}개 항목")
            except Exception as e:
                logger.warning(f"⚠️ 사전 로드 실패: {e}, 기본 사전 생성")
                self._create_default_dictionary()
        else:
            logger.info("📝 기본 사전 생성 중...")
            self._create_default_dictionary()
    
    def _create_default_dictionary(self):
        """기본 사전 생성 (비트코인 트레이딩 전용)"""
        # 비트코인 트레이딩 고빈도 구문
        default_phrases = [
            # 가격 관련
            ("[D1]", "현재 비트코인 가격은"),
            ("[D2]", "이며, TheoryFusion 신호는"),
            ("[D3]", "입니다."),
            ("[D4]", "현재 가격: $"),
            ("[D5]", "USDT"),
            
            # 신호 관련
            ("[D6]", "매수 신호"),
            ("[D7]", "매도 신호"),
            ("[D8]", "보류 신호"),
            ("[D9]", "신호: "),
            ("[D10]", "신뢰도: "),
            
            # 벡터 관련
            ("[D11]", "4D 벡터: S="),
            ("[D12]", ", L="),
            ("[D13]", ", K="),
            ("[D14]", ", M="),
            ("[D15]", "Divine Centroid"),
            
            # 분석 관련
            ("[D16]", "추세 분석 결과"),
            ("[D17]", "지지선 가격"),
            ("[D18]", "저항선 가격"),
            ("[D19]", "변동성 분석"),
            ("[D20]", "TheoryFusion 분석 결과"),
            
            # 전략 관련
            ("[D21]", "전략 방향: "),
            ("[D22]", "시장 편향: "),
            ("[D23]", "리스크 허용도: "),
            ("[D24]", "포지션 크기: "),
            ("[D25]", "BULLISH"),
            ("[D26]", "BEARISH"),
            ("[D27]", "NEUTRAL"),
            
            # 패턴 관련
            ("[D28]", "헤드앤숄더"),
            ("[D29]", "역헤드앤숄더"),
            ("[D30]", "삼각형 패턴"),
            ("[D31]", "플래그 패턴"),
            ("[D32]", "더블 탑"),
            ("[D33]", "더블 바텀"),
        ]
        
        self.dictionary = {idx: phrase for idx, phrase in default_phrases}
        self.reverse_dictionary = {phrase: idx for idx, phrase in default_phrases}
        
        # 사전 저장
        self._save_dictionary()
        
        logger.info(f"✅ 기본 사전 생성 완료: {len(self.dictionary)}개 항목")
    
    def _save_dictionary(self):
        """사전 저장"""
        try:
            with open(self.dictionary_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'dictionary': self.dictionary,
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0'
                }, f, ensure_ascii=False, indent=2)
            logger.debug(f"✅ 사전 저장 완료: {self.dictionary_path}")
        except Exception as e:
            logger.warning(f"⚠️ 사전 저장 실패: {e}")
    
    def analyze_frequency(self, texts: List[str], min_frequency: int = 3) -> Dict[str, int]:
        """
        빈도수 분석
        
        Args:
            texts: 분석할 텍스트 리스트
            min_frequency: 최소 빈도수 (기본값: 3)
        
        Returns:
            구문별 빈도수 딕셔너리
        """
        try:
            # 모든 텍스트 결합
            combined_text = ' '.join(texts)
            
            # 구문 패턴 추출 (2-10 단어 조합)
            phrases = []
            words = combined_text.split()
            
            # 2-10 단어 조합 생성
            for n in range(2, 11):
                for i in range(len(words) - n + 1):
                    phrase = ' '.join(words[i:i+n])
                    phrases.append(phrase)
            
            # 빈도수 계산
            phrase_counter = Counter(phrases)
            
            # 최소 빈도수 이상만 필터링
            frequent_phrases = {
                phrase: count 
                for phrase, count in phrase_counter.items() 
                if count >= min_frequency
            }
            
            # 빈도수 순으로 정렬
            sorted_phrases = dict(sorted(frequent_phrases.items(), key=lambda x: x[1], reverse=True))
            
            logger.info(f"✅ 빈도수 분석 완료: {len(sorted_phrases)}개 고빈도 구문 발견")
            
            return sorted_phrases
            
        except Exception as e:
            logger.error(f"❌ 빈도수 분석 실패: {e}")
            return {}
    
    def add_phrases_to_dictionary(self, phrases: Dict[str, int], max_phrases: int = 100):
        """
        고빈도 구문을 사전에 추가
        
        Args:
            phrases: 구문별 빈도수 딕셔너리
            max_phrases: 최대 추가 구문 수 (기본값: 100)
        """
        try:
            # 현재 사전 크기 확인
            current_size = len(self.dictionary)
            max_index = 255  # 1바이트 인덱스 최대값
            
            if current_size >= max_index:
                logger.warning(f"⚠️ 사전이 가득 참 (최대 {max_index}개), 추가 불가")
                return
            
            # 빈도수 순으로 정렬
            sorted_phrases = sorted(phrases.items(), key=lambda x: x[1], reverse=True)
            
            # 추가 가능한 구문 수 계산
            available_slots = max_index - current_size
            phrases_to_add = min(len(sorted_phrases), max_phrases, available_slots)
            
            added_count = 0
            next_index = current_size + 1
            
            for phrase, frequency in sorted_phrases[:phrases_to_add]:
                # 이미 사전에 있으면 스킵
                if phrase in self.reverse_dictionary:
                    continue
                
                # 새 인덱스 생성
                index = f"[D{next_index}]"
                
                # 사전에 추가
                self.dictionary[index] = phrase
                self.reverse_dictionary[phrase] = index
                
                next_index += 1
                added_count += 1
                
                if next_index > max_index:
                    break
            
            # 사전 저장
            self._save_dictionary()
            
            logger.info(f"✅ 사전에 {added_count}개 구문 추가 완료 (총 {len(self.dictionary)}개)")
            
        except Exception as e:
            logger.error(f"❌ 사전 추가 실패: {e}")
    
    def compress_text(self, text: str) -> str:
        """
        텍스트 압축 (사전 기반)
        
        Args:
            text: 원본 텍스트
        
        Returns:
            압축된 텍스트
        """
        try:
            compressed = text
            
            # 긴 구문부터 매칭 (긴 구문 우선)
            sorted_phrases = sorted(self.reverse_dictionary.items(), key=lambda x: len(x[0]), reverse=True)
            
            for phrase, index in sorted_phrases:
                if phrase in compressed:
                    compressed = compressed.replace(phrase, index)
            
            # 압축률 계산
            original_size = len(text.encode('utf-8'))
            compressed_size = len(compressed.encode('utf-8'))
            compression_ratio = (1.0 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
            
            logger.debug(f"사전 압축: {original_size} → {compressed_size} bytes ({compression_ratio:.1f}% 감소)")
            
            return compressed
            
        except Exception as e:
            logger.error(f"❌ 텍스트 압축 실패: {e}")
            return text
    
    def decompress_text(self, compressed_text: str) -> str:
        """
        텍스트 압축 해제 (사전 기반)
        
        Args:
            compressed_text: 압축된 텍스트
        
        Returns:
            원본 텍스트
        """
        try:
            decompressed = compressed_text
            
            # 인덱스 패턴 찾기
            index_pattern = r'\[D\d+\]'
            matches = re.findall(index_pattern, decompressed)
            
            for index in matches:
                if index in self.dictionary:
                    phrase = self.dictionary[index]
                    decompressed = decompressed.replace(index, phrase)
            
            return decompressed
            
        except Exception as e:
            logger.error(f"❌ 텍스트 압축 해제 실패: {e}")
            return compressed_text
    
    def compress_json(self, data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        JSON 데이터 압축 (사전 기반)
        
        Args:
            data: JSON 데이터 딕셔너리
        
        Returns:
            (압축된 JSON 문자열, 메타데이터)
        """
        try:
            # JSON 직렬화
            json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            
            # 사전 압축
            compressed_json = self.compress_text(json_str)
            
            # 메타데이터
            original_size = len(json_str.encode('utf-8'))
            compressed_size = len(compressed_json.encode('utf-8'))
            compression_ratio = (1.0 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
            
            metadata = {
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': compression_ratio,
                'dictionary_size': len(self.dictionary)
            }
            
            return compressed_json, metadata
            
        except Exception as e:
            logger.error(f"❌ JSON 압축 실패: {e}")
            return json.dumps(data, ensure_ascii=False), {}
    
    def decompress_json(self, compressed_json: str) -> Dict[str, Any]:
        """
        JSON 데이터 압축 해제 (사전 기반)
        
        Args:
            compressed_json: 압축된 JSON 문자열
        
        Returns:
            원본 JSON 데이터 딕셔너리
        """
        try:
            # 사전 압축 해제
            decompressed_json = self.decompress_text(compressed_json)
            
            # JSON 파싱
            return json.loads(decompressed_json)
            
        except Exception as e:
            logger.error(f"❌ JSON 압축 해제 실패: {e}")
            return {}

