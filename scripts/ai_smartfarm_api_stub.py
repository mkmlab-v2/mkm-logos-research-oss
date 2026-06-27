#!/usr/bin/env python3
"""FastAPI stub for AI Smartfarm contract v1.

Run:
  uvicorn scripts.ai_smartfarm_api_stub:app --host 127.0.0.1 --port 8020
"""

from __future__ import annotations

import os
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from scripts.normalize_qubics_coconet_v1 import normalize_qubics_coconet, qubics_ack_body
from scripts.smartfarm_persist_jsonl_v1 import append_jsonl

API_CONTRACT_VERSION = "1.0.0"
SCHEMA_VERSION = "v1"

app = FastAPI(title="AI Smartfarm API Stub", version=API_CONTRACT_VERSION)
_cors_raw = os.environ.get("SMARTFARM_API_CORS_ALLOW_ORIGINS", "https://farm.mkmlife.com").strip()
_cors_origins = ["*"] if _cors_raw == "*" else [x.strip() for x in _cors_raw.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_DATA_GAP_SEC = 900
RAIN_MM_THRESHOLD = 3.0
DAILY_MAX_RUNTIME_MIN = 120
DAILY_MAX_VOLUME_LITER = 12000
DEFAULT_SOIL_DRY_THRESHOLD_PCT = 23.0

# In-memory state for quick pilot validation. Replace with persistent storage in production.
LATEST_TELEMETRY_BY_ZONE: dict[str, Any] = {}
LATEST_BATCH_BY_ZONE: dict[str, Any] = {}
DAILY_RUNTIME_MIN_BY_ZONE: dict[str, int] = {}
DAILY_VOLUME_LITER_BY_ZONE: dict[str, int] = {}
LAST_CONTROL_BY_ZONE: dict[str, Any] = {}
EVENT_LOG: deque[dict[str, Any]] = deque(maxlen=500)
COMMAND_QUEUE_BY_ZONE: dict[str, deque[dict[str, Any]]] = {}


class CommonContext(BaseModel):
    farm_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    ts_utc: datetime
    timezone: str = "Asia/Seoul"


class TelemetryIngestPayload(CommonContext):
    soil_moisture_pct: float = Field(ge=0, le=100)
    soil_temp_c: float = Field(ge=-30, le=80)
    soil_ec_us_cm: float = Field(ge=0)
    line_pressure_kpa: float | None = Field(default=None, ge=0)
    flow_lpm: float | None = Field(default=None, ge=0)
    device_battery_pct: float | None = Field(default=None, ge=0, le=100)
    comm_ok: bool


class ControlCommandPayload(CommonContext):
    command_id: str = Field(min_length=1)
    mode: Literal["onsite_manual", "remote_manual", "auto"]
    target: Literal["pump", "valve"]
    action: Literal["on", "off", "open", "close"]
    reason_code: Literal[
        "soil_dryness_trigger",
        "scheduled_irrigation",
        "rain_gate_skip",
        "manual_override",
        "emergency_stop",
        "safety_limit_reached",
        "communication_loss",
        "pressure_anomaly",
    ]
    max_runtime_sec: int = Field(ge=1, le=3600)
    estimated_volume_liter: int = Field(default=0, ge=0)
    requested_by: str | None = None


class FermentationBatchRegisterPayload(CommonContext):
    batch_id: str = Field(min_length=1)
    brew_start_ts_utc: datetime
    brew_end_ts_utc: datetime
    batch_ph: float = Field(ge=0, le=14)
    batch_ec_us_cm: float = Field(ge=0)
    operator_confirmed: bool
    anomaly_flag: bool
    notes: str | None = None


class AlarmEventPayload(CommonContext):
    alarm_id: str = Field(min_length=1)
    severity: Literal["info", "warning", "critical"]
    alarm_code: Literal[
        "communication_loss",
        "pressure_anomaly",
        "flow_anomaly",
        "actuator_no_ack",
        "safety_limit_reached",
        "batch_gate_blocked",
        "manual_override_active",
    ]
    message: str = Field(min_length=1)
    requires_ack: bool
    acked_by: str | None = None
    acked_ts_utc: datetime | None = None


class DecisionInputSnapshot(BaseModel):
    soil_moisture_pct: float
    soil_temp_c: float
    soil_ec_us_cm: float
    forecast_rain_mm_12h: float
    comm_ok: bool


class DecisionLogEventPayload(CommonContext):
    decision_id: str = Field(min_length=1)
    decision: Literal["execute", "skip", "delay", "stop"]
    reason_code: str = Field(min_length=1)
    input_snapshot: DecisionInputSnapshot
    mode: Literal["onsite_manual", "remote_manual", "auto"]
    command_id: str
    command_ack_status: Literal["accepted", "executed", "failed", "timeout", "not_applicable"]


class AcceptedResponse(BaseModel):
    accepted: bool = True
    api_contract_version: str = API_CONTRACT_VERSION
    schema_version: str = SCHEMA_VERSION
    message_type: str
    received_ts_utc: datetime
    id: str | None = None


class AutoEvaluateRequest(BaseModel):
    farm_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    ts_utc: datetime
    forecast_rain_mm_12h: float = Field(ge=0)
    mode: Literal["auto"] = "auto"
    desired_runtime_sec: int = Field(default=600, ge=1, le=3600)
    estimated_volume_liter: int = Field(default=0, ge=0)
    soil_dry_threshold_pct: float = Field(default=DEFAULT_SOIL_DRY_THRESHOLD_PCT, ge=0, le=100)


class AutoEvaluateResponse(BaseModel):
    accepted: bool = True
    api_contract_version: str = API_CONTRACT_VERSION
    schema_version: str = SCHEMA_VERSION
    decision: Literal["execute", "skip", "delay", "stop"]
    reason_code: str
    suggested_command: dict[str, Any] | None = None
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    received_ts_utc: datetime


class ControlAckRequest(BaseModel):
    farm_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1)
    ack_status: Literal["accepted", "executed", "failed", "timeout"]
    ack_message: str | None = None
    ts_utc: datetime


