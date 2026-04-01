# 14B+4D-Native 감찰/제언용 클라이언트
from .llm_14b_advisory import get_14b_advisory
from .local_ops_llm import LocalOpsLlmClient

__all__ = ["get_14b_advisory", "LocalOpsLlmClient"]
