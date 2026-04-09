#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 통합 코드북 빌더 (Data-Tier + Logic-Tier 융합)

목적: Data-Tier와 Logic-Tier 코드북을 통합하여 구축
- JSON/YAML/SQL 패턴과 시스템 프롬프트 패턴을 통합
- 두 도메인의 패턴을 벡터화하여 코드북 구축
- MKMDomainCodebookRouter에 DATA와 LOGIC 도메인 통합

작성일: 2026-02-13
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
import logging
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "core"))

# Data-Tier와 Logic-Tier 빌더 import
try:
    from data_tier_codebook_builder import DataTierCodebookBuilder
    DATA_TIER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ DataTierCodebookBuilder 임포트 실패: {e}")
    DATA_TIER_AVAILABLE = False

try:
    from logic_tier_codebook_builder import LogicTierCodebookBuilder
    LOGIC_TIER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ LogicTierCodebookBuilder 임포트 실패: {e}")
    LOGIC_TIER_AVAILABLE = False

# SentenceTransformer import
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    logger.warning("SentenceTransformer를 사용할 수 없습니다.")
    SENTENCE_TRANSFORMER_AVAILABLE = False

# sklearn KMeans import
try:
    from sklearn.cluster import MiniBatchKMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("sklearn을 사용할 수 없습니다.")
    SKLEARN_AVAILABLE = False

# MKMDomainCodebookRouter import
try:
    from mkm_domain_codebook_router import MKMDomainCodebookRouter, Domain
    CODEBOOK_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ MKMDomainCodebookRouter 임포트 실패: {e}")
    CODEBOOK_ROUTER_AVAILABLE = False


