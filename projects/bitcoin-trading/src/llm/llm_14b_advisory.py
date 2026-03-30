#!/usr/bin/env python3
"""
14B+4D-Native 감찰/제언용 클라이언트

비트코인 매매 통찰 알림 시 선택적으로 14B 추론을 호출하여 한 문장 제언을 추가.
- Option B: server_url 설정 시 HTTP POST /infer 우선 (180초→15초 최적화)
- Fallback: run_sft_14b_inference.py를 서브프로세스로 호출 (기본 sft_14b LoRA + 4D-Native).

SSOT: `AGENTS.md` — 본 모듈은 **감찰(Auditor) 전용**. 거래소·주문 API 클라이언트를
import 하거나 주문을 실행하지 않는다. 주문 직전 게이트는 `oracle_gateway.py`가 담당.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from collections import Counter
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

__all__ = ("get_14b_advisory", "warmup_14b_server_if_configured")

# 품질 검증 실패 시 반환할 안전 문구 (알림에 깨진 문장 노출 방지)
FALLBACK_ADVISORY = "14B 제언: (출력 품질 검증 실패로 생략)"
FALLBACK_TIMEOUT = "14B 제언: (추론 시간 초과로 생략)"

# 품질 실패 시 원문 보존: LOG_14B_ADVISORY_RAW=1 이면 workspace 로그에 raw 출력 기록
LOG_14B_RAW_ENV = "LOG_14B_ADVISORY_RAW"

# Option B: 서버 모드 시 워밍업 완료한 URL (프로세스당 1회)
_warmed_server_urls: set = set()


def warmup_14b_server_if_configured() -> None:
    """
    Evolution Loop / Oracle 시작 전 14B 서버 워밍업.
    trading_config.yaml에 llm_14b.server_url이 있으면 1회 워밍업 실행.
    """
    if requests is None:
        return
    try:
        from src.config.config_loader import ConfigLoader
        loader = ConfigLoader()
        loader.load()
        call_path = loader.get_14b_4d_native_call_path()
        server_url = (call_path or {}).get("server_url")
        if server_url and isinstance(server_url, str):
            _warmup_14b_server(server_url)
    except Exception as e:
        logger.debug("14B 워밍업 스킵: %s", e)


def _warmup_14b_server(server_url: str) -> None:
    """Evolution Loop / Oracle 시작 전 cold start 완화용. 프로세스당 1회만 실행."""
    if server_url in _warmed_server_urls or requests is None:
        return
    _warmed_server_urls.add(server_url)
    try:
        url = server_url.rstrip("/") + "/infer"
        requests.post(
            url,
            json={"prompt": "테스트", "max_new_tokens": 1},
            timeout=30,
        )
        logger.debug("14B 서버 워밍업 완료: %s", server_url)
    except Exception as e:
        logger.debug("14B 워밍업 실패(무시): %s", e)


def _is_garbled(text: str) -> bool:
    """
    출력이 깨졌는지 휴리스틱 판단.
    - 한글·라틴·숫자·기본 문장부호 비율이 너무 낮으면 깨진 것으로 간주
    - 동일 단어/음절이 반복되면 깨진 것으로 간주
    - 키릴·CJK(비한글) 혼재 시 깨진 것으로 간주
    """
    if not text or len(text.strip()) < 5:
        return True
    allowed = re.compile(r"[가-힣a-zA-Z0-9\s.,!?\-%]")
    allowed_count = sum(1 for c in text if allowed.match(c))
    if len(text) > 20 and (allowed_count / len(text)) < 0.55:
        return True
    # 키릴·CJK(한글 제외) 문자가 있으면 감찰 제언으로는 부적절
    if re.search(r"[\u0400-\u04FF\u4e00-\u9fff]", text):
        return True
    # 반복 패턴 (동일 단어 4회 이상)
    words = re.findall(r"\b\w{2,}\b", text)
    if len(words) >= 8:
        most = Counter(words).most_common(1)[0]
        if most[1] >= 4:
            return True
    # 부분문자열 4회 이상 반복 (예: holmholmholm)
    for width in (4, 5, 6):
        for i in range(len(text) - width * 3):
            sub = text[i : i + width]
            if text.count(sub) >= 4:
                return True
    return False


def _save_raw_advisory_debug(root: Path, prompt_preview: str, raw_block: str) -> None:
    """품질 실패 시 원문을 로그 디렉터리에 기록 (LOG_14B_ADVISORY_RAW=1일 때)."""
    try:
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        out = log_dir / "14b_advisory_raw_fail.txt"
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"--- prompt_preview: {prompt_preview!r} ---\n{raw_block}\n\n")
        logger.info("14B raw (garbled) saved to %s", out)
    except Exception as e:
        logger.warning("Failed to save 14B raw advisory: %s", e)


def get_14b_advisory(
    prompt: str,
    call_path: Dict[str, Any],
    timeout_sec: int = 120,
    workspace_root: Optional[Path] = None,
) -> Optional[str]:
    """
    14B+4D-Native 추론 1회 실행 후 첫 응답 텍스트 반환.
    call_path에 server_url이 있으면 HTTP POST /infer 우선 (Option B 최적화).

    Args:
        prompt: 사용자 프롬프트 한 줄.
        call_path: get_14b_4d_native_call_path() 반환값.
            {"adapter_dir": Path, "inference_script": Path, "server_url": str|None}
        timeout_sec: 서브프로세스/HTTP 타임아웃(초).
        workspace_root: 작업 디렉토리(기본: inference_script 기준 상위 3단계).

    Returns:
        첫 응답 문자열 또는 실패 시 None.
    """
    server_url = call_path.get("server_url")
    if server_url and isinstance(server_url, str) and requests is not None:
        _warmup_14b_server(server_url)
        try:
            url = server_url.rstrip("/") + "/infer"
            resp = requests.post(
                url,
                json={"prompt": prompt.strip(), "max_new_tokens": 128},
                timeout=min(30, timeout_sec),
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data.get("error"), str):
                logger.warning("14B HTTP error: %s", data["error"])
                raise ValueError(data["error"])
            first_block = (data.get("response") or "").strip()
            if not first_block:
                raise ValueError("empty response")
            if _is_garbled(first_block):
                logger.debug("14B HTTP 출력 품질 검증 실패(깨짐)")
                return FALLBACK_ADVISORY
            return first_block
        except (
            requests.RequestException,
            TimeoutError,
            ConnectionError,
            KeyError,
            ValueError,
        ) as e:
            logger.warning("14B HTTP 추론 실패, subprocess fallback: %s", e)

    adapter_dir = call_path.get("adapter_dir")
    inference_script = call_path.get("inference_script")
    if not adapter_dir or not inference_script or not adapter_dir.is_dir() or not inference_script.is_file():
        logger.debug("14B call_path 불완전하여 스킵")
        return None

    root = workspace_root
    if root is None:
        # scripts/sse2_pure_essence/run_sft_14b_inference.py -> workspace
        root = inference_script.resolve().parent.parent.parent

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as f_prompt:
        f_prompt.write(prompt.strip() + "\n")
        prompts_path = Path(f_prompt.name)

    out_path = Path(tempfile.gettempdir()) / f"14b_advisory_out_{id(prompt)}.txt"
    try:
        cmd = [
            "py",
            str(inference_script.resolve()),
            "--4d-native",
            str(adapter_dir.resolve()),
            "--prompts",
            str(prompts_path),
            "--max-prompts",
            "1",
            "--max-new-tokens",
            "128",
            "--repetition-penalty",
            "1.3",
            "--output",
            str(out_path),
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            logger.warning("14B 추론 실패: returncode=%s stderr=%s", proc.returncode, proc.stderr[:200] if proc.stderr else "")
            return None
        if not out_path.is_file():
            return None
        text = out_path.read_text(encoding="utf-8").strip()
        # Phase C 형식: 빈 줄로 구분된 블록; 1개만 요청했으므로 첫 블록만
        first_block = text.split("\n\n")[0].strip() if text else ""
        if not first_block:
            return None
        if _is_garbled(first_block):
            logger.debug("14B 출력 품질 검증 실패(깨짐), fallback 문구 반환")
            if os.environ.get(LOG_14B_RAW_ENV):
                _save_raw_advisory_debug(root, prompt[:80], first_block)
            return FALLBACK_ADVISORY
        return first_block
    except subprocess.TimeoutExpired:
        logger.warning("14B 추론 타임아웃 (%s초)", timeout_sec)
        return FALLBACK_TIMEOUT
    except Exception as e:
        logger.warning("14B 추론 예외: %s", e)
        return None
    finally:
        prompts_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)
