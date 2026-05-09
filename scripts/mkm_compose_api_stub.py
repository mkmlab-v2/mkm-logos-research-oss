#!/usr/bin/env python3
"""MKM compose API stub (orchestrator).

Run:
  uvicorn scripts.mkm_compose_api_stub:app --host 127.0.0.1 --port 8040
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_myeongni_full_report_v1 import _build_report, _from_run_cli  # noqa: E402

RESOLVER_PATH = ROOT / "docs" / "final" / "artifacts" / "conflict_resolver_v1.json"
DEFAULT_AUDIT = ROOT / "reports" / "mkm_compose_api_audit_log.jsonl"


class ComposeRequest(BaseModel):
    name: str = "user"
    query: str
    year: int
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    second: int = Field(default=0, ge=0, le=59)
    iana_tz: str = "Asia/Seoul"
    is_male: bool = False
    annual_start_year: int = datetime.now(UTC).year
    annual_years: int = Field(default=3, ge=1, le=12)


class ComposeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    schema_name: str = Field(default="mkm_compose_response_v1", alias="schema")
    generated_at_utc: str
    domain: str
    field: dict[str, Any]
    lens: dict[str, Any]
    conflict: dict[str, Any]
    final_action: dict[str, Any]
    answer_markdown: str


class _IpRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    @staticmethod
    def _rpm() -> int:
        raw = os.environ.get("MKM_COMPOSE_API_RATE_LIMIT_RPM", "0").strip()
        try:
            v = int(raw)
        except ValueError:
            return 0
        return max(0, v)

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


_limiter = _IpRateLimiter()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolver() -> dict[str, Any]:
    return _read_json(RESOLVER_PATH)


def _api_keys() -> list[str]:
    raw = os.environ.get("MKM_COMPOSE_API_KEYS", "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _auth(x_api_key: str | None, authorization: str | None) -> None:
    keys = _api_keys()
    if not keys:
        return
    token = (x_api_key or "").strip()
    auth = (authorization or "").strip()
    if not token and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token or token not in keys:
        raise HTTPException(status_code=401, detail="invalid_api_key")


def _domain(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ("btc", "kospi", "주식", "시장", "금융", "매매", "투자")):
        return "market"
    if any(k in q for k in ("건강", "아토피", "통증", "혈압", "병원", "의료")):
        return "health"
    return "general"


def _myeongni_signal(req: ComposeRequest) -> dict[str, Any]:
    birth = _from_run_cli(req.year, req.month, req.day, req.hour, req.minute, req.second, req.iana_tz, req.is_male)
    rep = _build_report(birth, req.annual_start_year, req.annual_years, 1)
    sh = ((rep.get("structure_analysis") or {}).get("day_master_strength_hint") or {})
    strength = str(sh.get("strength_label") or "")
    confidence = 0.55 if strength in {"중약", "중강"} else 0.65 if strength == "강" else 0.45
    annual_rows = ((rep.get("annual_fortune") or {}).get("rows") or [])
    first = annual_rows[0] if annual_rows else {}
    tg = str(first.get("sewoon_stem_ten_god") or "")
    direction = 0.25 if tg in {"편재", "정재", "식신"} else -0.25 if tg in {"편관", "정관"} else 0.0
    return {
        "direction_score": direction,
        "confidence": confidence,
        "signal_basis": {"strength_label": strength, "first_sewoon_ten_god": tg},
    }


def _sasang_signal(query: str, domain: str) -> dict[str, Any]:
    q = query.lower()
    risk = 0.35
    if domain == "health":
        risk = 0.7
    if any(k in q for k in ("악화", "위험", "stress", "붕괴", "통증", "가려움")):
        risk = min(1.0, risk + 0.2)
    direction = -0.3 if risk >= 0.7 else 0.1
    confidence = 0.62
    return {"direction_score": direction, "confidence": confidence, "risk_score": risk}


def _live_market_signal() -> dict[str, Any]:
    p = ROOT / "docs" / "final" / "artifacts" / "btc_market_signals_latest.json"
    if not p.is_file():
        return {"direction_score": 0.0, "confidence": 0.5, "risk_score": 0.5, "source": "fallback"}
    doc = _read_json(p)
    risk = float((doc.get("risk") or {}).get("score", 0.5)) if isinstance(doc.get("risk"), dict) else 0.5
    direction = float(doc.get("direction_score", 0.0)) if isinstance(doc.get("direction_score"), (int, float)) else 0.0
    conf = float(doc.get("confidence", 0.55)) if isinstance(doc.get("confidence"), (int, float)) else 0.55
    return {"direction_score": max(-1.0, min(1.0, direction)), "confidence": max(0.0, min(1.0, conf)), "risk_score": max(0.0, min(1.0, risk)), "source": "btc_market_signals_latest"}


def _logos_signal(query: str) -> dict[str, Any]:
    return {
        "non_gating": True,
        "narrative": "리듬·절제·과신 경계 중심의 해설 레이어",
        "query_hash12": hashlib.sha256(query.encode("utf-8")).hexdigest()[:12],
    }


def _resolve(domain: str, lens: dict[str, Any], resolver: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    w = ((resolver.get("weights") or {}).get(domain) or {})
    g = resolver.get("gates") or {}
    m = lens["myeongni"]
    s = lens["sasang"]
    l = lens["live"]
    score = (float(w.get("myeongni", 0.45)) * float(m["direction_score"])) + (
        float(w.get("sasang", 0.45)) * float(s["direction_score"])
    ) + (float(w.get("live", 0.1)) * float(l["direction_score"]))
    confidence = min(float(m["confidence"]), float(s["confidence"]), float(l["confidence"]))
    risk_sasang = float(s["risk_score"])
    risk_live = float(l["risk_score"])

    reason = "moderate_signal"
    action = "WATCH"
    if risk_sasang >= float(g.get("sasang_risk_hard_hold_cut", 0.75)):
        action = "HOLD"
        reason = "sasang_hard_risk_gate"
    elif risk_live >= float(g.get("live_risk_watch_cut", 0.65)):
        action = "WATCH"
        reason = "live_risk_watch_gate"
    elif abs(score) < float(g.get("score_watch_abs_cut", 0.2)) or confidence < float(g.get("confidence_watch_cut", 0.55)):
        action = "WATCH"
        reason = "low_score_or_confidence"
    elif (
        abs(score) >= float(g.get("score_go_abs_cut", 0.55))
        and confidence >= float(g.get("confidence_go_cut", 0.7))
        and max(risk_sasang, risk_live) < float(g.get("risk_go_max", 0.5))
    ):
        action = "GO"
        reason = "high_score_confidence_low_risk"

    conflict = {
        "score": round(score, 6),
        "confidence": round(confidence, 6),
        "risk_sasang": round(risk_sasang, 6),
        "risk_live": round(risk_live, 6),
        "policy": "conservative_override",
        "reason": reason,
    }
    final_action = {"decision": action, "action_score": round(score, 6), "confidence": round(confidence, 6)}
    return conflict, final_action


def _answer(domain: str, field: dict[str, Any], lens: dict[str, Any], conflict: dict[str, Any], final_action: dict[str, Any]) -> str:
    return (
        "## MKM Compose Brief\n"
        f"- Domain: {domain}\n"
        f"- Field: {field.get('label')}\n"
        f"- Myeongni: dir={lens['myeongni']['direction_score']}, conf={lens['myeongni']['confidence']}\n"
        f"- Sasang: dir={lens['sasang']['direction_score']}, risk={lens['sasang']['risk_score']}\n"
        f"- Live: dir={lens['live']['direction_score']}, risk={lens['live']['risk_score']}\n"
        f"- Logos: [NON_GATING] {lens['logos']['narrative']}\n"
        f"- Conflict: score={conflict['score']}, conf={conflict['confidence']}, reason={conflict['reason']}\n"
        f"- Final Action: {final_action['decision']}\n"
    )


def _append_audit(event: dict[str, Any]) -> None:
    try:
        p = Path(os.environ.get("MKM_COMPOSE_AUDIT_LOG_PATH", str(DEFAULT_AUDIT)))
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        return


app = FastAPI(title="MKM Compose API Stub", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "mkm_compose_api_stub",
        "resolver_schema": _resolver().get("schema"),
        "api_key_mode": "required" if _api_keys() else "open",
        "rate_limit_rpm": _IpRateLimiter._rpm(),
    }


@app.post("/api/v1/mkm/compose", response_model=ComposeResponse)
def compose(
    request: Request,
    req: ComposeRequest,
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> ComposeResponse:
    ts = datetime.now(UTC)
    _auth(x_api_key, authorization)
    ip = request.client.host if request.client else "unknown"
    ok, retry_after = _limiter.allow(ip, ts.timestamp())
    if not ok:
        raise HTTPException(status_code=429, detail={"code": "rate_limited", "retry_after_seconds": retry_after})

    domain = _domain(req.query)
    field = {"label": "market_regime" if domain == "market" else "wellness_context" if domain == "health" else "general_context"}
    lens = {
        "myeongni": _myeongni_signal(req),
        "sasang": _sasang_signal(req.query, domain),
        "live": _live_market_signal() if domain == "market" else {"direction_score": 0.0, "confidence": 0.5, "risk_score": 0.4, "source": "not_market_query"},
        "logos": _logos_signal(req.query),
    }
    resolver = _resolver()
    conflict, final_action = _resolve(domain, lens, resolver)
    answer_markdown = _answer(domain, field, lens, conflict, final_action)
    _append_audit(
        {
            "ts_utc": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "route": "/api/v1/mkm/compose",
            "ip": ip,
            "status_code": 200,
            "domain": domain,
            "decision": final_action["decision"],
            "query_hash12": hashlib.sha256(req.query.encode("utf-8")).hexdigest()[:12],
        }
    )
    return ComposeResponse(
        generated_at_utc=ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        domain=domain,
        field=field,
        lens=lens,
        conflict=conflict,
        final_action=final_action,
        answer_markdown=answer_markdown,
    )

