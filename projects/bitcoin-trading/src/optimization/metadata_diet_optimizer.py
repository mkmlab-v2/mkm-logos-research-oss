#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 메타데이터 다이어트 최적화 - Phase 7-A 통합

목적: 짧은 텍스트의 메타데이터 오버헤드 감소
- 적응형 압축 전략 (텍스트 길이에 따라)
- 불필요한 메타데이터 제거
- 더 효율적인 바이너리 인코딩
- 목표: 짧은 텍스트 압축률 673% → 100% 이하

작성일: 2026-01-30
Phase: 7-A (메타데이터 다이어트)
통합: 비트코인 트레이딩 시스템
"""

import sys
import struct
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import OrderedDict
import logging

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "scripts"))

# MetadataMinimizer import (선택적)
try:
    from metadata_minimizer import MetadataMinimizer
    MINIMIZER_AVAILABLE = True
except ImportError:
    MINIMIZER_AVAILABLE = False
    logging.warning("⚠️ MetadataMinimizer import 실패, 표준 압축만 사용")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetadataDietOptimizer:
    """
    메타데이터 다이어트 최적화 엔진
    
    전략:
    1. 적응형 압축: 텍스트 길이에 따라 전략 변경
    2. 불필요한 메타데이터 제거
    3. 더 효율적인 바이너리 인코딩
    4. 값 압축 (중복 제거, 사전 기반)
    """
    
    # 텍스트 길이별 전략
    SHORT_TEXT_THRESHOLD = 200  # 200 bytes 이하: 최소 메타데이터
    MEDIUM_TEXT_THRESHOLD = 1000  # 1000 bytes 이하: 표준 압축
    LONG_TEXT_THRESHOLD = 5000  # 5000 bytes 이상: 최대 압축
    
    def __init__(self):
        """초기화"""
        if MINIMIZER_AVAILABLE:
            try:
                self.base_minimizer = MetadataMinimizer()
                logger.info("✅ MetadataMinimizer 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ MetadataMinimizer 초기화 실패: {e}")
                self.base_minimizer = None
        else:
            self.base_minimizer = None
        logger.info("✅ Metadata Diet Optimizer 초기화 완료")
    
    def _determine_strategy(self, text_size: int, metadata_size: int) -> str:
        """
        텍스트 크기에 따른 압축 전략 결정
        
        Args:
            text_size: 원본 텍스트 크기 (bytes)
            metadata_size: 메타데이터 크기 (bytes)
        
        Returns:
            전략 이름 ("minimal", "standard", "maximum")
        """
        if text_size <= self.SHORT_TEXT_THRESHOLD:
            # 짧은 텍스트: 항상 최소 메타데이터 전략 사용
            # 목표: 메타데이터/텍스트 비율 100% 이하
            return "minimal"
        elif text_size <= self.MEDIUM_TEXT_THRESHOLD:
            return "standard"
        else:
            return "maximum"
    
    def _compress_minimal(self, anchor_tags: Dict[str, Dict[str, Any]]) -> bytes:
        """
        최소 메타데이터 압축 (짧은 텍스트용)
        
        전략:
        - 위치 정보만 저장 (앵커 제거)
        - 값은 인덱스로만 참조
        - 타입 정보 제거 (복원 시 추론)
        """
        if not anchor_tags:
            return struct.pack("H", 0)
        
        sorted_tags = sorted(
            anchor_tags.items(),
            key=lambda x: x[1].get("original_start", 0)
        )
        
        binary_data = bytearray()
        binary_data.extend(struct.pack("H", len(sorted_tags)))
        
        prev_position = 0
        value_dict = {}  # 값 사전 (중복 제거)
        value_index = 0
        
        # 1단계: 값 사전 구축
        for tag, tag_data in sorted_tags:
            value = tag_data.get("value", "")
            if value not in value_dict:
                value_dict[value] = value_index
                value_index += 1
        
        # 2단계: 값 사전 저장 (먼저 저장하여 복원 시 먼저 읽을 수 있도록)
        value_dict_bytes = self._encode_value_dict_binary(value_dict)
        binary_data.extend(struct.pack("H", len(value_dict)))  # 값 개수 (2 bytes)
        binary_data.extend(struct.pack("H", len(value_dict_bytes)))  # 바이너리 크기 (2 bytes)
        binary_data.extend(value_dict_bytes)
        
        # 3단계: 태그 데이터 저장
        for tag, tag_data in sorted_tags:
            # 위치만 저장 (델타 인코딩)
            current_position = tag_data.get("original_start", 0)
            delta_position = current_position - prev_position
            prev_position = current_position
            
            # 값 인덱스
            value = tag_data.get("value", "")
            value_idx = value_dict[value]
            
            # 최소 정보만 저장: 델타 위치(2 bytes, uint16) + 값 인덱스(1 byte)
            # 짧은 텍스트에서는 위치가 작으므로 uint16으로 충분
            binary_data.extend(struct.pack("<HB", delta_position, value_idx))
        
        return bytes(binary_data)
    
    def _decompress_minimal(self, binary_data: bytes) -> Dict[str, Dict[str, Any]]:
        """
        최소 메타데이터 복원
        """
        if len(binary_data) < 2:
            return {}
        
        tag_count = struct.unpack("H", binary_data[:2])[0]
        if tag_count == 0:
            return {}
        
        anchor_tags = {}
        offset = 2
        prev_position = 0
        
        # 1단계: 값 사전 읽기 (바이너리 형식, 먼저 저장되었으므로 먼저 읽음)
        if offset + 4 > len(binary_data):
            return {}
        
        value_count = struct.unpack("H", binary_data[offset:offset+2])[0]
        offset += 2
        
        value_dict_size = struct.unpack("H", binary_data[offset:offset+2])[0]
        offset += 2
        
        if offset + value_dict_size > len(binary_data):
            return {}
        
        value_dict_bytes = binary_data[offset:offset+value_dict_size]
        value_dict = self._decode_value_dict_binary(value_dict_bytes, value_count)
        reverse_value_dict = value_dict  # 이미 인덱스 -> 값 매핑
        offset += value_dict_size
        
        # 2단계: 태그 데이터 복원
        for i in range(tag_count):
            if offset + 3 > len(binary_data):
                break
            
            delta_position, value_idx = struct.unpack("<HB", binary_data[offset:offset+3])
            offset += 3
            
            current_position = prev_position + delta_position
            prev_position = current_position
            
            value = reverse_value_dict.get(value_idx, "")
            
            # 태그 재구성 (타입 추론)
            tag_type = self._infer_tag_type(value)
            tag = f"[{tag_type}{i+1}]"
            
            anchor_tags[tag] = {
                "type": tag_type,
                "value": value,
                "original_start": current_position,
                "original_end": current_position + len(value)
            }
        
        return anchor_tags
    
    def _encode_value_dict_binary(self, value_dict: Dict[str, int]) -> bytes:
        """
        값 사전을 바이너리 형식으로 인코딩 (JSON 대신)
        
        형식:
        - 각 값: 길이(1 byte) + 값(bytes)
        - 짧은 값(1-2 bytes)은 직접 저장
        """
        binary_data = bytearray()
        
        # 값 사전을 인덱스 순서로 정렬
        sorted_values = sorted(value_dict.items(), key=lambda x: x[1])
        
        for value, idx in sorted_values:
            value_bytes = value.encode('utf-8')
            value_len = len(value_bytes)
            
            # 길이 제한: 1 byte (최대 255 bytes)
            if value_len > 255:
                # 긴 값은 잘라서 저장 (실제로는 짧은 텍스트에서 발생하지 않음)
                value_bytes = value_bytes[:255]
                value_len = 255
            
            # 길이(1 byte) + 값(bytes)
            binary_data.append(value_len)
            binary_data.extend(value_bytes)
        
        return bytes(binary_data)
    
    def _decode_value_dict_binary(self, binary_data: bytes, count: int) -> Dict[int, str]:
        """
        바이너리 형식의 값 사전 디코딩
        """
        value_dict = {}
        offset = 0
        idx = 0
        
        while idx < count and offset < len(binary_data):
            if offset + 1 > len(binary_data):
                break
            
            value_len = binary_data[offset]
            offset += 1
            
            if offset + value_len > len(binary_data):
                break
            
            value_bytes = binary_data[offset:offset+value_len]
            value = value_bytes.decode('utf-8')
            value_dict[idx] = value
            
            offset += value_len
            idx += 1
        
        return value_dict
    
    def _infer_tag_type(self, value: str) -> str:
        """
        값으로부터 태그 타입 추론
        """
        if value in [".", "!", "?", ":", ";"]:
            return "DOT"
        elif value in ["(", ")", "[", "]", "{", "}"]:
            return "PAREN"
        elif value.isdigit():
            return "N"
        elif any('\u4e00' <= char <= '\u9fff' for char in value):
            return "HANJA"
        else:
            return "VAL"
    
    def _compress_standard(self, anchor_tags: Dict[str, Dict[str, Any]]) -> bytes:
        """
        표준 압축 (기존 방식)
        """
        if self.base_minimizer:
            return self.base_minimizer.compress_anchor_tags(anchor_tags)
        else:
            # 폴백: JSON 압축
            return json.dumps(anchor_tags, ensure_ascii=False).encode('utf-8')
    
    def _compress_maximum(self, anchor_tags: Dict[str, Dict[str, Any]]) -> bytes:
        """
        최대 압축 (긴 텍스트용)
        
        전략:
        - 값 사전 기반 중복 제거
        - 허프만 코딩 (빈도 기반)
        - 더 공격적인 델타 인코딩
        """
        if not anchor_tags:
            return struct.pack("H", 0)
        
        sorted_tags = sorted(
            anchor_tags.items(),
            key=lambda x: x[1].get("original_start", 0)
        )
        
        # 값 빈도 계산
        value_freq = {}
        for tag, tag_data in sorted_tags:
            value = tag_data.get("value", "")
            value_freq[value] = value_freq.get(value, 0) + 1
        
        # 빈도순 정렬 (허프만 코딩 준비)
        sorted_values = sorted(value_freq.items(), key=lambda x: x[1], reverse=True)
        value_dict = {val: idx for idx, (val, _) in enumerate(sorted_values)}
        
        binary_data = bytearray()
        binary_data.extend(struct.pack("H", len(sorted_tags)))
        
        prev_position = 0
        
        for tag, tag_data in sorted_tags:
            current_position = tag_data.get("original_start", 0)
            delta_position = current_position - prev_position
            prev_position = current_position
            
            value = tag_data.get("value", "")
            value_idx = value_dict.get(value, 0)
            
            # 최적화된 패킹: 델타 위치(4 bytes) + 값 인덱스(2 bytes, uint16)
            binary_data.extend(struct.pack("<IH", delta_position, value_idx))
        
        # 값 사전 저장
        value_dict_bytes = json.dumps(value_dict, ensure_ascii=False).encode('utf-8')
        binary_data.extend(struct.pack("I", len(value_dict_bytes)))
        binary_data.extend(value_dict_bytes)
        
        return bytes(binary_data)
    
    def compress_adaptive(
        self,
        anchor_tags: Dict[str, Dict[str, Any]],
        text_size: int,
        current_metadata_size: int,
        use_nitro_sync: bool = True
    ) -> bytes:
        """
        적응형 압축 (텍스트 길이에 따라 전략 변경)
        
        Args:
            anchor_tags: 앵커 태그 딕셔너리
            text_size: 원본 텍스트 크기 (bytes)
            current_metadata_size: 현재 메타데이터 크기 (bytes)
            use_nitro_sync: Nitro Sync 사용 여부 (기본값: True)
        
        Returns:
            압축된 바이너리 데이터
        """
        strategy = self._determine_strategy(text_size, current_metadata_size)
        
        # Nitro Sync 사용 (긴 텍스트에서 특히 효과적)
        if use_nitro_sync:
            try:
                from src.optimization.nitro_sync import NitroSync
                nitro_sync = NitroSync(use_flatbuffers=False)
                
                # 전략에 따라 압축 레벨 결정
                if strategy == "minimal":
                    compression_level = "minimal"
                elif strategy == "maximum":
                    compression_level = "maximum"
                else:
                    compression_level = "standard"
                
                nitro_result = nitro_sync.encode_metadata(anchor_tags, text_size, compression_level)
                
                # 기존 방식과 비교하여 더 작은 것 선택
                if strategy == "minimal":
                    base_result = self._compress_minimal(anchor_tags)
                elif strategy == "maximum":
                    base_result = self._compress_maximum(anchor_tags)
                else:
                    base_result = self._compress_standard(anchor_tags)
                
                # 더 작은 크기 선택
                if len(nitro_result) < len(base_result):
                    logger.debug(f"✅ Nitro Sync 선택: {len(nitro_result)} bytes < {len(base_result)} bytes")
                    return nitro_result
                else:
                    logger.debug(f"✅ 기존 방식 선택: {len(base_result)} bytes <= {len(nitro_result)} bytes")
                    return base_result
            except ImportError as e:
                # Nitro Sync를 사용할 수 없으면 기존 방식 사용
                logger.debug(f"⚠️ Nitro Sync 사용 불가: {e}, 기존 방식 사용")
                pass
        
        # 기존 방식
        if strategy == "minimal":
            return self._compress_minimal(anchor_tags)
        elif strategy == "maximum":
            return self._compress_maximum(anchor_tags)
        else:
            return self._compress_standard(anchor_tags)
    
    def estimate_savings(
        self,
        anchor_tags: Dict[str, Dict[str, Any]],
        text_size: int,
        current_metadata_size: int
    ) -> Dict[str, Any]:
        """
        압축 개선 효과 추정
        
        Returns:
            개선 효과 정보
        """
        strategy = self._determine_strategy(text_size, current_metadata_size)
        
        # 기존 방식 크기
        if self.base_minimizer:
            standard_size = len(self.base_minimizer.compress_anchor_tags(anchor_tags))
        else:
            standard_size = len(json.dumps(anchor_tags, ensure_ascii=False).encode('utf-8'))
        
        # 적응형 압축 크기
        adaptive_size = len(self.compress_adaptive(anchor_tags, text_size, current_metadata_size))
        
        savings = standard_size - adaptive_size
        savings_ratio = (savings / standard_size * 100) if standard_size > 0 else 0
        
        return {
            "strategy": strategy,
            "standard_size": standard_size,
            "adaptive_size": adaptive_size,
            "savings": savings,
            "savings_ratio": savings_ratio,
            "text_size": text_size,
            "current_metadata_size": current_metadata_size
        }

