# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.7, M:0.7}
# Balance: 88
# Purpose: Provide minimal Pixel Universe agent onboarding API stubs.
# Keywords: fastapi, agent_profile_v1, register, message, governance
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pixel Universe platform API stubs (enterprise skeleton)."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import hmac
import os
import secrets
from threading import Lock
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/v1/pixel-universe", tags=["Pixel Universe"])

_REGISTRY_LOCK = Lock()
_AUDIT_LOCK = Lock()
_AGENT_REGISTRY: dict[str, dict[str, Any]] = {}
_TOKEN_INDEX: dict[str, str] = {}
_RATE_STATE: dict[str, deque[float]] = {}
_ASYNC_QUEUE: list[dict[str, Any]] = []
_GOVERNANCE_AUDIT_EVENTS: list[dict[str, Any]] = []
_METRICS = {
    "registered_agents_total": 0,
    "messages_total": 0,
    "messages_allowed_total": 0,
    "messages_blocked_total": 0,
    "auth_fail_total": 0,
    "rate_limit_exceeded_total": 0,
    "billing_charged_krw_total": 0,
    "queued_jobs_total": 0,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_rate_window_sec() -> int:
    raw = os.getenv("PIXEL_UNIVERSE_RATE_WINDOW_SEC", "60").strip()
    try:
        value = int(raw)
    except Exception:
        value = 60
    return max(1, value)


def _default_rate_limit_per_min() -> int:
    raw = os.getenv("PIXEL_UNIVERSE_RATE_LIMIT_PER_MIN", "60").strip()
    try:
        value = int(raw)
    except Exception:
        value = 60
    return max(1, value)


def _governance_audit_log_path() -> str:
    return os.getenv(
        "PIXEL_UNIVERSE_GOV_AUDIT_LOG",
        "C:/workspace/reports/pixel_universe/governance_audit_latest.jsonl",
    ).strip()


def _append_governance_audit(entry: dict[str, Any]) -> None:
    path = _governance_audit_log_path()
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with _AUDIT_LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{entry}\n".replace("'", "\""))


def _label_to_seed(label: str) -> dict[str, float]:
    key = (label or "").strip().lower()
    mapping = {
        "nurture": {"S": 0.85, "L": 0.75, "K": 0.35, "M": 0.55},
        "analysis": {"S": 0.55, "L": 0.45, "K": 0.8, "M": 0.5},
        "judgement": {"S": 0.35, "L": 0.25, "K": 0.9, "M": 0.3},
        "mercy": {"S": 0.75, "L": 0.9, "K": 0.3, "M": 0.85},
    }
    return mapping.get(key, {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5})


def _compose_seed(primary: str, secondary: str) -> dict[str, float]:
    p = _label_to_seed(primary)
    s = _label_to_seed(secondary)
    return {
        axis: round((p[axis] * 0.7) + (s[axis] * 0.3), 6)
        for axis in ("S", "L", "K", "M")
    }


def _cluster_from_seed(seed: dict[str, float]) -> str:
    if seed["S"] >= 0.7 and seed["L"] >= 0.65:
        return "LIFE_CLUSTER_EAST"
    if seed["K"] >= 0.75:
        return "CAPITAL_CLUSTER_WEST"
    return "MIXED_CLUSTER_CENTER"


def _pixel_position(seed: dict[str, float], size: int = 24) -> dict[str, int]:
    x = int(seed["L"] * (size - 1))
    y = int(seed["K"] * (size - 1))
    return {"x": max(0, min(size - 1, x)), "y": max(0, min(size - 1, y))}


def _message_risk(text: str) -> float:
    lowered = text.lower()
    risky_terms = ("파괴", "폭파", "destroy", "hack", "우회", "jailbreak")
    hit = any(token in lowered for token in risky_terms)
    return 0.92 if hit else 0.18


def _infer_intents(message: str, requested_action: str) -> set[str]:
    lowered = f"{message} {requested_action}".lower()
    intents: set[str] = set()
    if any(t in lowered for t in ("폭파", "파괴", "destroy", "explosion", "violence")):
        intents.add("violence")
    if any(t in lowered for t in ("우회", "해킹", "hack", "bypass", "jailbreak")):
        intents.add("security_bypass")
    if any(t in lowered for t in ("trade", "order", "asset_move")):
        intents.add("financial_execution")
    return intents


def _detect_language(text: str) -> str:
    if any("\uac00" <= ch <= "\ud7a3" for ch in text):
        return "ko"
    if all(ord(ch) < 128 for ch in text):
        return "en"
    return "other"


def _normalize_text_to_semantic_vector(text: str) -> dict[str, float]:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    axes = ("S", "L", "K", "M")
    out = {}
    for i, axis in enumerate(axes):
        chunk = digest[i * 8 : (i + 1) * 8]
        out[axis] = round(int(chunk, 16) / 0xFFFFFFFF, 6)
    return out


def _parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def _verify_agent_token(agent_id: str, authorization: str | None) -> str:
    token = _parse_bearer_token(authorization)
    if token is None:
        _METRICS["auth_fail_total"] += 1
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "missing_bearer_token"})
    owner = _TOKEN_INDEX.get(token)
    if owner != agent_id:
        _METRICS["auth_fail_total"] += 1
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "invalid_token"})
    return token