def _accepted(message_type: str, item_id: str | None = None) -> AcceptedResponse:
    return AcceptedResponse(
        message_type=message_type,
        received_ts_utc=datetime.now(UTC),
        id=item_id,
    )


def _zone_key(farm_id: str, zone_id: str) -> str:
    return f"{farm_id}:{zone_id}"


def _qubics_pilot_farm_id() -> str:
    return os.environ.get("SMARTFARM_PILOT_FARM_ID", "geumsan_farm_01")


def _qubics_pilot_zone_id() -> str:
    return os.environ.get("SMARTFARM_PILOT_ZONE_ID", "zone_01")


def _qubics_pilot_timezone() -> str:
    return os.environ.get("SMARTFARM_PILOT_TIMEZONE", "Asia/Seoul")


def _qubics_comm_ok_max_age_sec() -> int:
    raw = os.environ.get("SMARTFARM_QUBICS_COMM_OK_MAX_AGE_SEC", "900").strip()
    try:
        return max(60, int(raw))
    except ValueError:
        return 900


def _qubics_raw_jsonl_path() -> Path | None:
    raw = os.environ.get("SMARTFARM_QUBICS_RAW_JSONL", "").strip()
    if not raw:
        raw = os.environ.get("SMARTFARM_EVENT_JSONL_PATH", "").strip()
    return Path(raw) if raw else None


def _store_telemetry_envelope(envelope: dict[str, Any]) -> TelemetryIngestPayload:
    payload = envelope["payload"]
    body = TelemetryIngestPayload(**payload)
    zone_key = _zone_key(body.farm_id, body.zone_id)
    LATEST_TELEMETRY_BY_ZONE[zone_key] = body
    _append_event(
        zone_key,
        "telemetry_ingest",
        {
            "source": "qubics_coconet",
            "soil_moisture_pct": body.soil_moisture_pct,
            "soil_temp_c": body.soil_temp_c,
            "soil_ec_us_cm": body.soil_ec_us_cm,
            "comm_ok": body.comm_ok,
            "vendor_meta": envelope.get("vendor_meta"),
        },
    )
    return body


def _qubics_zone_id_for_payload(vendor_payload: dict[str, Any]) -> str:
    from scripts.smartfarm_qubics_device_resolver_v1 import manifest_path_from_env, resolve_zone_id, load_manifest

    path = manifest_path_from_env()
    if path is not None:
        zone = resolve_zone_id(load_manifest(path), vendor_payload)
        if zone:
            return zone
    return _qubics_pilot_zone_id()