class UnifiedCodebookBuilder:
    """
    통합 코드북 빌더
    
    Data-Tier와 Logic-Tier를 융합하여 통합 코드북을 구축합니다.
    """
    
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        codebook_size_per_domain: int = 31000,
        workspace_root: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        """
        초기화
        
        Args:
            embedding_model: 임베딩 모델 이름
            codebook_size_per_domain: 도메인당 코드북 크기
            workspace_root: 워크스페이스 루트 경로
            output_dir: 출력 디렉토리
        """
        logger.info("🔗 통합 코드북 빌더 초기화...")
        
        self.workspace_root = workspace_root or WORKSPACE_ROOT
        self.output_dir = output_dir or (self.workspace_root / "data" / "codebooks")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_model = embedding_model
        self.codebook_size_per_domain = codebook_size_per_domain
        
        # 임베딩 모델 로드
        self.brain = None
        if SENTENCE_TRANSFORMER_AVAILABLE:
            try:
                self.brain = SentenceTransformer(embedding_model)
                logger.info(f"✅ 임베딩 모델 로드 완료: {embedding_model}")
            except Exception as e:
                logger.error(f"❌ 임베딩 모델 로드 실패: {e}")
                self.brain = None
        
        # 코드북 라우터 초기화
        self.codebook_router = None
        if CODEBOOK_ROUTER_AVAILABLE:
            try:
                self.codebook_router = MKMDomainCodebookRouter(
                    embedding_model=embedding_model,
                    codebook_size_per_domain=codebook_size_per_domain
                )
                logger.info("✅ MKMDomainCodebookRouter 초기화 완료")
            except Exception as e:
                logger.error(f"❌ MKMDomainCodebookRouter 초기화 실패: {e}")
                self.codebook_router = None
        
        # Data-Tier 빌더 초기화
        self.data_tier_builder = None
        if DATA_TIER_AVAILABLE:
            try:
                self.data_tier_builder = DataTierCodebookBuilder(
                    embedding_model=embedding_model,
                    codebook_size_per_domain=codebook_size_per_domain
                )
                logger.info("✅ DataTierCodebookBuilder 초기화 완료")
            except Exception as e:
                logger.error(f"❌ DataTierCodebookBuilder 초기화 실패: {e}")
                self.data_tier_builder = None
        
        # Logic-Tier 빌더 초기화
        self.logic_tier_builder = None
        if LOGIC_TIER_AVAILABLE:
            try:
                self.logic_tier_builder = LogicTierCodebookBuilder(
                    output_dir=self.output_dir.parent / "logic_tier_patterns"
                )
                logger.info("✅ LogicTierCodebookBuilder 초기화 완료")
            except Exception as e:
                logger.error(f"❌ LogicTierCodebookBuilder 초기화 실패: {e}")
                self.logic_tier_builder = None
        
        logger.info("🔗 통합 코드북 빌더 초기화 완료")
    
    def collect_all_patterns(self) -> Dict[str, Any]:
        """
        모든 패턴 수집 (Data-Tier + Logic-Tier)
        
        Returns:
            수집된 패턴 딕셔너리
        """
        logger.info("=" * 80)
        logger.info("📥 모든 패턴 수집 시작 (Data-Tier + Logic-Tier)")
        logger.info("=" * 80)
        
        all_patterns = {
            "data_tier": {},
            "logic_tier": {},
            "total": 0
        }
        
        # 1. Data-Tier 패턴 수집
        if self.data_tier_builder:
            logger.info("\n[1/2] Data-Tier 패턴 수집 중...")
            try:
                json_patterns = self.data_tier_builder.collect_json_patterns(self.workspace_root)
                yaml_patterns = self.data_tier_builder.collect_yaml_patterns(self.workspace_root)
                sql_patterns = self.data_tier_builder.collect_sql_patterns(self.workspace_root)
                common_fields = self.data_tier_builder.extract_common_field_patterns()
                
                all_patterns["data_tier"] = {
                    "json_patterns": json_patterns,
                    "yaml_patterns": yaml_patterns,
                    "sql_patterns": sql_patterns,
                    "common_fields": common_fields,
                    "total": len(json_patterns) + len(yaml_patterns) + len(sql_patterns)
                }
                
                logger.info(f"✅ Data-Tier 패턴 수집 완료: {all_patterns['data_tier']['total']}개")
                logger.info(f"   - JSON: {len(json_patterns)}개")
                logger.info(f"   - YAML: {len(yaml_patterns)}개")
                logger.info(f"   - SQL: {len(sql_patterns)}개")
                logger.info(f"   - 공통 필드: {len(common_fields)}개")
            except Exception as e:
                logger.error(f"❌ Data-Tier 패턴 수집 실패: {e}")
                all_patterns["data_tier"] = {"error": str(e)}
        else:
            logger.warning("⚠️ DataTierCodebookBuilder를 사용할 수 없습니다.")
        
        # 2. Logic-Tier 패턴 수집
        if self.logic_tier_builder:
            logger.info("\n[2/2] Logic-Tier 패턴 수집 중...")
            try:
                openai_patterns = self.logic_tier_builder.collect_openai_prompts()
                anthropic_patterns = self.logic_tier_builder.collect_anthropic_prompts()
                google_patterns = self.logic_tier_builder.collect_google_prompts()
                instruction_patterns = self.logic_tier_builder.collect_instruction_patterns()
                caching_patterns = self.logic_tier_builder.analyze_prompt_caching_patterns()
                
                all_patterns["logic_tier"] = {
                    "openai_patterns": openai_patterns,
                    "anthropic_patterns": anthropic_patterns,
                    "google_patterns": google_patterns,
                    "instruction_patterns": instruction_patterns,
                    "caching_patterns": caching_patterns,
                    "total": len(openai_patterns) + len(anthropic_patterns) + 
                            len(google_patterns) + len(instruction_patterns) + 
                            len(caching_patterns)
                }
                
                logger.info(f"✅ Logic-Tier 패턴 수집 완료: {all_patterns['logic_tier']['total']}개")
                logger.info(f"   - OpenAI: {len(openai_patterns)}개")
                logger.info(f"   - Anthropic: {len(anthropic_patterns)}개")
                logger.info(f"   - Google: {len(google_patterns)}개")
                logger.info(f"   - Instructions: {len(instruction_patterns)}개")
                logger.info(f"   - Caching: {len(caching_patterns)}개")
            except Exception as e:
                logger.error(f"❌ Logic-Tier 패턴 수집 실패: {e}")
                all_patterns["logic_tier"] = {"error": str(e)}
        else:
            logger.warning("⚠️ LogicTierCodebookBuilder를 사용할 수 없습니다.")
        
        # 총 패턴 수 계산
        data_total = all_patterns["data_tier"].get("total", 0)
        logic_total = all_patterns["logic_tier"].get("total", 0)
        all_patterns["total"] = data_total + logic_total
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ 전체 패턴 수집 완료: {all_patterns['total']}개")
        logger.info(f"   - Data-Tier: {data_total}개")
        logger.info(f"   - Logic-Tier: {logic_total}개")
        logger.info("=" * 80)
        
        return all_patterns
    
    def build_unified_codebooks(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        통합 코드북 구축 (Data-Tier + Logic-Tier)
        
        두 도메인의 패턴을 통합하여 벡터화하고 코드북을 구축합니다.
        
        Args:
            domain: 구축할 도메인 ("DATA", "LOGIC", None=모두)
        
        Returns:
            구축 결과 딕셔너리
        """
        if domain:
            logger.info("=" * 80)
            logger.info(f"🏗️ {domain}-Tier 코드북 구축 시작")
            logger.info("=" * 80)
        else:
            logger.info("=" * 80)
            logger.info("🏗️ 통합 코드북 구축 시작 (Data-Tier + Logic-Tier)")
            logger.info("=" * 80)
        
        if not self.brain:
            raise RuntimeError("임베딩 모델이 로드되지 않았습니다.")
        
        if not self.codebook_router:
            raise RuntimeError("MKMDomainCodebookRouter가 초기화되지 않았습니다.")
        
        # 1. 모든 패턴 수집 (도메인 필터링)
        if domain == "DATA":
            # Data-Tier만 수집
            all_patterns = {
                "data_tier": {},
                "logic_tier": {},
                "total": 0
            }
            if self.data_tier_builder:
                logger.info("\n[1/1] Data-Tier 패턴 수집 중...")
                try:
                    json_patterns = self.data_tier_builder.collect_json_patterns(self.workspace_root)
                    yaml_patterns = self.data_tier_builder.collect_yaml_patterns(self.workspace_root)
                    sql_patterns = self.data_tier_builder.collect_sql_patterns(self.workspace_root)
                    common_fields = self.data_tier_builder.extract_common_field_patterns()
                    
                    all_patterns["data_tier"] = {
                        "json_patterns": json_patterns,
                        "yaml_patterns": yaml_patterns,
                        "sql_patterns": sql_patterns,
                        "common_fields": common_fields,
                        "total": len(json_patterns) + len(yaml_patterns) + len(sql_patterns)
                    }
                    all_patterns["total"] = all_patterns["data_tier"]["total"]
                    logger.info(f"✅ Data-Tier 패턴 수집 완료: {all_patterns['data_tier']['total']}개")
                except Exception as e:
                    logger.error(f"❌ Data-Tier 패턴 수집 실패: {e}")
                    all_patterns["data_tier"] = {"error": str(e)}
        elif domain == "LOGIC":
            # Logic-Tier만 수집
            all_patterns = {
                "data_tier": {},
                "logic_tier": {},
                "total": 0
            }
            if self.logic_tier_builder:
                logger.info("\n[1/1] Logic-Tier 패턴 수집 중...")
                try:
                    openai_patterns = self.logic_tier_builder.collect_openai_prompts()
                    anthropic_patterns = self.logic_tier_builder.collect_anthropic_prompts()
                    google_patterns = self.logic_tier_builder.collect_google_prompts()
                    instruction_patterns = self.logic_tier_builder.extract_instruction_patterns()
                    caching_patterns = self.logic_tier_builder.analyze_prompt_caching_patterns()
                    
                    all_patterns["logic_tier"] = {
                        "openai_patterns": openai_patterns,
                        "anthropic_patterns": anthropic_patterns,
                        "google_patterns": google_patterns,
                        "instruction_patterns": instruction_patterns,
                        "caching_patterns": caching_patterns,
                        "total": len(openai_patterns) + len(anthropic_patterns) + 
                                len(google_patterns) + len(instruction_patterns) + 
                                len(caching_patterns)
                    }
                    all_patterns["total"] = all_patterns["logic_tier"]["total"]
                    logger.info(f"✅ Logic-Tier 패턴 수집 완료: {all_patterns['logic_tier']['total']}개")
                except Exception as e:
                    logger.error(f"❌ Logic-Tier 패턴 수집 실패: {e}")
                    all_patterns["logic_tier"] = {"error": str(e)}
        else:
            # 모든 패턴 수집
            all_patterns = self.collect_all_patterns()
        
        # 2. 도메인별 코드북 구축
        results = {
            "data_tier": None,
            "logic_tier": None,
            "unified_stats": {}
        }
        
        # 2-1. Data-Tier 코드북 구축
        if (domain is None or domain == "DATA") and self.data_tier_builder and "error" not in all_patterns["data_tier"]:
            logger.info("\n" + "=" * 80)
            logger.info("📊 Data-Tier 코드북 구축 중...")
            logger.info("=" * 80)
            try:
                data_result = self.data_tier_builder.build_data_tier_codebook(
                    workspace_root=self.workspace_root,
                    output_dir=self.output_dir
                )
                results["data_tier"] = data_result
                logger.info(f"✅ Data-Tier 코드북 구축 완료")
            except Exception as e:
                logger.error(f"❌ Data-Tier 코드북 구축 실패: {e}")
                results["data_tier"] = {"success": False, "error": str(e)}
        
        # 2-2. Logic-Tier 코드북 구축
        if (domain is None or domain == "LOGIC") and self.logic_tier_builder and "error" not in all_patterns["logic_tier"]:
            logger.info("\n" + "=" * 80)
            logger.info("🚀 Logic-Tier 코드북 구축 중...")
            logger.info("=" * 80)
            try:
                # Logic-Tier는 패턴만 수집하고 저장하는 방식이므로
                # 별도로 벡터화 및 코드북 구축 필요
                logic_result = self._build_logic_tier_codebook(all_patterns["logic_tier"])
                results["logic_tier"] = logic_result
                logger.info(f"✅ Logic-Tier 코드북 구축 완료")
            except Exception as e:
                logger.error(f"❌ Logic-Tier 코드북 구축 실패: {e}")
                results["logic_tier"] = {"success": False, "error": str(e)}
        
        # 3. 통합 통계 생성
        logger.info("\n" + "=" * 80)
        logger.info("📊 통합 통계 생성 중...")
        logger.info("=" * 80)
        
        unified_stats = {
            "total_patterns": all_patterns["total"],
            "data_tier": {
                "total": all_patterns["data_tier"].get("total", 0),
                "json": len(all_patterns["data_tier"].get("json_patterns", [])),
                "yaml": len(all_patterns["data_tier"].get("yaml_patterns", [])),
                "sql": len(all_patterns["data_tier"].get("sql_patterns", [])),
                "common_fields": len(all_patterns["data_tier"].get("common_fields", {}))
            },
            "logic_tier": {
                "total": all_patterns["logic_tier"].get("total", 0),
                "openai": len(all_patterns["logic_tier"].get("openai_patterns", [])),
                "anthropic": len(all_patterns["logic_tier"].get("anthropic_patterns", [])),
                "google": len(all_patterns["logic_tier"].get("google_patterns", [])),
                "instruction": len(all_patterns["logic_tier"].get("instruction_patterns", [])),
                "caching": len(all_patterns["logic_tier"].get("caching_patterns", []))
            },
            "compression_ratios": {
                "data_tier": results["data_tier"].get("compression_ratio", 0) if results["data_tier"] else 0,
                "logic_tier": results["logic_tier"].get("compression_ratio", 0) if results["logic_tier"] else 0
            }
        }
        
        results["unified_stats"] = unified_stats
        
        # 4. 통합 리포트 저장
        report_file = self.output_dir / "unified_codebook_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0.0",
                    "embedding_model": self.embedding_model,
                    "codebook_size_per_domain": self.codebook_size_per_domain
                },
                "results": results,
                "statistics": unified_stats
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 통합 리포트 저장 완료: {report_file}")
        
        # 5. 최종 요약
        logger.info("\n" + "=" * 80)
        logger.info("🎉 통합 코드북 구축 완료!")
        logger.info("=" * 80)
        logger.info(f"📊 총 패턴 수: {unified_stats['total_patterns']}개")
        logger.info(f"   - Data-Tier: {unified_stats['data_tier']['total']}개")
        logger.info(f"   - Logic-Tier: {unified_stats['logic_tier']['total']}개")
        logger.info(f"📈 압축률:")
        logger.info(f"   - Data-Tier: {unified_stats['compression_ratios']['data_tier']:.2f}%")
        logger.info(f"   - Logic-Tier: {unified_stats['compression_ratios']['logic_tier']:.2f}%")
        logger.info("=" * 80)
        
        return results
    
    def _build_logic_tier_codebook(self, logic_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """
        Logic-Tier 코드북 구축 (벡터화 및 클러스터링)
        
        Args:
            logic_patterns: Logic-Tier 패턴 딕셔너리
        
        Returns:
            구축 결과 딕셔너리
        """
        logger.info("🚀 Logic-Tier 코드북 벡터화 및 구축 중...")
        
        # 디버깅: 패턴 구조 확인
        logger.info(f"📊 수집된 패턴 구조: {list(logic_patterns.keys())}")
        logger.info(f"   - OpenAI: {len(logic_patterns.get('openai_patterns', []))}개")
        logger.info(f"   - Anthropic: {len(logic_patterns.get('anthropic_patterns', []))}개")
        logger.info(f"   - Google: {len(logic_patterns.get('google_patterns', []))}개")
        logger.info(f"   - Instruction: {len(logic_patterns.get('instruction_patterns', []))}개")
        logger.info(f"   - Caching: {len(logic_patterns.get('caching_patterns', []))}개")
        
        # 모든 패턴을 텍스트로 변환
        all_texts = []
        all_metadata = []
        
        # OpenAI 패턴
        openai_list = logic_patterns.get("openai_patterns", [])
        if openai_list:
            logger.info(f"   첫 번째 OpenAI 패턴 구조: {list(openai_list[0].keys())}")
        for pattern in openai_list:
            # "text" 또는 "pattern" 키 모두 지원
            text = pattern.get("text", "") or pattern.get("pattern", "")
            if text:
                all_texts.append(text)
                all_metadata.append({
                    "type": "openai",
                    "pattern_type": pattern.get("type", ""),
                    "frequency": pattern.get("frequency", 0)
                })
        
        # Anthropic 패턴
        for pattern in logic_patterns.get("anthropic_patterns", []):
            text = pattern.get("text", "") or pattern.get("pattern", "")
            if text:
                all_texts.append(text)
                all_metadata.append({
                    "type": "anthropic",
                    "pattern_type": pattern.get("type", ""),
                    "frequency": pattern.get("frequency", 0)
                })
        
        # Google 패턴
        for pattern in logic_patterns.get("google_patterns", []):
            text = pattern.get("text", "") or pattern.get("pattern", "")
            if text:
                all_texts.append(text)
                all_metadata.append({
                    "type": "google",
                    "pattern_type": pattern.get("type", ""),
                    "frequency": pattern.get("frequency", 0)
                })
        
        # Instruction 패턴
        for pattern in logic_patterns.get("instruction_patterns", []):
            text = pattern.get("text", "") or pattern.get("pattern", "")
            if text:
                all_texts.append(text)
                all_metadata.append({
                    "type": "instruction",
                    "pattern_type": pattern.get("type", ""),
                    "frequency": pattern.get("frequency", 0)
                })
        
        # Caching 패턴
        for pattern in logic_patterns.get("caching_patterns", []):
            text = pattern.get("text", "") or pattern.get("pattern", "")
            if text:
                all_texts.append(text)
                all_metadata.append({
                    "type": "caching",
                    "pattern_type": pattern.get("type", ""),
                    "frequency": pattern.get("frequency", 0)
                })
        
        if not all_texts:
            logger.warning("⚠️ Logic-Tier 패턴이 없어 코드북을 구축할 수 없습니다.")
            return {
                "success": False,
                "error": "패턴 수 부족",
                "total_patterns": 0
            }
        
        logger.info(f"✅ 벡터화할 텍스트 수: {len(all_texts)}개")
        
        # 벡터화
        logger.info("벡터화 중...")
        embeddings = self.brain.encode(all_texts, show_progress_bar=True, batch_size=32)
        logger.info(f"✅ 벡터화 완료: {embeddings.shape}")
        
        # 코드북 구축 (KMeans 클러스터링)
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("sklearn을 사용할 수 없습니다.")
        
        n_clusters = min(self.codebook_size_per_domain, len(embeddings))
        if n_clusters < 2:
            logger.warning("⚠️ 패턴 수가 부족하여 코드북을 구축할 수 없습니다.")
            return {
                "success": False,
                "error": "패턴 수 부족",
                "total_patterns": len(all_texts)
            }
        
        logger.info(f"코드북 구축 중... (클러스터 수: {n_clusters})")
        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # 코드북 벡터 (클러스터 중심)
        codebook_vectors = kmeans.cluster_centers_
        logger.info(f"✅ 코드북 구축 완료: {codebook_vectors.shape}")
        
        # 메타데이터 생성
        codebook_metadata = []
        for i in range(n_clusters):
            cluster_patterns = [all_metadata[j] for j in range(len(all_metadata)) if cluster_labels[j] == i]
            representative = cluster_patterns[0] if cluster_patterns else {}
            
            codebook_metadata.append({
                "index": i,
                "representative": representative,
                "pattern_count": len(cluster_patterns)
            })
        
        # LOGIC 도메인 코드북 저장
        codebook_file = self.output_dir / "L.bin"  # LOGIC 도메인
        metadata_file = self.output_dir / "L_metadata.json"
        
        # 코드북 벡터 저장
        np.save(str(codebook_file), codebook_vectors)
        
        # 메타데이터 저장
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(codebook_metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 코드북 저장 완료: {codebook_file}")
        logger.info(f"✅ 메타데이터 저장 완료: {metadata_file}")
        
        # 압축률 계산
        original_size = sum(len(text) for text in all_texts)
        compressed_size = len(all_texts) * 4  # 정수 4바이트
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        logger.info(f"✅ 압축률 계산 완료:")
        logger.info(f"   원본 크기: {original_size:,} bytes")
        logger.info(f"   압축 후 크기: {compressed_size:,} bytes")
        logger.info(f"   압축률: {compression_ratio:.2f}%")
        
        return {
            "success": True,
            "total_patterns": len(all_texts),
            "codebook_size": n_clusters,
            "codebook_file": str(codebook_file),
            "metadata_file": str(metadata_file),
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio,
            "target_compression": "80-85%",
            "target_achieved": 80 <= compression_ratio <= 85
        }


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="통합 코드북 빌더 (Data-Tier + Logic-Tier)")
    parser.add_argument(
        "--workspace-root",
        type=str,
        default=str(WORKSPACE_ROOT),
        help="워크스페이스 루트 경로"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="출력 디렉토리"
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="임베딩 모델 이름"
    )
    parser.add_argument(
        "--codebook-size",
        type=int,
        default=31000,
        help="코드북 크기"
    )
    parser.add_argument(
        "--domain",
        type=str,
        choices=["DATA", "LOGIC"],
        default=None,
        help="구축할 도메인 (DATA, LOGIC, 또는 모두)"
    )
    
    args = parser.parse_args()
    
    workspace_root = Path(args.workspace_root)
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    builder = UnifiedCodebookBuilder(
        embedding_model=args.embedding_model,
        codebook_size_per_domain=args.codebook_size,
        workspace_root=workspace_root,
        output_dir=output_dir
    )
    
    results = builder.build_unified_codebooks(domain=args.domain)
    
    if not results:
        print("\n" + "=" * 80)
        print("❌ 통합 코드북 구축 실패: 결과가 None입니다.")
        print("=" * 80)
        sys.exit(1)
    
    # 도메인별 성공 조건 확인
    if args.domain == "DATA":
        success = results.get("data_tier", {}).get("success", False)
    elif args.domain == "LOGIC":
        success = results.get("logic_tier", {}).get("success", False)
    else:
        success = results.get("data_tier", {}).get("success", False) and results.get("logic_tier", {}).get("success", False)
    
    if success:
        print("\n" + "=" * 80)
        print("✅ 통합 코드북 구축 성공!")
        print("=" * 80)
        print(f"총 패턴: {results['unified_stats']['total_patterns']}개")
        print(f"Data-Tier 압축률: {results['unified_stats']['compression_ratios']['data_tier']:.2f}%")
        print(f"Logic-Tier 압축률: {results['unified_stats']['compression_ratios']['logic_tier']:.2f}%")
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("❌ 통합 코드북 구축 실패!")
        print("=" * 80)
        if results.get("data_tier"):
            print(f"Data-Tier: {results['data_tier'].get('error', 'Unknown error')}")
        if results.get("logic_tier"):
            print(f"Logic-Tier: {results['logic_tier'].get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