def _enforce_rate_limit(token: str, now_ts: float, per_min_limit: int) -> None:
    window_sec = _default_rate_window_sec()
    bucket = _RATE_STATE.setdefault(token, deque())
    while bucket and (now_ts - bucket[0]) > window_sec:
        bucket.popleft()
    if len(bucket) >= per_min_limit:
        _METRICS["rate_limit_exceeded_total"] += 1
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"error": "rate_limit_exceeded"})
    bucket.append(now_ts)


def _get_rate_limit_for_record(record: dict[str, Any]) -> int:
    default_limit = _default_rate_limit_per_min()
    profile = record.get("profile", {})
    gov = profile.get("governance_clearance", {})
    override = gov.get("rate_limit_per_min")
    if isinstance(override, int) and override > 0:
        return override
    return default_limit


class AgentIdentity(BaseModel):
    agent_id: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    name: str = Field(min_length=1, max_length=120)
    developer: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)


class SeedMapping(BaseModel):
    primary_trait: str = Field(min_length=1, max_length=64)
    secondary_trait: str = Field(min_length=1, max_length=64)


class GovernanceClearance(BaseModel):
    policy_version: str = Field(min_length=1, max_length=64)
    safety_level: Literal["Tier-1", "Tier-2", "Tier-3"]
    allowed_actions: list[str] = Field(default_factory=list)
    prohibited_intents: list[str] = Field(default_factory=list)
    human_override_required: bool = True
    audit_consent: bool = True
    violation_penalty: Literal["warn", "block", "suspend"] = "block"
    rate_limit_per_min: int = Field(default=60, ge=1, le=10000)


class EconomyProfile(BaseModel):
    billing_key: str = Field(min_length=3, max_length=256)
    api_call_fee_krw: int = Field(ge=0, le=1_000_000)


class AgentProfileV1(BaseModel):
    identity: AgentIdentity
    four_d_seed_mapping: SeedMapping
    governance_clearance: GovernanceClearance
    economy: EconomyProfile


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    schema_id: Literal["agent_profile_v1"] = Field(default="agent_profile_v1", alias="schema")
    profile: AgentProfileV1


class RegisterResponse(BaseModel):
    status: Literal["registered", "updated"]
    agent_id: str
    bearer_token: str
    cluster: str
    pixel_position: dict[str, int]
    registered_at_utc: str
    trace_ref: str


class MessageRequest(BaseModel):
    agent_id: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    message: str = Field(min_length=1, max_length=1000)
    requested_action: str = Field(default="observe", max_length=120)


class MessageResponse(BaseModel):
    decision: Literal["allow", "block"]
    reason_codes: list[str]
    risk_score: float = Field(ge=0.0, le=1.0)
    normalized_language: str
    semantic_vector_4d: dict[str, float]
    charged_krw: int = Field(ge=0)
    remaining_credits_krw: int = Field(ge=0)
    governance_policy_version: str
    cluster: str
    trace_ref: str
    processed_at_utc: str


class AsyncAcceptedResponse(BaseModel):
    status: Literal["accepted"]
    job_id: str
    queue_depth: int
    accepted_at_utc: str
    trace_ref: str


class MetricsResponse(BaseModel):
    registered_agents_total: int
    active_tokens: int
    messages_total: int
    block_rate: float
    auth_fail_total: int
    rate_limit_exceeded_total: int
    billing_charged_krw_total: int
    queued_jobs_total: int
    governance_audit_events_total: int


class AdminUnsuspendResponse(BaseModel):
    status: Literal["unsuspended"]
    agent_id: str
    updated_at_utc: str


class AuditRotateResponse(BaseModel):
    status: Literal["rotated", "no_file"]
    previous_path: str
    rotated_path: str | None
    rotated_at_utc: str


