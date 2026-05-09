#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배치/CI용 Gemini 멀티모달 호출 — Cursor `aistudio-mcp`의 generate_content와 동일한 전술 축을
google-genai SDK로 재현한다 (IDE 밖 실행·스케줄러·파이프라인 편입).

의존성: pip install google-genai
인증: 환경 변수 GEMINI_API_KEY 또는 GOOGLE_API_KEY. Client에는 _api_key()로 읽은 값을 명시 전달(GEMINI 우선).
  두 변수가 모두 있으면 google-genai가 경고 로그를 낼 수 있으나, 전달한 api_key가 요청에 사용됨.

예:
  py scripts/gemini_multimodal_batch.py check
  py scripts/gemini_multimodal_batch.py research --file paper.pdf --prompt "요약해 줘" --timeout 600
  py scripts/gemini_multimodal_batch.py image --prompt "pixel character, flat vector" --out-dir ./out
  py scripts/gemini_multimodal_batch.py crosscheck --file chart.png --meta "BTC 4h Binance 2026-04-01Z"
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from google import genai
from google.genai import types

MAX_FILES = 10

DEFAULT_MODEL_RESEARCH = "gemini-2.5-flash"
DEFAULT_MODEL_IMAGE = "gemini-2.5-flash-image"

# HTTP 전체 타임아웃(초; 클라이언트에는 ms로 전달). 미설정 시 SDK 기본에 맡겨 장시간 대기처럼 보일 수 있음.
DEFAULT_TIMEOUT_RESEARCH_S = 900
DEFAULT_TIMEOUT_IMAGE_S = 300
DEFAULT_TIMEOUT_CROSSCHECK_S = 900
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USAGE_LOG = ROOT / "reports" / "gemini_batch" / "usage_log.jsonl"


def _api_key() -> Optional[str]:
    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )


def _mime_for_path(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        return mime
    suf = path.suffix.lower()
    fallback = {
        ".md": "text/markdown",
        ".json": "application/json",
        ".csv": "text/csv",
    }
    return fallback.get(suf, "application/octet-stream")


def _file_parts(paths: Iterable[Path]) -> List[types.Part]:
    parts: List[types.Part] = []
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError(f"파일 없음: {p}")
        data = p.read_bytes()
        parts.append(types.Part.from_bytes(data=data, mime_type=_mime_for_path(p)))
    return parts


def _build_tools(
    *,
    google_search: bool,
    code_execution: bool,
) -> List[types.Tool]:
    tools: List[types.Tool] = []
    if google_search:
        tools.append(types.Tool(google_search=types.GoogleSearch()))
    if code_execution:
        tools.append(types.Tool(code_execution=types.ToolCodeExecution()))
    return tools


def _thinking_config(budget: int) -> Optional[types.ThinkingConfig]:
    if budget == 0:
        return None
    return types.ThinkingConfig(thinking_budget=budget)


def _make_client(api_key: str, timeout_sec: int) -> genai.Client:
    # google.genai HttpOptions.timeout is milliseconds; API minimum deadline is 10s.
    timeout_ms = max(10_000, int(timeout_sec) * 1000)
    http = types.HttpOptions(timeout=timeout_ms)
    # Force AI Studio key route when API key is present.
    # Some environments set GOOGLE_GENAI_USE_VERTEXAI=1 globally, which causes
    # image generation to fail with 401 unless OAuth credentials are configured.
    return genai.Client(api_key=api_key, vertexai=False, http_options=http)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _usage_counts(log_path: Path) -> tuple[int, int]:
    """Return (daily_count, monthly_count) for current UTC day/month."""
    now = datetime.now(timezone.utc)
    day_key = now.strftime("%Y-%m-%d")
    month_key = now.strftime("%Y-%m")
    daily = 0
    monthly = 0
    if not log_path.is_file():
        return daily, monthly
    for line in log_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        ts = str(row.get("ts_utc") or "")
        if ts.startswith(day_key):
            daily += 1
        if ts.startswith(month_key):
            monthly += 1
    return daily, monthly


def _append_usage(log_path: Path, *, command: str, model: str | None) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "gemini_batch_usage_v1",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": command,
        "model": model or "",
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _enforce_budget_guard(ns: argparse.Namespace) -> int:
    """Return 0 when allowed; 3 when blocked by daily/monthly caps."""
    if getattr(ns, "budget_bypass", False):
        return 0
    log_path = Path(ns.usage_log) if ns.usage_log else DEFAULT_USAGE_LOG
    daily_cap = _env_int("GEMINI_BATCH_DAILY_MAX_CALLS", 25)
    monthly_cap = _env_int("GEMINI_BATCH_MONTHLY_MAX_CALLS", 400)
    daily, monthly = _usage_counts(log_path)
    if daily_cap > 0 and daily >= daily_cap:
        print(
            f"예산 가드 차단: 일일 호출 상한 도달 ({daily}/{daily_cap}). "
            f"--budget-bypass 또는 GEMINI_BATCH_DAILY_MAX_CALLS 조정 필요.",
            file=sys.stderr,
        )
        return 3
    if monthly_cap > 0 and monthly >= monthly_cap:
        print(
            f"예산 가드 차단: 월간 호출 상한 도달 ({monthly}/{monthly_cap}). "
            f"--budget-bypass 또는 GEMINI_BATCH_MONTHLY_MAX_CALLS 조정 필요.",
            file=sys.stderr,
        )
        return 3
    return 0


def _call_generate(client: genai.Client, **kwargs):
    try:
        return client.models.generate_content(**kwargs)
    except Exception as e:
        msg = str(e).lower()
        if "timeout" in msg or "timed out" in msg:
            print(
                "요청 시간 초과(HTTP timeout). --timeout 값을 늘리거나, "
                "thinking/검색/코드 실행을 줄여 재시도하세요.",
                file=sys.stderr,
            )
        raise


def cmd_research(ns: argparse.Namespace) -> int:
    paths = [Path(p) for p in ns.file]
    if len(paths) > MAX_FILES:
        print(f"파일은 최대 {MAX_FILES}개까지.", file=sys.stderr)
        return 2

    parts: List[types.Part] = [types.Part.from_text(text=ns.prompt)]
    parts.extend(_file_parts(paths))

    tools = _build_tools(google_search=ns.google_search, code_execution=ns.code_execution)
    cfg = types.GenerateContentConfig(
        system_instruction=ns.system or None,
        temperature=ns.temperature,
        tools=tools or None,
        thinking_config=_thinking_config(ns.thinking_budget),
    )

    client = _make_client(_api_key() or "", ns.timeout)
    resp = _call_generate(
        client,
        model=ns.model,
        contents=parts,
        config=cfg,
    )
    print(resp.text or "")
    return 0


def _save_image_parts(resp: genai.types.GenerateContentResponse, out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    idx = 0
    cands = resp.candidates or []
    for cand in cands:
        content = cand.content
        if not content or not content.parts:
            continue
        for part in content.parts:
            if not part.inline_data or not part.inline_data.data:
                continue
            mime = part.inline_data.mime_type or "image/png"
            ext = ".png" if "png" in mime else ".jpg" if "jpeg" in mime or "jpg" in mime else ".bin"
            idx += 1
            name = f"gemini_image_{idx}{ext}"
            path = out_dir / name
            path.write_bytes(part.inline_data.data)
            saved.append(path)
    return saved


def cmd_image(ns: argparse.Namespace) -> int:
    modalities: List[types.Modality] = (
        [types.Modality.IMAGE]
        if ns.only_image
        else [types.Modality.TEXT, types.Modality.IMAGE]
    )
    # Gemini API(google-genai) 경로에서는 ImageConfig.output_mime_type 등 일부 필드가 거절될 수 있음.
    img_cfg: Optional[types.ImageConfig] = None
    if ns.aspect_ratio:
        img_cfg = types.ImageConfig(aspect_ratio=ns.aspect_ratio)
    cfg = types.GenerateContentConfig(
        system_instruction=ns.system or None,
        temperature=ns.temperature,
        response_modalities=modalities,
        image_config=img_cfg,
    )

    client = _make_client(_api_key() or "", ns.timeout)
    resp = _call_generate(
        client,
        model=ns.model,
        contents=ns.prompt,
        config=cfg,
    )

    if ns.out_dir:
        out = Path(ns.out_dir)
        paths = _save_image_parts(resp, out)
        for p in paths:
            print(str(p.resolve()))
        if not ns.only_image and (resp.text or "").strip():
            print("\n--- text ---\n")
            print(resp.text)
        return 0

    # data URI 스타일: 콘솔에는 메타만 (base64 전체는 토큰·로그 폭주 방지)
    print(json.dumps({"text": resp.text, "candidates": len(resp.candidates or [])}, ensure_ascii=False))
    return 0


def cmd_crosscheck(ns: argparse.Namespace) -> int:
    paths = [Path(p) for p in ns.file]
    if len(paths) > MAX_FILES:
        print(f"파일은 최대 {MAX_FILES}개까지.", file=sys.stderr)
        return 2

    meta = ns.meta or ""
    body = (
        f"{ns.prompt}\n\n"
        f"[캡처 메타데이터 — 모델이 과신하지 않도록 반드시 참고]\n{meta}"
    )
    parts: List[types.Part] = [types.Part.from_text(text=body)]
    parts.extend(_file_parts(paths))

    tools = _build_tools(google_search=True, code_execution=False)
    cfg = types.GenerateContentConfig(
        system_instruction=ns.system or None,
        temperature=ns.temperature,
        tools=tools,
        thinking_config=_thinking_config(ns.thinking_budget),
    )

    client = _make_client(_api_key() or "", ns.timeout)
    resp = _call_generate(
        client,
        model=ns.model,
        contents=parts,
        config=cfg,
    )
    print(resp.text or "")
    return 0


def cmd_check(_ns: argparse.Namespace) -> int:
    """키·네트워크 없이 SDK·임포트만 검증."""
    import importlib.util

    spec = importlib.util.find_spec("google.genai")
    ok = spec is not None
    print("google.genai:", "OK" if ok else "MISSING")
    if not ok:
        return 2
    key = _api_key()
    g = os.getenv("GEMINI_API_KEY")
    o = os.getenv("GOOGLE_API_KEY")
    print("GEMINI_API_KEY:", "set" if g else "unset")
    print("GOOGLE_API_KEY:", "set" if o else "unset")
    if g:
        print("active_key_source: GEMINI_API_KEY (우선)")
    elif o:
        print("active_key_source: GOOGLE_API_KEY")
    else:
        print("active_key_source: none (배치 호출 전에 설정)")
    print("combined:", "set" if key else "not set")
    if g and o:
        print(
            "hint: GEMINI만 사용 시 사용자 환경 변수의 GOOGLE_API_KEY(레거시)를 비우면 "
            "google-genai 경고가 줄어듦",
        )
    tiny = Path(os.environ.get("TEMP", ".")) / "gemini_batch_mime_probe.txt"
    tiny.write_text("ok", encoding="utf-8")
    try:
        m = _mime_for_path(tiny)
        print(f"mime probe ({tiny.name}): {m}")
    finally:
        try:
            tiny.unlink()
        except OSError:
            pass
    print("CLI: py scripts/gemini_multimodal_batch.py {research,image,crosscheck} --help")
    return 0


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SEC",
        help="HTTP 전체 타임아웃(초). 서브커맨드별 기본값 사용 시 생략 가능",
    )
    common.add_argument(
        "--usage-log",
        default=str(DEFAULT_USAGE_LOG),
        help="호출 카운트 JSONL 경로 (기본 reports/gemini_batch/usage_log.jsonl).",
    )
    common.add_argument(
        "--budget-bypass",
        action="store_true",
        help="일일/월간 호출 상한 가드를 일시 우회.",
    )

    p = argparse.ArgumentParser(
        description="Gemini 멀티모달 배치 (aistudio-mcp generate_content 전술 대응)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser(
        "research",
        parents=[common],
        help="PDF/이미지 등 + 검색 + (선택) 코드 실행 + thinking",
    )
    pr.add_argument(
        "--model",
        default=DEFAULT_MODEL_RESEARCH,
        help=f"모델 id (기본 {DEFAULT_MODEL_RESEARCH})",
    )
    pr.add_argument("--file", "-f", action="append", default=[], required=True, help="입력 파일 경로 (여러 번 가능)")
    pr.add_argument("--prompt", "-p", required=True)
    pr.add_argument("--system", "-s", default=None)
    pr.add_argument("--temperature", type=float, default=0.2)
    pr.add_argument("--google-search", action="store_true", help="Google Search 도구")
    pr.add_argument("--code-execution", action="store_true", help="코드 실행 도구")
    pr.add_argument(
        "--thinking-budget",
        type=int,
        default=-1,
        help="-1=무제한(모델 지원 시), 0=끔",
    )
    pr.set_defaults(func=cmd_research, _timeout_default=DEFAULT_TIMEOUT_RESEARCH_S)

    pi = sub.add_parser(
        "image",
        parents=[common],
        help="이미지 생성 (저장 시 base64를 콘솔에 안 뿌림)",
    )
    pi.add_argument("--prompt", "-p", required=True)
    pi.add_argument("--system", "-s", default=None)
    pi.add_argument("--temperature", type=float, default=0.2)
    pi.add_argument(
        "--model",
        default=DEFAULT_MODEL_IMAGE,
        help=f"기본: {DEFAULT_MODEL_IMAGE}",
    )
    pi.add_argument("--only-image", action="store_true", help="응답 모달리티 IMAGE 위주")
    pi.add_argument("--out-dir", "-o", default=None, help="저장 디렉터리 (지정 시 PNG 등으로 기록)")
    pi.add_argument("--aspect-ratio", default=None, help="예: 1:1, 16:9 (모델/플랜 지원 시)")
    pi.set_defaults(func=cmd_image, _timeout_default=DEFAULT_TIMEOUT_IMAGE_S)

    pc = sub.add_parser(
        "crosscheck",
        parents=[common],
        help="비전 + Google Search 교차 검증 (차트 등)",
    )
    pc.add_argument(
        "--model",
        default=DEFAULT_MODEL_RESEARCH,
        help=f"모델 id (기본 {DEFAULT_MODEL_RESEARCH})",
    )
    pc.add_argument("--file", "-f", action="append", default=[], required=True)
    pc.add_argument(
        "--prompt",
        "-p",
        default=(
            "이미지에 보이는 차트 구조를 설명하고, Google 검색으로 확인한 최근 매크로 뉴스와 "
            "모순이 있으면 지적하라. 불확실하면 불확실로 표시하라."
        ),
    )
    pc.add_argument("--system", "-s", default=None)
    pc.add_argument("--meta", "-m", default="", help="심볼·타임프레임·캡처 시각 등")
    pc.add_argument("--temperature", type=float, default=0.2)
    pc.add_argument("--thinking-budget", type=int, default=-1)
    pc.set_defaults(func=cmd_crosscheck, _timeout_default=DEFAULT_TIMEOUT_CROSSCHECK_S)

    pch = sub.add_parser("check", help="SDK·환경 로컬 점검 (API 호출 없음)")
    pch.set_defaults(func=cmd_check)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "check":
        return int(args.func(args))

    if not _api_key():
        print("GEMINI_API_KEY 또는 GOOGLE_API_KEY 가 필요합니다.", file=sys.stderr)
        return 2

    td = getattr(args, "_timeout_default", 600)
    if args.timeout is None:
        args.timeout = td

    budget_rc = _enforce_budget_guard(args)
    if budget_rc != 0:
        return budget_rc

    try:
        rc = int(args.func(args))
        if rc == 0:
            _append_usage(
                Path(args.usage_log) if args.usage_log else DEFAULT_USAGE_LOG,
                command=args.command,
                model=getattr(args, "model", None),
            )
        return rc
    except KeyboardInterrupt:
        print("중단됨.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
