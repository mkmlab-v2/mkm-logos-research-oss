#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📚 표준 코드북 구축 스크립트

목적: 자주 쓰는 코드 패턴 1,000개를 벡터화하여 표준 코드북 구축
- 로컬 코드베이스에서 패턴 수집
- GitHub 오픈소스 패턴 수집 (선택적)
- 코드북 벡터화 및 저장

작성일: 2026-01-22
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging
from collections import defaultdict

# 워크스페이스 루트 추가
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "core"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from hybrid_vectorizer import hybrid_vectorize
    from mkm_domain_codebook_router import MKMDomainCodebookRouter, Domain
    HYBRID_VECTORIZER_AVAILABLE = True
    CODEBOOK_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ 모듈 임포트 실패: {e}")
    HYBRID_VECTORIZER_AVAILABLE = False
    CODEBOOK_ROUTER_AVAILABLE = False


class StandardCodebookBuilder:
    """
    표준 코드북 구축기
    
    목표: 자주 쓰는 코드 패턴 1,000개 수집 및 벡터화
    """
    
    # 표준 패턴 카테고리
    PATTERN_CATEGORIES = {
        "authentication": [
            "login", "logout", "register", "password_reset", "token_validation",
            "jwt_auth", "oauth", "session_management"
        ],
        "database": [
            "db_connection", "query", "insert", "update", "delete",
            "transaction", "migration", "schema_creation"
        ],
        "api": [
            "rest_endpoint", "graphql_query", "webhook", "rate_limit",
            "cors", "authentication_middleware"
        ],
        "ui": [
            "button", "form", "modal", "table", "chart",
            "navigation", "responsive_layout"
        ],
        "utils": [
            "validation", "formatting", "parsing", "encryption",
            "logging", "error_handling", "caching"
        ]
    }
    
    def __init__(self, target_size: int = 1000):
        """
        초기화
        
        Args:
            target_size: 목표 패턴 수
        """
        self.target_size = target_size
        self.patterns: List[Dict[str, Any]] = []
        self.codebook_router = None
        
        if CODEBOOK_ROUTER_AVAILABLE:
            self.codebook_router = MKMDomainCodebookRouter()
    
    def collect_patterns_from_workspace(self, workspace_root: Path) -> List[Dict[str, Any]]:
        """
        워크스페이스에서 코드 패턴 수집
        
        Args:
            workspace_root: 워크스페이스 루트 경로
        
        Returns:
            패턴 리스트
        """
        logger.info(f"🔍 워크스페이스에서 패턴 수집 중: {workspace_root}")
        
        patterns = []
        pattern_count = defaultdict(int)
        
        # 수집할 파일 확장자
        extensions = {'.py', '.ts', '.tsx', '.js', '.jsx'}
        
        # 제외할 디렉토리
        exclude_dirs = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.next', '.cache', 'memory'
        }
        
        # 파일 순회
        for file_path in workspace_root.rglob('*'):
            # 디렉토리 제외
            if file_path.is_dir():
                continue
            
            # 확장자 확인
            if file_path.suffix not in extensions:
                continue
            
            # 제외 디렉토리 확인
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue
            
            try:
                # 파일 읽기
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # 패턴 추출 (간단한 버전: 함수/클래스 정의 찾기)
                file_patterns = self._extract_patterns_from_file(content, str(file_path))
                
                for pattern in file_patterns:
                    # 카테고리 분류
                    category = self._classify_pattern(pattern)
                    pattern['category'] = category
                    pattern['file_path'] = str(file_path)
                    
                    patterns.append(pattern)
                    pattern_count[category] += 1
                    
                    if len(patterns) >= self.target_size:
                        logger.info(f"✅ 목표 패턴 수 달성: {len(patterns)}개")
                        break
                
                if len(patterns) >= self.target_size:
                    break
                    
            except Exception as e:
                logger.debug(f"⚠️ 파일 처리 실패 ({file_path}): {e}")
                continue
        
        logger.info(f"✅ 패턴 수집 완료: {len(patterns)}개")
        logger.info(f"  카테고리별 분포: {dict(pattern_count)}")
        
        return patterns
    
    def _extract_patterns_from_file(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        파일에서 패턴 추출
        
        Args:
            content: 파일 내용
            file_path: 파일 경로
        
        Returns:
            패턴 리스트
        """
        patterns = []
        
        # Python 함수 추출
        if file_path.endswith('.py'):
            import ast
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # 함수 코드 추출
                        func_code = ast.get_source_segment(content, node) or ""
                        
                        # 간단한 설명 생성
                        description = f"function {node.name}"
                        if node.args.args:
                            params = [arg.arg for arg in node.args.args]
                            description += f" with parameters {params}"
                        
                        patterns.append({
                            "name": node.name,
                            "type": "function",
                            "code": func_code,
                            "description": description,
                            "language": "python"
                        })
            except SyntaxError:
                pass
        
        # TypeScript/JavaScript 함수 추출 (정규식 기반)
        elif file_path.endswith(('.ts', '.tsx', '.js', '.jsx')):
            import re
            
            # 함수 정의 패턴
            func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{[^}]*\}'
            matches = re.finditer(func_pattern, content, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                func_name = match.group(1)
                func_code = match.group(0)
                
                patterns.append({
                    "name": func_name,
                    "type": "function",
                    "code": func_code,
                    "description": f"function {func_name}",
                    "language": "typescript" if file_path.endswith(('.ts', '.tsx')) else "javascript"
                })
        
        return patterns
    
    def _classify_pattern(self, pattern: Dict[str, Any]) -> str:
        """
        패턴 카테고리 분류
        
        Args:
            pattern: 패턴 딕셔너리
        
        Returns:
            카테고리명
        """
        name = pattern.get("name", "").lower()
        description = pattern.get("description", "").lower()
        code = pattern.get("code", "").lower()
        
        # 카테고리별 키워드 매칭
        for category, keywords in self.PATTERN_CATEGORIES.items():
            for keyword in keywords:
                if keyword in name or keyword in description or keyword in code:
                    return category
        
        return "general"
    
    def vectorize_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        패턴 벡터화
        
        Args:
            patterns: 패턴 리스트
        
        Returns:
            벡터화된 패턴 리스트
        """
        logger.info(f"🔧 패턴 벡터화 중: {len(patterns)}개")
        
        if not HYBRID_VECTORIZER_AVAILABLE:
            logger.error("❌ 벡터화 모듈을 사용할 수 없습니다.")
            return patterns
        
        vectorized_patterns = []
        
        for i, pattern in enumerate(patterns):
            try:
                # 코드 설명 생성
                description = pattern.get("description", "")
                code = pattern.get("code", "")
                
                # 벡터화
                vector_result = hybrid_vectorize(description + "\n" + code[:500])  # 처음 500자만
                
                # 벡터 결과 추가
                pattern['vector_4d'] = vector_result.get("vector_4d", {})
                pattern['vector_12d'] = vector_result.get("vector_12d", [])
                pattern['dcv'] = vector_result.get("dcv", 0.5)
                pattern['pattern_type'] = vector_result.get("pattern_type")
                
                vectorized_patterns.append(pattern)
                
                if (i + 1) % 100 == 0:
                    logger.info(f"  진행: {i + 1}/{len(patterns)}")
                    
            except Exception as e:
                logger.warning(f"⚠️ 패턴 벡터화 실패 ({pattern.get('name', 'unknown')}): {e}")
                continue
        
        logger.info(f"✅ 벡터화 완료: {len(vectorized_patterns)}개")
        return vectorized_patterns
    
    def build_codebook(self, patterns: List[Dict[str, Any]], output_path: Path) -> bool:
        """
        코드북 구축 및 저장
        
        Args:
            patterns: 벡터화된 패턴 리스트
            output_path: 출력 경로
        
        Returns:
            성공 여부
        """
        logger.info(f"📚 코드북 구축 중: {len(patterns)}개 패턴")
        
        if not self.codebook_router:
            logger.error("❌ 코드북 라우터를 사용할 수 없습니다.")
            return False
        
        try:
            # 도메인별로 패턴 분류
            domain_patterns = defaultdict(list)
            for pattern in patterns:
                # 카테고리 → 도메인 매핑
                category = pattern.get("category", "general")
                domain = self._category_to_domain(category)
                domain_patterns[domain].append(pattern)
            
            # 도메인별 코드북 구축
            codebooks = {}
            for domain, domain_pats in domain_patterns.items():
                logger.info(f"  {domain.value} 도메인: {len(domain_pats)}개 패턴")
                
                # 벡터 추출
                vectors = []
                metadata = []
                for pattern in domain_pats:
                    vector_12d = pattern.get("vector_12d")
                    if vector_12d and len(vector_12d) == 12:
                        vectors.append(vector_12d)
                        metadata.append({
                            "index": len(vectors) - 1,
                            "name": pattern.get("name"),
                            "type": pattern.get("type"),
                            "category": pattern.get("category"),
                            "code": pattern.get("code", "")[:500],  # 처음 500자만
                            "description": pattern.get("description")
                        })
                
                if vectors:
                    # 코드북 구축 (간단한 버전: 벡터 평균 클러스터링)
                    import numpy as np
                    vectors_array = np.array(vectors, dtype=np.float32)
                    
                    codebooks[domain.value] = {
                        "codebook": vectors_array.tolist(),
                        "metadata": metadata,
                        "size": len(metadata)
                    }
            
            # 코드북 저장
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "version": "1.0",
                    "total_patterns": len(patterns),
                    "codebooks": codebooks,
                    "categories": dict(self.PATTERN_CATEGORIES)
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 코드북 저장 완료: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 코드북 구축 실패: {e}")
            return False
    
    def _category_to_domain(self, category: str) -> Domain:
        """카테고리를 도메인으로 변환"""
        mapping = {
            "authentication": Domain.LOGIC,
            "database": Domain.MATERIAL,
            "api": Domain.LOGIC,
            "ui": Domain.MATERIAL,
            "utils": Domain.KNOWLEDGE,
            "general": Domain.KNOWLEDGE
        }
        return mapping.get(category, Domain.KNOWLEDGE)


def main():
    """메인 함수"""
    logger.info("=" * 80)
    logger.info("📚 표준 코드북 구축 스크립트")
    logger.info("=" * 80)
    
    # 워크스페이스 루트
    workspace_root = Path(os.getenv("WORKSPACE_ROOT", "C:/workspace"))
    
    # 출력 경로
    output_path = workspace_root / "memory" / "codebooks" / "standard_codebook_v1.0.json"
    
    # 구축기 초기화
    builder = StandardCodebookBuilder(target_size=1000)
    
    # 1. 패턴 수집
    logger.info("\n[Step 1] 패턴 수집")
    patterns = builder.collect_patterns_from_workspace(workspace_root)
    
    if not patterns:
        logger.error("❌ 패턴 수집 실패")
        return
    
    # 2. 벡터화
    logger.info("\n[Step 2] 패턴 벡터화")
    vectorized_patterns = builder.vectorize_patterns(patterns)
    
    if not vectorized_patterns:
        logger.error("❌ 벡터화 실패")
        return
    
    # 3. 코드북 구축
    logger.info("\n[Step 3] 코드북 구축")
    success = builder.build_codebook(vectorized_patterns, output_path)
    
    if success:
        logger.info("\n" + "=" * 80)
        logger.info("✅ 표준 코드북 구축 완료!")
        logger.info(f"  출력 경로: {output_path}")
        logger.info(f"  총 패턴 수: {len(vectorized_patterns)}개")
        logger.info("=" * 80)
    else:
        logger.error("❌ 코드북 구축 실패")


if __name__ == "__main__":
    main()