def _admin_keys() -> dict[str, str]:
    # Legacy plain keys (optional fallback).
    return {
        "ops_audit_admin": os.getenv("PIXEL_UNIVERSE_ADMIN_KEY_OPS_AUDIT", "dev-admin-key-ops").strip(),
        "risk_admin": os.getenv("PIXEL_UNIVERSE_ADMIN_KEY_RISK", "dev-admin-key-risk").strip(),
        # Backward-compatible super admin key (optional)
        "super_admin": os.getenv("PIXEL_UNIVERSE_ADMIN_KEY", "").strip(),
    }


def _admin_hmac_keyring() -> dict[str, dict[str, str]]:
    # role -> {kid: secret}
    return {
        "ops_audit_admin": {
            os.getenv("PIXEL_UNIVERSE_ADMIN_KID_OPS_AUDIT", "ops-v1").strip(): os.getenv(
                "PIXEL_UNIVERSE_ADMIN_SECRET_OPS_AUDIT", "dev-ops-secret-v1"
            ).strip()
        },
        "risk_admin": {
            os.getenv("PIXEL_UNIVERSE_ADMIN_KID_RISK", "risk-v1").strip(): os.getenv(
                "PIXEL_UNIVERSE_ADMIN_SECRET_RISK", "dev-risk-secret-v1"
            ).strip()
        },
    }


def _verify_admin_hmac(x_admin_auth: str | None, role: str) -> bool:
    if not x_admin_auth:
        return False
    parts = x_admin_auth.strip().split(":")
    if len(parts) != 3:
        return False
    kid, ts_raw, sig = parts
    try:
        ts = int(ts_raw)
    except Exception:
        return False
    now_ts = int(datetime.now(timezone.utc).timestamp())
    # 5-minute replay window
    if abs(now_ts - ts) > 300:
        return False
    keyring = _admin_hmac_keyring().get(role, {})
    secret = keyring.get(kid, "")
    if not secret:
        return False
    message = f"{role}:{ts}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def _require_admin_role(x_admin_auth: str | None, x_admin_key: str | None, allowed_roles: set[str]) -> None:
    # Preferred: signed admin auth header (kid:ts:hmac)
    for role in allowed_roles:
        if _verify_admin_hmac(x_admin_auth, role):
            return

    # Legacy plain key fallback.
    if x_admin_key:
        keys = _admin_keys()
        if keys.get("super_admin") and x_admin_key == keys["super_admin"]:
            return
        for role in allowed_roles:
            if x_admin_key == keys.get(role):
                return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "admin_auth_invalid"})


@router.post("/agents/register", response_model=RegisterResponse)
async def agent_register(payload: RegisterRequest) -> RegisterResponse:
    profile = payload.profile
    seed = _compose_seed(
        profile.four_d_seed_mapping.primary_trait,
        profile.four_d_seed_mapping.secondary_trait,
    )
    cluster = _cluster_from_seed(seed)
    position = _pixel_position(seed)

    token = f"pxu_{secrets.token_urlsafe(24)}"
    with _REGISTRY_LOCK:
        existed = profile.identity.agent_id in _AGENT_REGISTRY
        prev_credits = 0
        if existed:
            prev_credits = int(_AGENT_REGISTRY[profile.identity.agent_id].get("credits_krw", 0))
        default_credit = max(profile.economy.api_call_fee_krw * 10, 100)
        _AGENT_REGISTRY[profile.identity.agent_id] = {
            "profile": profile.model_dump(),
            "seed": seed,
            "cluster": cluster,
            "pixel_position": position,
            "token": token,
            "credits_krw": prev_credits if existed else default_credit,
            "suspended": False,
            "updated_at_utc": _utc_now(),
        }
        _TOKEN_INDEX[token] = profile.identity.agent_id
        if not existed:
            _METRICS["registered_agents_total"] += 1

    return RegisterResponse(
        status="updated" if existed else "registered",
        agent_id=profile.identity.agent_id,
        bearer_token=token,
        cluster=cluster,
        pixel_position=position,
        registered_at_utc=_utc_now(),
        trace_ref=f"pxu-reg-{profile.identity.agent_id}",
    )


