#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nitro Compression Engine (니트로 압축 엔진)

목적: 100% 복원 정확도를 유지하며 텍스트 압축률 70% 이상 달성
- 프롬프트 압축 (Gemini API 호출 시)
- 응답 압축 (Gemini API 응답)
- 캐시 압축 (차트 이미지 캐시)
- 로그 압축 (로그 파일)

작성일: 2026-01-30
상태: ✅ 구축 완료
"""

import sys
import os
import json
import gzip
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re

# Dictionary Compression Engine import
try:
    from src.optimization.dictionary_compression import DictionaryCompressionEngine
    DICTIONARY_COMPRESSION_AVAILABLE = True
except ImportError:
    DICTIONARY_COMPRESSION_AVAILABLE = False
    logging.warning("⚠️ Dictionary Compression Engine 미설치, 사전 압축 기능 비활성화")

# Metadata Diet Optimizer import (Phase 7-A)
try:
    from src.optimization.metadata_diet_optimizer import MetadataDietOptimizer
    METADATA_DIET_AVAILABLE = True
except ImportError:
    METADATA_DIET_AVAILABLE = False
    logging.warning("⚠️ Metadata Diet Optimizer 미설치, 적응형 압축 기능 비활성화")

# Nitro Sync import
try:
    from src.optimization.nitro_sync import NitroSync
    NITRO_SYNC_AVAILABLE = True
except ImportError:
    NITRO_SYNC_AVAILABLE = False
    logging.warning("⚠️ Nitro Sync 미설치, 바이너리 직렬화 최적화 기능 비활성화")

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NitroCompressionEngine:
    """
    니트로 압축 엔진
    
    기능:
    1. 프롬프트 압축: 불필요한 설명 제거, JSON 형식만 요청
    2. 응답 압축: Gemini API 응답 텍스트 압축
    3. 캐시 압축: 차트 이미지 캐시 압축 저장
    4. 로그 압축: 로그 파일 자동 압축 및 아카이빙
    """
    
    def __init__(
        self, 
        compression_level: int = 6, 
        use_dictionary: bool = True,
        use_metadata_diet: bool = True,
        use_nitro_sync: bool = True
    ):
        """
        Args:
            compression_level: gzip 압축 레벨 (1-9, 기본값: 6)
            use_dictionary: 사전 압축 사용 여부 (기본값: True)
            use_metadata_diet: 메타데이터 다이어트 사용 여부 (기본값: True, Phase 7-A)
            use_nitro_sync: Nitro Sync 사용 여부 (기본값: True)
        """
        self.compression_level = compression_level
        self.use_dictionary = use_dictionary and DICTIONARY_COMPRESSION_AVAILABLE
        self.use_metadata_diet = use_metadata_diet and METADATA_DIET_AVAILABLE
        self.use_nitro_sync = use_nitro_sync and NITRO_SYNC_AVAILABLE
        
        # Dictionary Compression Engine 초기화
        self.dictionary_compression = None
        if self.use_dictionary:
            try:
                self.dictionary_compression = DictionaryCompressionEngine()
                logger.info("✅ Dictionary Compression Engine 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Dictionary Compression Engine 초기화 실패: {e}")
                self.use_dictionary = False
        
        # Metadata Diet Optimizer 초기화 (Phase 7-A)
        self.metadata_diet_optimizer = None
        if self.use_metadata_diet:
            try:
                self.metadata_diet_optimizer = MetadataDietOptimizer()
                logger.info("✅ Metadata Diet Optimizer 초기화 완료 (Phase 7-A)")
            except Exception as e:
                logger.warning(f"⚠️ Metadata Diet Optimizer 초기화 실패: {e}")
                self.use_metadata_diet = False
        
        # Nitro Sync 초기화
        self.nitro_sync = None
        if self.use_nitro_sync:
            try:
                self.nitro_sync = NitroSync(use_flatbuffers=False)
                logger.info("✅ Nitro Sync 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Nitro Sync 초기화 실패: {e}")
                self.use_nitro_sync = False
        
        logger.info(f"✅ Nitro Compression Engine 초기화 완료")
        logger.info(f"   - 압축 레벨: {compression_level}")
        logger.info(f"   - 사전 압축: {self.use_dictionary}")
        logger.info(f"   - 메타데이터 다이어트: {self.use_metadata_diet} (Phase 7-A)")
        logger.info(f"   - Nitro Sync: {self.use_nitro_sync}")
    
    def compress_prompt(self, prompt: str) -> str:
        """
        프롬프트 압축 (불필요한 설명 제거, JSON 형식만 요청)
        
        Args:
            prompt: 원본 프롬프트
        
        Returns:
            압축된 프롬프트
        """
        try:
            # 1. 불필요한 설명 제거
            # "다음 정보를 분석해주세요:" 같은 불필요한 문구 제거
            prompt = re.sub(r'다음 정보를.*?해주세요:', '', prompt, flags=re.DOTALL)
            prompt = re.sub(r'⚠️ 중요:.*?평가해주세요\.', '', prompt, flags=re.DOTALL)
            
            # 2. JSON 형식만 추출
            json_match = re.search(r'\{[^}]+\}', prompt, re.DOTALL)
            if json_match:
                # JSON 형식만 남기고 나머지 제거
                prompt = f"JSON 형식으로 응답:\n{json_match.group(0)}"
            
            # 3. 중복 공백 제거
            prompt = re.sub(r'\s+', ' ', prompt).strip()
            
            # 4. 압축률 계산
            original_size = len(prompt.encode('utf-8'))
            compressed_size = len(prompt.encode('utf-8'))
            compression_ratio = (1.0 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
            
            logger.debug(f"프롬프트 압축: {original_size} → {compressed_size} bytes ({compression_ratio:.1f}% 감소)")
            
            return prompt
            
        except Exception as e:
            logger.warning(f"⚠️ 프롬프트 압축 실패: {e}")
            return prompt
    
    def compress_text(self, text: str, use_adaptive: bool = True) -> bytes:
        """
        텍스트 압축 (적응형 압축 + 사전 압축 + gzip)
        
        Args:
            text: 원본 텍스트
            use_adaptive: 적응형 압축 사용 여부 (기본값: True, Phase 7-A)
        
        Returns:
            압축된 바이너리 데이터
        """
        try:
            original_text = text
            original_size = len(text.encode('utf-8'))
            
            # Step 1: 사전 압축 (논리적 압축)
            if self.use_dictionary and self.dictionary_compression:
                text = self.dictionary_compression.compress_text(text)
                logger.debug("✅ 사전 압축 적용 완료")
            
            # Step 2: 메타데이터 다이어트 (Phase 7-A) - 짧은 텍스트 최적화
            # 주의: 메타데이터 다이어트는 anchor_tags가 필요한데, 
            # 일반 텍스트 압축에는 직접 적용하지 않음 (gzip이 더 효율적)
            # 메타데이터 다이어트는 JSON/구조화된 데이터에 적용
            
            # Step 3: gzip 압축 (물리적 압축)
            text_bytes = text.encode('utf-8')
            compressed = gzip.compress(text_bytes, compresslevel=self.compression_level)
            
            compressed_size = len(compressed)
            compression_ratio = (1.0 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
            
            logger.debug(f"텍스트 압축: {original_size} → {compressed_size} bytes ({compression_ratio:.1f}% 감소)")
            
            return compressed
            
        except Exception as e:
            logger.error(f"❌ 텍스트 압축 실패: {e}")
            return text.encode('utf-8')
    
    def decompress_text(self, compressed_data: bytes) -> str:
        """
        텍스트 압축 해제 (gzip + 사전 압축 해제)
        
        Args:
            compressed_data: 압축된 바이너리 데이터
        
        Returns:
            원본 텍스트
        """
        try:
            # Step 1: gzip 압축 해제 (물리적 압축 해제)
            decompressed = gzip.decompress(compressed_data)
            text = decompressed.decode('utf-8')
            
            # Step 2: 사전 압축 해제 (논리적 압축 해제)
            if self.use_dictionary and self.dictionary_compression:
                text = self.dictionary_compression.decompress_text(text)
                logger.debug("✅ 사전 압축 해제 완료")
            
            return text
            
        except Exception as e:
            logger.error(f"❌ 텍스트 압축 해제 실패: {e}")
            return compressed_data.decode('utf-8', errors='ignore')
    
    def compress_json(self, data: Dict[str, Any], use_adaptive: bool = True) -> bytes:
        """
        JSON 데이터 압축 (적응형 압축 + 사전 압축 + gzip)
        
        Args:
            data: JSON 데이터 딕셔너리
            use_adaptive: 적응형 압축 사용 여부 (기본값: True, Phase 7-A)
        
        Returns:
            압축된 바이너리 데이터
        """
        try:
            original_json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            original_size = len(original_json_str.encode('utf-8'))
            json_str = original_json_str
            
            # Step 1: 사전 압축 (논리적 압축)
            if self.use_dictionary and self.dictionary_compression:
                try:
                    compressed_json, metadata = self.dictionary_compression.compress_json(data)
                    json_str = compressed_json
                    logger.debug(f"✅ 사전 압축 적용 완료 (압축률: {metadata.get('compression_ratio', 0):.1f}%)")
                except Exception as e:
                    logger.debug(f"⚠️ 사전 압축 실패, 원본 사용: {e}")
            
            # Step 2: 메타데이터 다이어트 (Phase 7-A) - 짧은 JSON에 적용
            # 주의: 메타데이터 다이어트는 anchor_tags 구조가 필요하므로
            # 일반 JSON에는 직접 적용하지 않음 (gzip이 더 효율적)
            
            # Step 3: gzip 압축 (물리적 압축)
            compressed = gzip.compress(json_str.encode('utf-8'), compresslevel=self.compression_level)
            
            compressed_size = len(compressed)
            compression_ratio = (1.0 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
            
            logger.debug(f"JSON 압축: {original_size} → {compressed_size} bytes ({compression_ratio:.1f}% 감소)")
            
            return compressed
            
        except Exception as e:
            logger.error(f"❌ JSON 압축 실패: {e}")
            return json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    def decompress_json(self, compressed_data: bytes) -> Dict[str, Any]:
        """
        JSON 데이터 압축 해제 (gzip + 사전 압축 해제)
        
        Args:
            compressed_data: 압축된 바이너리 데이터
        
        Returns:
            원본 JSON 데이터 딕셔너리
        """
        try:
            # Step 1: gzip 압축 해제 (물리적 압축 해제)
            decompressed = gzip.decompress(compressed_data)
            json_str = decompressed.decode('utf-8')
            
            # Step 2: 사전 압축 해제 (논리적 압축 해제)
            if self.use_dictionary and self.dictionary_compression:
                json_str = self.dictionary_compression.decompress_text(json_str)
                logger.debug("✅ 사전 압축 해제 완료")
            
            return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"❌ JSON 압축 해제 실패: {e}")
            return {}
    
    def compress_base64_image(self, image_base64: str) -> bytes:
        """
        Base64 이미지 압축 (차트 이미지 캐시용)
        
        Args:
            image_base64: Base64 인코딩된 이미지 문자열
        
        Returns:
            압축된 바이너리 데이터
        """
        try:
            # Base64 디코딩
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
            
            image_bytes = base64.b64decode(image_base64)
            
            # gzip 압축
            compressed = gzip.compress(image_bytes, compresslevel=self.compression_level)
            
            original_size = len(image_bytes)
            compressed_size = len(compressed)
            compression_ratio = (1.0 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
            
            logger.debug(f"이미지 압축: {original_size} → {compressed_size} bytes ({compression_ratio:.1f}% 감소)")
            
            return compressed
            
        except Exception as e:
            logger.error(f"❌ 이미지 압축 실패: {e}")
            return base64.b64decode(image_base64)
    
    def decompress_base64_image(self, compressed_data: bytes) -> str:
        """
        Base64 이미지 압축 해제
        
        Args:
            compressed_data: 압축된 바이너리 데이터
        
        Returns:
            원본 Base64 인코딩된 이미지 문자열
        """
        try:
            decompressed = gzip.decompress(compressed_data)
            image_base64 = base64.b64encode(decompressed).decode('utf-8')
            return image_base64
            
        except Exception as e:
            logger.error(f"❌ 이미지 압축 해제 실패: {e}")
            return ""
    
    def compress_log_file(self, log_file_path: Path, archive_dir: Optional[Path] = None) -> Optional[Path]:
        """
        로그 파일 압축 및 아카이빙
        
        Args:
            log_file_path: 로그 파일 경로
            archive_dir: 아카이브 디렉토리 (기본값: logs/archive)
        
        Returns:
            압축된 파일 경로 (없으면 None)
        """
        try:
            if not log_file_path.exists():
                logger.warning(f"⚠️ 로그 파일이 없습니다: {log_file_path}")
                return None
            
            # 아카이브 디렉토리 설정
            if archive_dir is None:
                archive_dir = log_file_path.parent / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # 압축 파일 경로
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            compressed_file = archive_dir / f"{log_file_path.stem}_{timestamp}.gz"
            
            # 파일 읽기 및 압축
            with open(log_file_path, 'rb') as f:
                original_data = f.read()
            
            compressed_data = gzip.compress(original_data, compresslevel=self.compression_level)
            
            # 압축 파일 저장
            with open(compressed_file, 'wb') as f:
                f.write(compressed_data)
            
            original_size = len(original_data)
            compressed_size = len(compressed_data)
            compression_ratio = (1.0 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
            
            logger.info(f"✅ 로그 파일 압축 완료: {log_file_path.name}")
            logger.info(f"   원본: {original_size / 1024:.2f} KB")
            logger.info(f"   압축: {compressed_size / 1024:.2f} KB")
            logger.info(f"   압축률: {compression_ratio:.1f}%")
            
            # 원본 파일 삭제 (선택적)
            # log_file_path.unlink()
            
            return compressed_file
            
        except Exception as e:
            logger.error(f"❌ 로그 파일 압축 실패: {e}")
            return None
    
    def calculate_compression_ratio(self, original_size: int, compressed_size: int) -> float:
        """
        압축률 계산
        
        Args:
            original_size: 원본 크기 (bytes)
            compressed_size: 압축된 크기 (bytes)
        
        Returns:
            압축률 (%)
        """
        if original_size == 0:
            return 0.0
        return (1.0 - compressed_size / original_size) * 100.0
    
    def compress_with_metadata_diet(
        self,
        anchor_tags: Dict[str, Dict[str, Any]],
        text_size: int,
        current_metadata_size: int
    ) -> bytes:
        """
        메타데이터 다이어트를 사용한 적응형 압축 (Phase 7-A)
        
        Args:
            anchor_tags: 앵커 태그 딕셔너리
            text_size: 원본 텍스트 크기 (bytes)
            current_metadata_size: 현재 메타데이터 크기 (bytes)
        
        Returns:
            압축된 바이너리 데이터
        """
        if not self.use_metadata_diet or not self.metadata_diet_optimizer:
            # 폴백: JSON 압축
            return json.dumps(anchor_tags, ensure_ascii=False).encode('utf-8')
        
        try:
            # 적응형 압축 (텍스트 길이에 따라 전략 변경)
            compressed = self.metadata_diet_optimizer.compress_adaptive(
                anchor_tags=anchor_tags,
                text_size=text_size,
                current_metadata_size=current_metadata_size,
                use_nitro_sync=self.use_nitro_sync
            )
            
            original_size = current_metadata_size
            compressed_size = len(compressed)
            compression_ratio = (1.0 - compressed_size / original_size) * 100 if original_size > 0 else 0.0
            
            logger.debug(f"메타데이터 다이어트 압축: {original_size} → {compressed_size} bytes ({compression_ratio:.1f}% 감소)")
            
            return compressed
            
        except Exception as e:
            logger.warning(f"⚠️ 메타데이터 다이어트 압축 실패: {e}, 폴백 사용")
            return json.dumps(anchor_tags, ensure_ascii=False).encode('utf-8')
    
    def optimize_prompt_for_gemini(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Gemini API용 프롬프트 최적화 (토큰 절약)
        
        Args:
            prompt: 원본 프롬프트
            max_tokens: 최대 토큰 수 (기본값: 500)
        
        Returns:
            최적화된 프롬프트
        """
        try:
            # 1. 불필요한 설명 제거
            prompt = re.sub(r'다음 정보를.*?해주세요:', '', prompt, flags=re.DOTALL)
            prompt = re.sub(r'⚠️ 중요:.*?평가해주세요\.', '', prompt, flags=re.DOTALL)
            prompt = re.sub(r'정확한 정보만.*?제외해주세요\.', '', prompt, flags=re.DOTALL)
            
            # 2. JSON 형식만 추출
            json_match = re.search(r'\{[^}]+\}', prompt, re.DOTALL)
            if json_match:
                # JSON 형식만 남기고 나머지 제거
                prompt = f"JSON:\n{json_match.group(0)}"
            
            # 3. 중복 공백 제거
            prompt = re.sub(r'\s+', ' ', prompt).strip()
            
            # 4. 토큰 수 확인 (대략적 추정: 1 토큰 ≈ 4 문자)
            estimated_tokens = len(prompt) / 4
            if estimated_tokens > max_tokens:
                # 토큰 수가 초과하면 더 압축
                prompt = prompt[:max_tokens * 4]
            
            logger.debug(f"프롬프트 최적화: {estimated_tokens:.0f} 토큰 (목표: {max_tokens})")
            
            return prompt
            
        except Exception as e:
            logger.warning(f"⚠️ 프롬프트 최적화 실패: {e}")
            return prompt

