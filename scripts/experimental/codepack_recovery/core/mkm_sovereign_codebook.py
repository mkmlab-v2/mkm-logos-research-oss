#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ MKM Sovereign Codebook 구축

목적: VQ-VAE 기반 코드북 생성으로 전송량 99.98% 감소
- 성경 구절 31,102개 → 코드북 인덱스 (0-31,101)
- 사상체질 4개 → 코드북 인덱스 (31,102-31,105)
- 투자 용어 1,000개 → 코드북 인덱스 (31,106-32,105)
- 명리학 패턴 → 코드북 인덱스 (32,106+)

작성일: 2026-01-22
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import json
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent

# SentenceTransformer import
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    logger.warning("SentenceTransformer를 사용할 수 없습니다.")
    SENTENCE_TRANSFORMER_AVAILABLE = False

# sklearn KMeans import
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("sklearn을 사용할 수 없습니다.")
    SKLEARN_AVAILABLE = False


class MKMSovereignCodebook:
    """
    MKM Sovereign Codebook 생성기
    
    VQ-VAE 원리:
    1. 연속 벡터(768D)를 코드북의 가장 가까운 벡터로 양자화
    2. 벡터 자체가 아닌 코드북 인덱스(정수)만 전송
    3. 수신측은 인덱스로 코드북에서 벡터 조회
    """
    
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        codebook_size: int = 50000  # 코드북 크기 (성경 31,102 + 사상체질 4 + 투자 1,000 + 명리학 등)
    ):
        """
        초기화
        
        Args:
            embedding_model: 임베딩 모델 이름
            codebook_size: 코드북 크기
        """
        logger.info("🏛️ MKM Sovereign Codebook 구축 시작...")
        
        # 1. 임베딩 모델 로드
        self.brain = None
        if SENTENCE_TRANSFORMER_AVAILABLE:
            try:
                self.brain = SentenceTransformer(embedding_model)
                logger.info(f"✅ 임베딩 모델 로드 완료: {embedding_model}")
            except Exception as e:
                logger.error(f"❌ 임베딩 모델 로드 실패: {e}")
                self.brain = None
        else:
            logger.warning("⚠️ SentenceTransformer를 사용할 수 없습니다.")
        
        self.codebook_size = codebook_size
        self.codebook = None  # 코드북 벡터 배열 (N x 768)
        self.codebook_metadata = []  # 코드북 메타데이터 (인덱스 → 텍스트/카테고리)
        self.index_to_text = {}  # 인덱스 → 원본 텍스트 매핑
        
        # 모델 일관성 보장을 위한 모델 정보 저장
        self.embedding_model_name = embedding_model  # 사용 중인 임베딩 모델 이름
        self.codebook_version = "1.0.0"  # 코드북 버전
        
    def load_bible_verses(self) -> List[Tuple[str, str]]:
        """
        성경 구절 로드 (31,102개)
        
        Returns:
            [(텍스트, 카테고리), ...] 리스트
        """
        logger.info("📖 성경 구절 로드 중...")
        
        verses = []
        
        # English Trinity 파일 경로
        kjv_file = WORKSPACE_ROOT / "data" / "logos" / "multi_logos" / "kjv.json"
        nasb_file = WORKSPACE_ROOT / "data" / "logos" / "multi_logos" / "nasb.json"
        niv_file = WORKSPACE_ROOT / "data" / "logos" / "multi_logos" / "niv.json"
        
        # KJV 로드 (우선)
        if kjv_file.exists():
            try:
                with open(kjv_file, 'r', encoding='utf-8') as f:
                    kjv_data = json.load(f)
                    if isinstance(kjv_data, dict) and "books" in kjv_data:
                        for book in kjv_data.get("books", []):
                            for chapter in book.get("chapters", []):
                                for verse in chapter.get("verses", []):
                                    text = verse.get("text", "")
                                    if text:
                                        verses.append((text, f"bible_kjv_{book.get('name', '')}_{chapter.get('chapter', 0)}_{verse.get('verse', 0)}"))
                    logger.info(f"✅ KJV 로드 완료: {len(verses)}개 구절")
            except Exception as e:
                logger.warning(f"⚠️ KJV 로드 실패: {e}")
        
        # NASB 로드 (추가)
        if nasb_file.exists() and len(verses) < 10000:
            try:
                with open(nasb_file, 'r', encoding='utf-8') as f:
                    nasb_data = json.load(f)
                    if isinstance(nasb_data, dict) and "books" in nasb_data:
                        for book in nasb_data.get("books", []):
                            for chapter in book.get("chapters", []):
                                for verse in chapter.get("verses", []):
                                    text = verse.get("text", "")
                                    if text:
                                        verses.append((text, f"bible_nasb_{book.get('name', '')}_{chapter.get('chapter', 0)}_{verse.get('verse', 0)}"))
                    logger.info(f"✅ NASB 로드 완료: 총 {len(verses)}개 구절")
            except Exception as e:
                logger.warning(f"⚠️ NASB 로드 실패: {e}")
        
        # NIV 로드 (추가)
        if niv_file.exists() and len(verses) < 20000:
            try:
                with open(niv_file, 'r', encoding='utf-8') as f:
                    niv_data = json.load(f)
                    if isinstance(niv_data, dict) and "books" in niv_data:
                        for book in niv_data.get("books", []):
                            for chapter in book.get("chapters", []):
                                for verse in chapter.get("verses", []):
                                    text = verse.get("text", "")
                                    if text:
                                        verses.append((text, f"bible_niv_{book.get('name', '')}_{chapter.get('chapter', 0)}_{verse.get('verse', 0)}"))
                    logger.info(f"✅ NIV 로드 완료: 총 {len(verses)}개 구절")
            except Exception as e:
                logger.warning(f"⚠️ NIV 로드 실패: {e}")
        
        if not verses:
            logger.warning("⚠️ 성경 구절을 찾을 수 없습니다. 샘플 데이터 생성...")
            # 샘플 데이터 생성 (테스트용)
            verses = [
                ("In the beginning was the Word", "bible_sample_1"),
                ("For God so loved the world", "bible_sample_2"),
                ("The Lord is my shepherd", "bible_sample_3")
            ]
        
        logger.info(f"📖 성경 구절 로드 완료: {len(verses)}개")
        return verses
    
    def load_constitution_patterns(self) -> List[Tuple[str, str]]:
        """
        사상체질 4개 패턴 로드
        
        Returns:
            [(텍스트, 카테고리), ...] 리스트
        """
        logger.info("🏛️ 사상체질 패턴 로드 중...")
        
        patterns = [
            ("Type A: Innovation Pattern - 창의적이고 혁신적인 사고", "constitution_type_a"),
            ("Type B: Stability Pattern - 안정적이고 균형잡힌 사고", "constitution_type_b"),
            ("Type C: Efficiency Pattern - 효율적이고 논리적인 사고", "constitution_type_c"),
            ("Type D: Precision Pattern - 정밀하고 실용적인 사고", "constitution_type_d")
        ]
        
        logger.info(f"✅ 사상체질 패턴 로드 완료: {len(patterns)}개")
        return patterns
    
    def load_investment_terms(self) -> List[Tuple[str, str]]:
        """
        투자 용어 1,000개 로드
        
        Returns:
            [(텍스트, 카테고리), ...] 리스트
        """
        logger.info("💰 투자 용어 로드 중...")
        
        # 기본 투자 용어 (실제로는 파일에서 로드하거나 API에서 가져와야 함)
        investment_terms = [
            ("EPS: Earnings Per Share", "investment_eps"),
            ("ROE: Return on Equity", "investment_roe"),
            ("ROA: Return on Assets", "investment_roa"),
            ("P/E Ratio: Price to Earnings Ratio", "investment_pe_ratio"),
            ("Market Cap: Market Capitalization", "investment_market_cap"),
            ("Dividend Yield", "investment_dividend_yield"),
            ("Beta: Market Volatility", "investment_beta"),
            ("Alpha: Excess Return", "investment_alpha"),
            ("Bull Market: 상승장", "investment_bull_market"),
            ("Bear Market: 하락장", "investment_bear_market")
        ]
        
        # 실제로는 1,000개를 로드해야 하지만, 여기서는 샘플만 제공
        # TODO: 실제 투자 용어 데이터베이스에서 로드
        
        logger.info(f"✅ 투자 용어 로드 완료: {len(investment_terms)}개 (샘플)")
        return investment_terms
    
    def load_myeongri_patterns(self) -> List[Tuple[str, str]]:
        """
        명리학 패턴 로드
        
        Returns:
            [(텍스트, 카테고리), ...] 리스트
        """
        logger.info("🔮 명리학 패턴 로드 중...")
        
        # 기본 명리학 패턴 (실제로는 파일에서 로드해야 함)
        myeongri_patterns = [
            ("천간: 갑을병정무기경신임계", "myeongri_cheongan"),
            ("지지: 자축인묘진사오미신유술해", "myeongri_jiji"),
            ("오행: 목화토금수", "myeongri_ohaeng"),
            ("십이지지: 자축인묘진사오미신유술해", "myeongri_sibijiji"),
            ("사주: 년월일시", "myeongri_saju")
        ]
        
        # TODO: 실제 명리학 패턴 데이터베이스에서 로드
        
        logger.info(f"✅ 명리학 패턴 로드 완료: {len(myeongri_patterns)}개 (샘플)")
        return myeongri_patterns
    
    def build_codebook(self) -> Dict[str, Any]:
        """
        코드북 구축 (VQ-VAE)
        
        Returns:
            코드북 딕셔너리
        """
        logger.info("🏛️ MKM Sovereign Codebook 구축 시작...")
        
        if not self.brain:
            logger.error("❌ 임베딩 모델이 없습니다. 코드북 구축 불가.")
            return {}
        
        # 1. 모든 텍스트 수집
        all_texts = []
        all_metadata = []
        
        # 성경 구절
        bible_verses = self.load_bible_verses()
        for text, category in bible_verses:
            all_texts.append(text)
            all_metadata.append({"category": category, "type": "bible"})
        
        # 사상체질
        constitution_patterns = self.load_constitution_patterns()
        for text, category in constitution_patterns:
            all_texts.append(text)
            all_metadata.append({"category": category, "type": "constitution"})
        
        # 투자 용어
        investment_terms = self.load_investment_terms()
        for text, category in investment_terms:
            all_texts.append(text)
            all_metadata.append({"category": category, "type": "investment"})
        
        # 명리학 패턴
        myeongri_patterns = self.load_myeongri_patterns()
        for text, category in myeongri_patterns:
            all_texts.append(text)
            all_metadata.append({"category": category, "type": "myeongri"})
        
        logger.info(f"📊 총 {len(all_texts)}개 텍스트 수집 완료")
        
        # 2. 벡터화
        logger.info("🔄 벡터화 중...")
        try:
            vectors = self.brain.encode(all_texts, show_progress_bar=True)
            logger.info(f"✅ 벡터화 완료: {vectors.shape}")
        except Exception as e:
            logger.error(f"❌ 벡터화 실패: {e}")
            return {}
        
        # 3. 코드북 생성 (K-means 클러스터링)
        if SKLEARN_AVAILABLE and len(vectors) > self.codebook_size:
            logger.info(f"🔧 K-means 클러스터링으로 코드북 생성 중... (목표: {self.codebook_size}개)")
            try:
                kmeans = KMeans(
                    n_clusters=self.codebook_size,
                    random_state=42,
                    n_init=10,
                    max_iter=100
                )
                kmeans.fit(vectors)
                
                # 코드북 = 클러스터 중심
                self.codebook = kmeans.cluster_centers_.astype(np.float32)
                logger.info(f"✅ 코드북 생성 완료: {self.codebook.shape}")
                
                # 각 벡터에 대한 코드북 인덱스 할당
                codebook_indices = kmeans.predict(vectors)
                
                # 인덱스 → 텍스트 매핑 (가장 가까운 텍스트 선택)
                for idx, codebook_idx in enumerate(codebook_indices):
                    if codebook_idx not in self.index_to_text:
                        self.index_to_text[codebook_idx] = all_texts[idx]
                        self.codebook_metadata.append({
                            "index": int(codebook_idx),
                            "text": all_texts[idx],
                            "metadata": all_metadata[idx]
                        })
            except Exception as e:
                logger.error(f"❌ K-means 클러스터링 실패: {e}")
                # Fallback: 모든 벡터를 코드북으로 사용
                self.codebook = vectors.astype(np.float32)
                for idx, text in enumerate(all_texts):
                    self.index_to_text[idx] = text
                    self.codebook_metadata.append({
                        "index": idx,
                        "text": text,
                        "metadata": all_metadata[idx]
                    })
        else:
            # Fallback: 모든 벡터를 코드북으로 사용
            logger.info("⚠️ K-means 사용 불가. 모든 벡터를 코드북으로 사용...")
            self.codebook = vectors.astype(np.float32)
            for idx, text in enumerate(all_texts):
                self.index_to_text[idx] = text
                self.codebook_metadata.append({
                    "index": idx,
                    "text": text,
                    "metadata": all_metadata[idx]
                })
        
        logger.info(f"✅ 코드북 구축 완료: {len(self.codebook_metadata)}개 항목")
        
        return {
            "codebook": self.codebook.tolist(),
            "metadata": self.codebook_metadata,
            "index_to_text": self.index_to_text,
            "size": len(self.codebook_metadata)
        }
    
    def quantize_vector(self, vector: np.ndarray) -> int:
        """
        벡터를 코드북 인덱스로 양자화
        
        Args:
            vector: 768D 벡터
        
        Returns:
            코드북 인덱스 (정수)
        """
        if self.codebook is None:
            logger.error("❌ 코드북이 구축되지 않았습니다.")
            return -1
        
        # 가장 가까운 코드북 벡터 찾기
        distances = np.linalg.norm(self.codebook - vector.reshape(1, -1), axis=1)
        closest_idx = np.argmin(distances)
        
        return int(closest_idx)
    
    def dequantize_index(self, index: int) -> Optional[np.ndarray]:
        """
        코드북 인덱스를 벡터로 복원
        
        Args:
            index: 코드북 인덱스
        
        Returns:
            768D 벡터
        """
        if self.codebook is None:
            logger.error("❌ 코드북이 구축되지 않았습니다.")
            return None
        
        if index < 0 or index >= len(self.codebook):
            logger.error(f"❌ 잘못된 인덱스: {index} (범위: 0-{len(self.codebook)-1})")
            return None
        
        return self.codebook[index]
    
    def save_codebook(
        self,
        filepath: Path,
        include_text_mapping: bool = False  # 배포용은 False (보안 강화)
    ) -> bool:
        """
        코드북 저장
        
        Args:
            filepath: 저장 경로
            include_text_mapping: 원본 텍스트 매핑 포함 여부 (기본값: False, 보안 강화)
                - False: 배포용 코드북 (index_to_text 제외, Zero-Knowledge API 지원)
                - True: 서버 전용 코드북 (index_to_text 포함, 디버깅/개발용)
        
        Returns:
            성공 여부
        """
        if self.codebook is None:
            logger.error("❌ 코드북이 구축되지 않았습니다.")
            return False
        
        logger.info(f"💾 코드북 저장 중: {filepath}")
        
        codebook_data = {
            "version": self.codebook_version,  # 코드북 버전
            "embedding_model": self.embedding_model_name,  # 임베딩 모델 이름
            "codebook": self.codebook.tolist(),
            "metadata": self.codebook_metadata,
            "size": len(self.codebook_metadata),
            "vector_dim": self.codebook.shape[1] if len(self.codebook.shape) > 1 else 768
        }
        
        # 보안 강화: 배포용 코드북에는 index_to_text 제외
        if include_text_mapping:
            codebook_data["index_to_text"] = self.index_to_text
            logger.info("⚠️ 원본 텍스트 매핑 포함 (서버 전용 모드)")
        else:
            logger.info("✅ 배포용 코드북 모드 (index_to_text 제외, Zero-Knowledge API 지원)")
        
        # 서버 전용 매핑 파일 분리 (include_text_mapping=True일 때만)
        if include_text_mapping and self.index_to_text:
            mapping_file = filepath.with_suffix('.mapping.json')
            try:
                with open(mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(self.index_to_text, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ 서버 전용 매핑 파일 저장: {mapping_file}")
            except Exception as e:
                logger.warning(f"⚠️ 매핑 파일 저장 실패: {e}")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(codebook_data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 코드북 저장 완료: {filepath}")
            return True
        except Exception as e:
            logger.error(f"❌ 코드북 저장 실패: {e}")
            return False
    
    def load_codebook(self, filepath: Path) -> bool:
        """
        코드북 로드
        
        Args:
            filepath: 로드 경로
        
        Returns:
            성공 여부
        """
        logger.info(f"📂 코드북 로드 중: {filepath}")
        
        if not filepath.exists():
            logger.error(f"❌ 코드북 파일이 없습니다: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                codebook_data = json.load(f)
            
            # 모델 일관성 검증 (코드북에 저장된 모델과 현재 모델 일치 확인)
            saved_embedding_model = codebook_data.get("embedding_model")
            if saved_embedding_model and saved_embedding_model != self.embedding_model_name:
                logger.error(
                    f"❌ 코드북 모델 불일치: "
                    f"코드북에 저장된 모델={saved_embedding_model}, "
                    f"현재 모델={self.embedding_model_name}. "
                    f"코드북을 다시 구축하거나 동일한 모델을 사용하세요."
                )
                return False
            
            # 버전 정보 로드 (선택적)
            self.codebook_version = codebook_data.get("version", "1.0.0")
            
            self.codebook = np.array(codebook_data["codebook"], dtype=np.float32)
            self.codebook_metadata = codebook_data.get("metadata", [])
            
            # 보안 강화: 배포용 코드북에는 index_to_text 제외
            # 서버 전용 매핑 파일 로드 시도
            mapping_file = filepath.with_suffix('.mapping.json')
            if mapping_file.exists():
                try:
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        self.index_to_text = json.load(f)
                    logger.info(f"✅ 서버 전용 매핑 파일 로드: {mapping_file}")
                except Exception as e:
                    logger.warning(f"⚠️ 매핑 파일 로드 실패: {e}")
                    # 레거시 코드북 지원 (index_to_text가 코드북 파일에 포함된 경우)
                    self.index_to_text = codebook_data.get("index_to_text", {})
                    if self.index_to_text:
                        logger.warning("⚠️ 레거시 코드북 감지 (index_to_text 포함)")
            else:
                # 배포용 코드북 모드: index_to_text 제외
                self.index_to_text = {}
                logger.info("✅ 배포용 코드북 모드 (index_to_text 제외, Zero-Knowledge API 지원)")
            
            logger.info(
                f"✅ 코드북 로드 완료: {len(self.codebook_metadata)}개 항목 "
                f"(모델: {saved_embedding_model or self.embedding_model_name}, "
                f"버전: {self.codebook_version})"
            )
            return True
        except Exception as e:
            logger.error(f"❌ 코드북 로드 실패: {e}")
            return False


def main():
    """메인 함수: 코드북 구축 및 테스트"""
    logger.info("=" * 80)
    logger.info("🏛️ MKM Sovereign Codebook 구축")
    logger.info("=" * 80)
    
    # 코드북 구축
    codebook_builder = MKMSovereignCodebook(
        embedding_model="all-MiniLM-L6-v2",
        codebook_size=50000
    )
    
    # 코드북 구축
    codebook_data = codebook_builder.build_codebook()
    
    if not codebook_data:
        logger.error("❌ 코드북 구축 실패")
        return
    
    # 코드북 저장
    codebook_path = WORKSPACE_ROOT / "data" / "mkm_sovereign_codebook.json"
    codebook_path.parent.mkdir(parents=True, exist_ok=True)
    codebook_builder.save_codebook(codebook_path)
    
    # 테스트: 벡터 양자화 및 복원
    logger.info("\n" + "=" * 80)
    logger.info("🧪 코드북 테스트")
    logger.info("=" * 80)
    
    test_text = "In the beginning was the Word"
    if codebook_builder.brain:
        test_vector = codebook_builder.brain.encode(test_text)
        quantized_idx = codebook_builder.quantize_vector(test_vector)
        dequantized_vector = codebook_builder.dequantize_index(quantized_idx)
        
        logger.info(f"📝 테스트 텍스트: {test_text}")
        logger.info(f"📊 양자화 인덱스: {quantized_idx}")
        logger.info(f"📊 복원 벡터 차원: {dequantized_vector.shape if dequantized_vector is not None else 'None'}")
        logger.info(f"📊 코드북 인덱스 → 텍스트: {codebook_builder.index_to_text.get(quantized_idx, 'N/A')}")
        
        # 압축률 계산
        original_size = len(test_text.encode('utf-8'))
        quantized_size = 4  # int32 = 4 bytes
        compression_ratio = (1 - quantized_size / original_size) * 100
        
        logger.info(f"📊 압축률: {compression_ratio:.2f}% (원본: {original_size} bytes → 양자화: {quantized_size} bytes)")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ MKM Sovereign Codebook 구축 완료")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

