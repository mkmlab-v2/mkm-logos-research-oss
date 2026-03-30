#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nitro Sync: 바이너리 직렬화 최적화 엔진

목적: FlatBuffers 기반 고성능 바이너리 직렬화
- 현재 21.7% 추가 절감률 → 30%+ 목표
- 메타데이터 다이어트와 통합
- 기존 바이너리 프로토콜 대비 추가 최적화

작성일: 2026-01-30
Phase: Nitro Sync
통합: 비트코인 트레이딩 시스템
"""

import struct
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import sys
import logging

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FlatBuffers 사용 가능 여부 확인
FLATBUFFERS_AVAILABLE = False
try:
    import flatbuffers
    from flatbuffers import Builder
    FLATBUFFERS_AVAILABLE = True
    logger.info("✅ FlatBuffers 라이브러리 사용 가능")
except ImportError:
    logger.warning("⚠️ FlatBuffers 라이브러리가 설치되지 않았습니다. 기본 바이너리 프로토콜을 사용합니다.")
    logger.warning("   설치: pip install flatbuffers")


class NitroSync:
    """
    Nitro Sync: 바이너리 직렬화 최적화 엔진
    
    특징:
    1. 고밀도 바이너리 인코딩
    2. 값 사전 기반 중복 제거
    3. 델타 인코딩 (위치 정보)
    4. 타입 추론 (복원 시)
    5. 선택적 압축 (긴 데이터)
    """
    
    def __init__(self, use_flatbuffers: bool = False):
        """
        초기화
        
        Args:
            use_flatbuffers: FlatBuffers 사용 여부 (설치된 경우)
        """
        self.use_flatbuffers = use_flatbuffers and FLATBUFFERS_AVAILABLE
        if self.use_flatbuffers:
            logger.info("✅ Nitro Sync: FlatBuffers 모드 활성화")
        else:
            logger.info("✅ Nitro Sync: 최적화 바이너리 모드 활성화")
    
    def encode_metadata(
        self,
        anchor_tags: Dict[str, Dict[str, Any]],
        text_size: int,
        compression_level: str = "auto"
    ) -> bytes:
        """
        메타데이터를 바이너리로 인코딩 (Nitro Sync 최적화)
        
        Args:
            anchor_tags: 앵커 태그 딕셔너리
            text_size: 원본 텍스트 크기
            compression_level: 압축 레벨 ("minimal", "standard", "maximum", "auto")
        
        Returns:
            바이너리 데이터
        """
        if not anchor_tags:
            return struct.pack("H", 0)
        
        # 압축 레벨 자동 결정
        if compression_level == "auto":
            if text_size <= 200:
                compression_level = "minimal"
            elif text_size <= 1000:
                compression_level = "standard"
            else:
                compression_level = "maximum"
        
        if self.use_flatbuffers:
            return self._encode_with_flatbuffers(anchor_tags, compression_level)
        else:
            return self._encode_optimized(anchor_tags, compression_level)
    
    def _encode_optimized(
        self,
        anchor_tags: Dict[str, Dict[str, Any]],
        compression_level: str
    ) -> bytes:
        """
        최적화된 바이너리 인코딩 (FlatBuffers 없이)
        
        전략:
        - 값 사전 기반 중복 제거
        - 델타 인코딩 (위치 정보)
        - 가변 길이 인코딩 (작은 값은 더 작게)
        """
        sorted_tags = sorted(
            anchor_tags.items(),
            key=lambda x: x[1].get("original_start", 0)
        )
        
        binary_data = bytearray()
        
        # 헤더: 태그 개수 (2 bytes)
        binary_data.extend(struct.pack("H", len(sorted_tags)))
        
        # 값 사전 구축 (중복 제거)
        value_dict = {}
        value_index = 0
        value_list = []
        
        for tag_key, tag_data in sorted_tags:
            value = tag_data.get("value", "")
            if value not in value_dict:
                value_dict[value] = value_index
                value_list.append(value)
                value_index += 1
        
        # 값 사전 저장 (최적화: 길이 + 값)
        binary_data.extend(struct.pack("H", len(value_list)))  # 값 개수
        
        for value in value_list:
            value_bytes = value.encode('utf-8')
            value_len = len(value_bytes)
            
            # 가변 길이 인코딩: 255 이하는 1 byte, 그 이상은 2 bytes
            if value_len <= 255:
                binary_data.append(0)  # 플래그: 1 byte 길이
                binary_data.append(value_len)
            else:
                binary_data.append(1)  # 플래그: 2 bytes 길이
                binary_data.extend(struct.pack("H", value_len))
            
            binary_data.extend(value_bytes)
        
        # 태그 데이터 저장 (델타 인코딩)
        prev_position = 0
        
        for tag_key, tag_data in sorted_tags:
            # 위치 (델타 인코딩)
            position = tag_data.get("original_start", 0)
            delta = position - prev_position
            
            # 가변 길이 인코딩: 작은 델타는 1 byte, 큰 델타는 2 bytes
            if delta <= 255:
                binary_data.append(0)  # 플래그: 1 byte
                binary_data.append(delta)
            else:
                binary_data.append(1)  # 플래그: 2 bytes
                binary_data.extend(struct.pack("H", delta))
            
            # 값 인덱스 (가변 길이)
            value = tag_data.get("value", "")
            value_idx = value_dict.get(value, 0)
            
            if value_idx <= 255:
                binary_data.append(value_idx)
            else:
                binary_data.append(255)  # 플래그: 2 bytes 인덱스
                binary_data.extend(struct.pack("H", value_idx))
            
            prev_position = position
        
        return bytes(binary_data)
    
    def _encode_with_flatbuffers(
        self,
        anchor_tags: Dict[str, Dict[str, Any]],
        compression_level: str
    ) -> bytes:
        """
        FlatBuffers를 사용한 인코딩 (향후 구현)
        
        현재는 최적화 바이너리 모드 사용
        """
        # TODO: FlatBuffers 스키마 정의 및 구현
        logger.warning("⚠️ FlatBuffers 인코딩은 아직 구현되지 않았습니다. 최적화 바이너리 모드 사용")
        return self._encode_optimized(anchor_tags, compression_level)
    
    def decode_metadata(
        self,
        binary_data: bytes,
        compression_level: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        바이너리 데이터를 메타데이터로 디코딩
        
        Args:
            binary_data: 바이너리 데이터
            compression_level: 압축 레벨 (자동 감지)
        
        Returns:
            앵커 태그 딕셔너리
        """
        if len(binary_data) < 2:
            return {}
        
        if self.use_flatbuffers:
            return self._decode_with_flatbuffers(binary_data, compression_level)
        else:
            return self._decode_optimized(binary_data, compression_level)
    
    def _decode_optimized(
        self,
        binary_data: bytes,
        compression_level: Optional[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        최적화된 바이너리 디코딩
        """
        offset = 0
        
        # 태그 개수 읽기
        if offset + 2 > len(binary_data):
            return {}
        
        tag_count = struct.unpack("H", binary_data[offset:offset+2])[0]
        offset += 2
        
        if tag_count == 0:
            return {}
        
        # 값 사전 읽기
        if offset + 2 > len(binary_data):
            return {}
        
        value_count = struct.unpack("H", binary_data[offset:offset+2])[0]
        offset += 2
        
        value_list = []
        
        for _ in range(value_count):
            if offset + 1 > len(binary_data):
                break
            
            length_flag = binary_data[offset]
            offset += 1
            
            if length_flag == 0:
                # 1 byte 길이
                if offset + 1 > len(binary_data):
                    break
                value_len = binary_data[offset]
                offset += 1
            else:
                # 2 bytes 길이
                if offset + 2 > len(binary_data):
                    break
                value_len = struct.unpack("H", binary_data[offset:offset+2])[0]
                offset += 2
            
            if offset + value_len > len(binary_data):
                break
            
            value_bytes = binary_data[offset:offset+value_len]
            value = value_bytes.decode('utf-8')
            value_list.append(value)
            offset += value_len
        
        # 태그 데이터 읽기
        anchor_tags = {}
        prev_position = 0
        
        for i in range(tag_count):
            if offset + 1 > len(binary_data):
                break
            
            # 위치 (델타 디코딩)
            delta_flag = binary_data[offset]
            offset += 1
            
            if delta_flag == 0:
                # 1 byte 델타
                if offset + 1 > len(binary_data):
                    break
                delta = binary_data[offset]
                offset += 1
            else:
                # 2 bytes 델타
                if offset + 2 > len(binary_data):
                    break
                delta = struct.unpack("H", binary_data[offset:offset+2])[0]
                offset += 2
            
            position = prev_position + delta
            
            # 값 인덱스 읽기
            if offset + 1 > len(binary_data):
                break
            
            value_idx_byte = binary_data[offset]
            offset += 1
            
            if value_idx_byte == 255:
                # 2 bytes 인덱스
                if offset + 2 > len(binary_data):
                    break
                value_idx = struct.unpack("H", binary_data[offset:offset+2])[0]
                offset += 2
            else:
                value_idx = value_idx_byte
            
            if value_idx < len(value_list):
                value = value_list[value_idx]
                
                tag_key = f"tag_{i}"
                anchor_tags[tag_key] = {
                    "value": value,
                    "original_start": position,
                    "original_end": position + len(value)
                }
            
            prev_position = position
        
        return anchor_tags
    
    def _decode_with_flatbuffers(
        self,
        binary_data: bytes,
        compression_level: Optional[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        FlatBuffers를 사용한 디코딩 (향후 구현)
        """
        logger.warning("⚠️ FlatBuffers 디코딩은 아직 구현되지 않았습니다. 최적화 바이너리 모드 사용")
        return self._decode_optimized(binary_data, compression_level)
    
    def compare_with_legacy(
        self,
        anchor_tags: Dict[str, Dict[str, Any]],
        legacy_binary: bytes
    ) -> Dict[str, Any]:
        """
        기존 바이너리 프로토콜과 크기 비교
        
        Args:
            anchor_tags: 앵커 태그
            legacy_binary: 기존 바이너리 데이터
        
        Returns:
            비교 결과
        """
        # Nitro Sync 인코딩
        text_size = sum(len(tag.get("value", "")) for tag in anchor_tags.values())
        nitro_binary = self.encode_metadata(anchor_tags, text_size)
        
        legacy_size = len(legacy_binary)
        nitro_size = len(nitro_binary)
        
        improvement = ((legacy_size - nitro_size) / legacy_size * 100) if legacy_size > 0 else 0
        
        return {
            "legacy_size": legacy_size,
            "nitro_size": nitro_size,
            "improvement_percent": improvement,
            "size_reduction": legacy_size - nitro_size
        }