@router.post("/agents/message", response_model=MessageResponse)
async def agent_message(
    payload: MessageRequest,
    response: Response,
    authorization: str | None = Header(default=None),
) -> MessageResponse:
    token = _verify_agent_token(payload.agent_id, authorization)
    with _REGISTRY_LOCK:
        record = _AGENT_REGISTRY.get(payload.agent_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "agent_not_registered"})
    if record.get("suspended", False):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail={"error": "agent_suspended"})
    now_ts = datetime.now(timezone.utc).timestamp()
    _enforce_rate_limit(token, now_ts, _get_rate_limit_for_record(record))

    profile = record["profile"]
    gov = profile["governance_clearance"]
    lang = _detect_language(payload.message)
    semantic_vector = _normalize_text_to_semantic_vector(payload.message)
    actions = set(gov.get("allowed_actions", []))
    prohibited_intents = set(gov.get("prohibited_intents", []))
    risk = _message_risk(payload.message)
    intents = _infer_intents(payload.message, payload.requested_action)
    reason_codes: list[str] = []

    blocked = False
    if payload.requested_action not in actions:
        blocked = True
        reason_codes.append("ACTION_NOT_ALLOWED")
    if risk >= 0.9:
        blocked = True
        reason_codes.append("HIGH_RISK_MESSAGE")
    violated = sorted(intents.intersection(prohibited_intents))
    if violated:
        penalty = gov.get("violation_penalty", "block")
        reason_codes.append(f"POLICY_PROHIBITED_INTENT:{','.join(violated)}")
        if penalty in {"block", "suspend"}:
            blocked = True
        if penalty == "suspend":
            with _REGISTRY_LOCK:
                current_s = _AGENT_REGISTRY.get(payload.agent_id)
                if current_s is not None:
                    current_s["suspended"] = True
                    _AGENT_REGISTRY[payload.agent_id] = current_s
            reason_codes.append("ACCOUNT_SUSPENDED")
    if gov.get("human_override_required", False) and payload.requested_action == "financial_execute":
        blocked = True
        reason_codes.append("HUMAN_OVERRIDE_REQUIRED")

    decision: Literal["allow", "block"] = "block" if blocked else "allow"
    if not reason_codes:
        reason_codes.append("PASS")

    if gov.get("audit_consent", False):
        entry = {
            "ts_utc": _utc_now(),
            "agent_id": payload.agent_id,
            "decision": decision,
            "requested_action": payload.requested_action,
            "reason_codes": reason_codes,
            "policy_version": gov.get("policy_version", "unknown"),
        }
        _GOVERNANCE_AUDIT_EVENTS.append(entry)
        _append_governance_audit(entry)

    fee = int(profile["economy"].get("api_call_fee_krw", 0))
    charged = 0
    with _REGISTRY_LOCK:
        current = _AGENT_REGISTRY.get(payload.agent_id, {})
        credits = int(current.get("credits_krw", 0))
        if decision == "allow":
            if credits < fee:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={"error": "insufficient_credits", "required_krw": fee, "balance_krw": credits},
                )
            credits -= fee
            charged = fee
            current["credits_krw"] = credits
            _AGENT_REGISTRY[payload.agent_id] = current
            _METRICS["billing_charged_krw_total"] += fee
        remaining = credits

    _METRICS["messages_total"] += 1
    if decision == "allow":
        _METRICS["messages_allowed_total"] += 1
    else:
        _METRICS["messages_blocked_total"] += 1

    response.headers["X-Language-Detected"] = lang
    return MessageResponse(
        decision=decision,
        reason_codes=reason_codes,
        risk_score=risk,
        normalized_language=lang,
        semantic_vector_4d=semantic_vector,
        charged_krw=charged,
        remaining_credits_krw=remaining,
        governance_policy_version=str(gov.get("policy_version", "unknown")),
        cluster=record["cluster"],
        trace_ref=f"pxu-msg-{payload.agent_id}",
        processed_at_utc=_utc_now(),
    )


@router.post("/agents/message-async", response_model=AsyncAcceptedResponse)
async def agent_message_async(
    payload: MessageRequest,
    authorization: str | None = Header(default=None),
) -> AsyncAcceptedResponse:
    token = _verify_agent_token(payload.agent_id, authorization)
    with _REGISTRY_LOCK:
        record = _AGENT_REGISTRY.get(payload.agent_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "agent_not_registered"})
    if record.get("suspended", False):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail={"error": "agent_suspended"})
    now_ts = datetime.now(timezone.utc).timestamp()
    _enforce_rate_limit(token, now_ts, _get_rate_limit_for_record(record))

    job_id = f"pxu-job-{secrets.token_hex(8)}"
    _ASYNC_QUEUE.append(
        {
            "job_id": job_id,
            "payload": payload.model_dump(),
            "queued_at_utc": _utc_now(),
            "status": "queued",
        }
    )
    _METRICS["queued_jobs_total"] += 1
    return AsyncAcceptedResponse(
        status="accepted",
        job_id=job_id,
        queue_depth=len(_ASYNC_QUEUE),
        accepted_at_utc=_utc_now(),
        trace_ref=f"pxu-async-{payload.agent_id}",
    )