def _process_qubics_ingest(vendor_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        ack = qubics_ack_body(vendor_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    zone_id = _qubics_zone_id_for_payload(vendor_payload)
    farm_id = _qubics_pilot_farm_id()
    try:
        normalized = normalize_qubics_coconet(
            vendor_payload,
            farm_id=farm_id,
            zone_id=zone_id,
            timezone=_qubics_pilot_timezone(),
            comm_ok_max_age_sec=_qubics_comm_ok_max_age_sec(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _store_telemetry_envelope(normalized)
    append_jsonl(
        _qubics_raw_jsonl_path(),
        {
            "event_type": "qubics_vendor_ingest",
            "zone_key": _zone_key(farm_id, zone_id),
            "vendor_payload": vendor_payload,
            "normalized": normalized,
            "ack": ack,
        },
    )
    return ack, normalized


def _append_event(zone_key: str, event_type: str, payload: dict[str, Any]) -> None:
    EVENT_LOG.append(
        {
            "event_id": f"evt_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            "zone_key": zone_key,
            "event_type": event_type,
            "ts_utc": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
    )


def _next_command_id(zone_key: str) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    safe_zone = zone_key.replace(":", "_")
    return f"cmd_{safe_zone}_{ts}"


def _build_auto_response(
    *,
    decision: Literal["execute", "skip", "delay", "stop"],
    reason_code: str,
    suggested_command: dict[str, Any] | None,
    state_snapshot: dict[str, Any],
) -> AutoEvaluateResponse:
    return AutoEvaluateResponse(
        decision=decision,
        reason_code=reason_code,
        suggested_command=suggested_command,
        state_snapshot=state_snapshot,
        received_ts_utc=datetime.now(UTC),
    )


def _evaluate_auto_decision(body: AutoEvaluateRequest) -> AutoEvaluateResponse:
    zone_key = _zone_key(body.farm_id, body.zone_id)
    telemetry = LATEST_TELEMETRY_BY_ZONE.get(zone_key)
    batch = LATEST_BATCH_BY_ZONE.get(zone_key)
    runtime_min = DAILY_RUNTIME_MIN_BY_ZONE.get(zone_key, 0)
    volume_liter = DAILY_VOLUME_LITER_BY_ZONE.get(zone_key, 0)
    last_control = LAST_CONTROL_BY_ZONE.get(zone_key)

    snapshot: dict[str, Any] = {
        "zone_key": zone_key,
        "has_telemetry": telemetry is not None,
        "has_batch": batch is not None,
        "daily_runtime_min": runtime_min,
        "daily_volume_liter": volume_liter,
        "forecast_rain_mm_12h": body.forecast_rain_mm_12h,
    }
    if telemetry is not None:
        age_sec = int((body.ts_utc - telemetry.ts_utc).total_seconds())
        snapshot["telemetry_age_sec"] = age_sec
        snapshot["soil_moisture_pct"] = telemetry.soil_moisture_pct
        snapshot["comm_ok"] = telemetry.comm_ok
    else:
        snapshot["telemetry_age_sec"] = None

    if telemetry is None:
        return _build_auto_response(
            decision="delay",
            reason_code="telemetry_missing",
            suggested_command=None,
            state_snapshot=snapshot,
        )
    if not telemetry.comm_ok:
        return _build_auto_response(
            decision="stop",
            reason_code="communication_loss",
            suggested_command=None,
            state_snapshot=snapshot,
        )
    if snapshot["telemetry_age_sec"] is not None and snapshot["telemetry_age_sec"] < 0:
        return _build_auto_response(
            decision="delay",
            reason_code="telemetry_timestamp_future",
            suggested_command=None,
            state_snapshot=snapshot,
        )
    if snapshot["telemetry_age_sec"] is None or snapshot["telemetry_age_sec"] > MAX_DATA_GAP_SEC:
        return _build_auto_response(
            decision="delay",
            reason_code="telemetry_stale",
            suggested_command=None,
            state_snapshot=snapshot,
        )
    if batch is None:
        return _build_auto_response(
            decision="stop",
            reason_code="batch_gate_blocked_missing_batch",
            suggested_command=None,
            state_snapshot=snapshot,
        )
    if not batch.operator_confirmed or batch.anomaly_flag:
        return _build_auto_response(
            decision="stop",
            reason_code="batch_gate_blocked_invalid_batch",
            suggested_command=None,
            state_snapshot=snapshot,
        )
    if body.forecast_rain_mm_12h >= RAIN_MM_THRESHOLD:
        return _build_auto_response(
            decision="skip",
            reason_code="rain_gate_skip",
            suggested_command=None,
            state_snapshot=snapshot,
        )
    next_runtime_min = runtime_min + int(round(body.desired_runtime_sec / 60.0))
    if next_runtime_min > DAILY_MAX_RUNTIME_MIN:
        return _build_auto_response(
            decision="stop",
            reason_code="safety_limit_runtime_reached",
            suggested_command=None,
            state_snapshot=snapshot,
        )
    next_volume = volume_liter + int(body.estimated_volume_liter)
    if next_volume > DAILY_MAX_VOLUME_LITER:
        return _build_auto_response(
            decision="stop",
            reason_code="safety_limit_volume_reached",
            suggested_command=None,
            state_snapshot=snapshot,
        )
    if telemetry.soil_moisture_pct > body.soil_dry_threshold_pct:
        return _build_auto_response(
            decision="skip",
            reason_code="soil_not_dry_enough",
            suggested_command=None,
            state_snapshot=snapshot,
        )

    command_id = _next_command_id(zone_key)
    suggested_command = {
        "command_id": command_id,
        "farm_id": body.farm_id,
        "zone_id": body.zone_id,
        "ts_utc": body.ts_utc.isoformat(),
        "timezone": "Asia/Seoul",
        "mode": "auto",
        "target": "pump",
        "action": "on",
        "reason_code": "soil_dryness_trigger",
        "max_runtime_sec": body.desired_runtime_sec,
        "requested_by": "auto_evaluator",
        "batch_id": batch.batch_id,
        "previous_command_id": last_control.command_id if last_control else None,
    }
    COMMAND_QUEUE_BY_ZONE.setdefault(zone_key, deque()).append(suggested_command)
    _append_event(zone_key, "auto_command_suggested", suggested_command)
    return _build_auto_response(
        decision="execute",
        reason_code="soil_dryness_trigger",
        suggested_command=suggested_command,
        state_snapshot=snapshot,
    )


@app.post("/")
def qubics_root_post(body: dict[str, Any]) -> dict[str, Any]:
    """QuBICS gateway default POST target — ACK only per sensor manual."""
    ack, _ = _process_qubics_ingest(body)
    return ack


@app.post("/v1/vendor/qubics/ingest")
def qubics_named_ingest(body: dict[str, Any]) -> dict[str, Any]:
    """MKM named ingest — returns vendor ACK plus normalized telemetry envelope."""
    ack, normalized = _process_qubics_ingest(body)
    return {"ack": ack, "normalized": normalized}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "ai_smartfarm_api_stub",
        "api_contract_version": API_CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "in_memory_state": {
            "telemetry_zones": len(LATEST_TELEMETRY_BY_ZONE),
            "batch_zones": len(LATEST_BATCH_BY_ZONE),
            "control_zones": len(LAST_CONTROL_BY_ZONE),
        },
        "ts_utc": datetime.now(UTC).isoformat(),
    }


@app.post("/v1/telemetry", response_model=AcceptedResponse)
def telemetry_ingest(body: TelemetryIngestPayload) -> AcceptedResponse:
    zone_key = _zone_key(body.farm_id, body.zone_id)
    LATEST_TELEMETRY_BY_ZONE[zone_key] = body
    _append_event(
        zone_key,
        "telemetry_ingest",
        {
            "soil_moisture_pct": body.soil_moisture_pct,
            "soil_temp_c": body.soil_temp_c,
            "soil_ec_us_cm": body.soil_ec_us_cm,
            "comm_ok": body.comm_ok,
        },
    )
    return _accepted("telemetry_ingest", item_id=f"{body.farm_id}:{body.zone_id}")


@app.post("/v1/control", response_model=AcceptedResponse)
def control_command(body: ControlCommandPayload) -> AcceptedResponse:
    zone_key = _zone_key(body.farm_id, body.zone_id)
    LAST_CONTROL_BY_ZONE[zone_key] = body
    if body.action in {"on", "open"}:
        runtime_min_add = int(round(body.max_runtime_sec / 60.0))
        DAILY_RUNTIME_MIN_BY_ZONE[zone_key] = DAILY_RUNTIME_MIN_BY_ZONE.get(zone_key, 0) + runtime_min_add
        DAILY_VOLUME_LITER_BY_ZONE[zone_key] = (
            DAILY_VOLUME_LITER_BY_ZONE.get(zone_key, 0) + int(body.estimated_volume_liter)
        )
    _append_event(
        zone_key,
        "control_command",
        {
            "command_id": body.command_id,
            "target": body.target,
            "action": body.action,
            "reason_code": body.reason_code,
            "mode": body.mode,
        },
    )
    return _accepted("control_command", item_id=body.command_id)


@app.post("/v1/batch", response_model=AcceptedResponse)
def fermentation_batch_register(body: FermentationBatchRegisterPayload) -> AcceptedResponse:
    zone_key = _zone_key(body.farm_id, body.zone_id)
    LATEST_BATCH_BY_ZONE[zone_key] = body
    _append_event(
        zone_key,
        "batch_register",
        {
            "batch_id": body.batch_id,
            "operator_confirmed": body.operator_confirmed,
            "anomaly_flag": body.anomaly_flag,
        },
    )
    return _accepted("fermentation_batch_register", item_id=body.batch_id)


@app.post("/v1/alarm", response_model=AcceptedResponse)
def alarm_event(body: AlarmEventPayload) -> AcceptedResponse:
    zone_key = _zone_key(body.farm_id, body.zone_id)
    _append_event(
        zone_key,
        "alarm_event",
        {
            "alarm_id": body.alarm_id,
            "severity": body.severity,
            "alarm_code": body.alarm_code,
            "requires_ack": body.requires_ack,
        },
    )
    return _accepted("alarm_event", item_id=body.alarm_id)


@app.post("/v1/decision", response_model=AcceptedResponse)
def decision_log_event(body: DecisionLogEventPayload) -> AcceptedResponse:
    zone_key = _zone_key(body.farm_id, body.zone_id)
    _append_event(
        zone_key,
        "decision_log_event",
        {
            "decision_id": body.decision_id,
            "decision": body.decision,
            "reason_code": body.reason_code,
            "mode": body.mode,
            "command_id": body.command_id,
            "command_ack_status": body.command_ack_status,
        },
    )
    return _accepted("decision_log_event", item_id=body.decision_id)


@app.post("/v1/auto/evaluate", response_model=AutoEvaluateResponse)
def auto_evaluate(body: AutoEvaluateRequest) -> AutoEvaluateResponse:
    return _evaluate_auto_decision(body)


@app.get("/v1/state/{farm_id}/{zone_id}")
def get_zone_state(farm_id: str, zone_id: str) -> dict[str, Any]:
    zone_key = _zone_key(farm_id, zone_id)
    telemetry = LATEST_TELEMETRY_BY_ZONE.get(zone_key)
    batch = LATEST_BATCH_BY_ZONE.get(zone_key)
    last_control = LAST_CONTROL_BY_ZONE.get(zone_key)
    return {
        "farm_id": farm_id,
        "zone_id": zone_id,
        "zone_key": zone_key,
        "telemetry": telemetry.model_dump(mode="json") if telemetry else None,
        "batch": batch.model_dump(mode="json") if batch else None,
        "last_control": last_control.model_dump(mode="json") if last_control else None,
        "daily_runtime_min": DAILY_RUNTIME_MIN_BY_ZONE.get(zone_key, 0),
        "daily_volume_liter": DAILY_VOLUME_LITER_BY_ZONE.get(zone_key, 0),
        "pending_command_count": len(COMMAND_QUEUE_BY_ZONE.get(zone_key, deque())),
        "updated_ts_utc": datetime.now(UTC).isoformat(),
    }


@app.get("/v1/events")
def get_events(farm_id: str | None = None, zone_id: str | None = None, limit: int = 50) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 200))
    events = list(EVENT_LOG)
    if farm_id and zone_id:
        zk = _zone_key(farm_id, zone_id)
        events = [e for e in events if e.get("zone_key") == zk]
    elif farm_id:
        prefix = f"{farm_id}:"
        events = [e for e in events if str(e.get("zone_key", "")).startswith(prefix)]
    sliced = events[-safe_limit:]
    return {"count": len(sliced), "limit": safe_limit, "events": sliced}


@app.get("/v1/control/next/{farm_id}/{zone_id}")
def poll_next_control_command(farm_id: str, zone_id: str) -> dict[str, Any]:
    zone_key = _zone_key(farm_id, zone_id)
    queue = COMMAND_QUEUE_BY_ZONE.setdefault(zone_key, deque())
    if not queue:
        return {"available": False, "command": None, "zone_key": zone_key}
    command = queue[0]
    return {"available": True, "command": command, "zone_key": zone_key}


@app.post("/v1/control/ack", response_model=AcceptedResponse)
def ack_control_command(body: ControlAckRequest) -> AcceptedResponse:
    zone_key = _zone_key(body.farm_id, body.zone_id)
    queue = COMMAND_QUEUE_BY_ZONE.setdefault(zone_key, deque())
    if queue and queue[0].get("command_id") == body.command_id:
        queue.popleft()
    _append_event(
        zone_key,
        "control_ack",
        {
            "command_id": body.command_id,
            "ack_status": body.ack_status,
            "ack_message": body.ack_message,
            "ts_utc": body.ts_utc.isoformat(),
        },
    )
    return _accepted("control_ack", item_id=body.command_id)
