#!/usr/bin/env python3
"""FastAPI stub for one-shot myeongni autobot service.

Run:
  uvicorn scripts.myeongni_autobot_api_stub:app --host 127.0.0.1 --port 8030
"""

from __future__ import annotations

import os
import sys
from collections import deque
from datetime import UTC, datetime
import json
import hashlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_myeongni_full_report_v1 import _build_report, _from_run_cli  # noqa: E402
from scripts.run_myeongni_autobot_v1 import _bot_answer  # noqa: E402


class MyeongniAutobotRequest(BaseModel):
    name: str = "user"
    year: int
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    second: int = Field(default=0, ge=0, le=59)
    iana_tz: str = "Asia/Seoul"
    is_male: bool = False
    user_prompt: str = ""
    annual_start_year: int = datetime.now(UTC).year
    annual_years: int = Field(default=5, ge=1, le=20)
    monthly_months_per_year: int = Field(default=3, ge=0, le=12)


class MyeongniAutobotResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    schema_name: str = Field(default="myeongni_autobot_response_v1", alias="schema")
    generated_at_utc: str
    name: str
    answer_markdown: str
    report: dict[str, Any]


app = FastAPI(title="MKM Myeongni Autobot API Stub", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _IpRateLimiter:
    """Simple in-memory IP rate limiter.

    Env:
    - MYEONGNI_AUTOBOT_RATE_LIMIT_RPM (default: 0 = disabled)
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    @staticmethod
    def _rpm() -> int:
        raw = os.environ.get("MYEONGNI_AUTOBOT_RATE_LIMIT_RPM", "0").strip()
        try:
            val = int(raw)
        except ValueError:
            return 0
        return max(0, val)

    def allow(self, key: str, now_ts: float) -> tuple[bool, int | None]:
        rpm = self._rpm()
        if rpm <= 0:
            return True, None
        q = self._hits.setdefault(key, deque())
        cutoff = now_ts - 60.0
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= rpm:
            retry_after = max(1, int(60 - (now_ts - q[0])))
            return False, retry_after
        q.append(now_ts)
        return True, None


_rate_limiter = _IpRateLimiter()
DEFAULT_AUDIT_LOG = ROOT / "reports" / "myeongni_autobot_api_audit_log.jsonl"


def _api_key_list() -> list[str]:
    raw = os.environ.get("MYEONGNI_AUTOBOT_API_KEYS", "").strip()
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def _validate_api_key(x_api_key: str | None, authorization: str | None) -> None:
    keys = _api_key_list()
    if not keys:
        # Dev/local default: no keys configured means open.
        return
    token = (x_api_key or "").strip()
    auth = (authorization or "").strip()
    if not token and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token or token not in keys:
        raise HTTPException(status_code=401, detail="invalid_api_key")


def _audit_log_path() -> Path:
    raw = os.environ.get("MYEONGNI_AUTOBOT_AUDIT_LOG_PATH", "").strip()
    if raw:
        return Path(raw)
    return DEFAULT_AUDIT_LOG


def _sha256_12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _append_audit(event: dict[str, Any]) -> None:
    try:
        p = _audit_log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Audit log failure must not break API response path.
        return


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "myeongni_autobot_api_stub",
        "version": "1.0.0",
        "api_key_mode": "required" if len(_api_key_list()) > 0 else "open",
        "rate_limit_rpm": _IpRateLimiter._rpm(),
    }


@app.post("/api/v1/myeongni/autobot", response_model=MyeongniAutobotResponse)
def run_myeongni_autobot(
    request: Request,
    req: MyeongniAutobotRequest,
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> MyeongniAutobotResponse:
    ts = datetime.now(UTC)
    _validate_api_key(x_api_key, authorization)
    client_ip = request.client.host if request.client else "unknown"
    ok, retry_after = _rate_limiter.allow(client_ip, ts.timestamp())
    if not ok:
        _append_audit(
            {
                "ts_utc": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "route": "/api/v1/myeongni/autobot",
                "ip": client_ip,
                "status_code": 429,
                "reason": "rate_limited",
                "retry_after_seconds": retry_after,
            }
        )
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": "too_many_requests_per_ip",
                "retry_after_seconds": retry_after,
            },
        )
    birth = _from_run_cli(
        req.year,
        req.month,
        req.day,
        req.hour,
        req.minute,
        req.second,
        req.iana_tz,
        req.is_male,
    )
    report = _build_report(
        birth,
        req.annual_start_year,
        req.annual_years,
        req.monthly_months_per_year,
    )
    answer = _bot_answer(report, req.user_prompt)
    _append_audit(
        {
            "ts_utc": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "route": "/api/v1/myeongni/autobot",
            "ip": client_ip,
            "status_code": 200,
            "name": req.name,
            "birth_key": f"{req.year:04d}-{req.month:02d}-{req.day:02d}",
            "tz": req.iana_tz,
            "is_male": req.is_male,
            "annual_start_year": req.annual_start_year,
            "annual_years": req.annual_years,
            "monthly_months_per_year": req.monthly_months_per_year,
            "prompt_hash12": _sha256_12(req.user_prompt or ""),
            "api_key_mode": "required" if len(_api_key_list()) > 0 else "open",
        }
    )
    return MyeongniAutobotResponse(
        generated_at_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        name=req.name,
        answer_markdown=answer,
        report=report,
    )

