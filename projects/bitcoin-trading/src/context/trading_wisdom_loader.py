"""
trading_wisdom.jsonl 로더 — 비트코인 매매 파이프라인 RAG/conditioning용.

설계 지침 §6.3: trading_wisdom.jsonl은 4D 조건화·RAG·대화 참조용.
SFT/LoRA 훈련이 아닌, 전략 로그/메타데이터에 참조 훅으로 연동.
"""
from pathlib import Path
import json
import os
from typing import List, Dict, Any, Optional

# workspace_root: projects/bitcoin-trading/src/context/trading_wisdom_loader.py → 5단계 상위
_current = Path(__file__).resolve()
_workspace_root = _current.parent.parent.parent.parent.parent
if not _workspace_root.exists():
    _workspace_root = Path(os.getenv("WORKSPACE_ROOT", "C:/workspace")).resolve()

DEFAULT_WISDOM_PATH = _workspace_root / "data" / "distill_14b" / "trading_wisdom.jsonl"

_cached_items: Optional[List[Dict[str, Any]]] = None


def _load_lines(path: Path) -> List[Dict[str, Any]]:
    items = []
    if not path.exists():
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                items.append(obj)
            except json.JSONDecodeError:
                continue
    return items


def get_trading_wisdom_context(
    limit: int = 3,
    wisdom_path: Optional[Path] = None,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """
    trading_wisdom.jsonl에서 Q&A 목록을 로드해 RAG/conditioning용으로 반환.

    Returns:
        [ {"q": "질문", "a": "답변"}, ... ]  (최대 limit건)
    """
    global _cached_items
    path = wisdom_path or DEFAULT_WISDOM_PATH
    if use_cache and _cached_items is not None:
        items = _cached_items
    else:
        items = _load_lines(path)
        if use_cache:
            _cached_items = items

    result = []
    for obj in items[:limit]:
        messages = obj.get("messages") or []
        q, a = "", ""
        for m in messages:
            role = (m.get("role") or "").lower()
            content = (m.get("content") or "").strip()
            if role == "user":
                q = content
            elif role == "assistant":
                a = content
        if q or a:
            result.append({"q": q, "a": a})
    return result


def get_cited_trading_wisdom(limit: int = 2) -> List[Dict[str, str]]:
    """
    전략 로그/리포트에 넣을 '참조한 trading_wisdom' 포맷.
    cited_research 스타일과 유사하게 path + 요약 반환.
    """
    items = get_trading_wisdom_context(limit=limit, use_cache=True)
    return [
        {"path": "data/distill_14b/trading_wisdom.jsonl", "q": x["q"], "a": x["a"]}
        for x in items
    ]