@router.get("/metrics", response_model=MetricsResponse)
async def pixel_universe_metrics() -> MetricsResponse:
    total = _METRICS["messages_total"]
    blocked = _METRICS["messages_blocked_total"]
    block_rate = (blocked / total) if total > 0 else 0.0
    return MetricsResponse(
        registered_agents_total=_METRICS["registered_agents_total"],
        active_tokens=len(_TOKEN_INDEX),
        messages_total=total,
        block_rate=round(block_rate, 6),
        auth_fail_total=_METRICS["auth_fail_total"],
        rate_limit_exceeded_total=_METRICS["rate_limit_exceeded_total"],
        billing_charged_krw_total=_METRICS["billing_charged_krw_total"],
        queued_jobs_total=_METRICS["queued_jobs_total"],
        governance_audit_events_total=len(_GOVERNANCE_AUDIT_EVENTS),
    )


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def pixel_universe_metrics_prometheus() -> str:
    total = _METRICS["messages_total"]
    blocked = _METRICS["messages_blocked_total"]
    block_rate = (blocked / total) if total > 0 else 0.0
    lines = [
        "# HELP pixel_universe_registered_agents_total Total registered agents",
        "# TYPE pixel_universe_registered_agents_total gauge",
        f"pixel_universe_registered_agents_total {_METRICS['registered_agents_total']}",
        "# HELP pixel_universe_messages_total Total message requests",
        "# TYPE pixel_universe_messages_total counter",
        f"pixel_universe_messages_total {_METRICS['messages_total']}",
        "# HELP pixel_universe_messages_blocked_total Total blocked message requests",
        "# TYPE pixel_universe_messages_blocked_total counter",
        f"pixel_universe_messages_blocked_total {_METRICS['messages_blocked_total']}",
        "# HELP pixel_universe_block_rate Current block rate",
        "# TYPE pixel_universe_block_rate gauge",
        f"pixel_universe_block_rate {round(block_rate, 6)}",
        "# HELP pixel_universe_billing_charged_krw_total Total charged KRW",
        "# TYPE pixel_universe_billing_charged_krw_total counter",
        f"pixel_universe_billing_charged_krw_total {_METRICS['billing_charged_krw_total']}",
        "# HELP pixel_universe_governance_audit_events_total Total governance audit events",
        "# TYPE pixel_universe_governance_audit_events_total counter",
        f"pixel_universe_governance_audit_events_total {len(_GOVERNANCE_AUDIT_EVENTS)}",
    ]
    return "\n".join(lines) + "\n"


@router.post("/admin/agents/{agent_id}/unsuspend", response_model=AdminUnsuspendResponse)
async def admin_unsuspend_agent(
    agent_id: str,
    x_admin_auth: str | None = Header(default=None),
    x_admin_key: str | None = Header(default=None),
) -> AdminUnsuspendResponse:
    _require_admin_role(x_admin_auth, x_admin_key, {"risk_admin"})
    with _REGISTRY_LOCK:
        record = _AGENT_REGISTRY.get(agent_id)
        if record is None:
            raise HTTPException(status_code=404, detail={"error": "agent_not_registered"})
        record["suspended"] = False
        record["updated_at_utc"] = _utc_now()
        _AGENT_REGISTRY[agent_id] = record
    return AdminUnsuspendResponse(status="unsuspended", agent_id=agent_id, updated_at_utc=_utc_now())


@router.post("/admin/audit/rotate", response_model=AuditRotateResponse)
async def admin_rotate_audit_log(
    x_admin_auth: str | None = Header(default=None),
    x_admin_key: str | None = Header(default=None),
) -> AuditRotateResponse:
    _require_admin_role(x_admin_auth, x_admin_key, {"ops_audit_admin"})
    path = _governance_audit_log_path()
    rotated_path: str | None = None
    if os.path.isfile(path):
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rotated_path = path.replace(".jsonl", f"_{ts}.jsonl")
        os.replace(path, rotated_path)
        status_value: Literal["rotated", "no_file"] = "rotated"
    else:
        status_value = "no_file"
    _GOVERNANCE_AUDIT_EVENTS.clear()
    return AuditRotateResponse(
        status=status_value,
        previous_path=path,
        rotated_path=rotated_path,
        rotated_at_utc=_utc_now(),
    )
