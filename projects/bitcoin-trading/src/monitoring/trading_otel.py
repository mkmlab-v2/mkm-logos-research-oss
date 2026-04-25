# -*- coding: utf-8 -*-
"""
Optional OpenTelemetry tracing for the bitcoin trading daemon.

Enable: MKM_OTEL_ENABLED=1
Export: set OTEL_EXPORTER_OTLP_TRACES_ENDPOINT (HTTP) for OTLP, or leave unset to use
         console exporter when MKM_OTEL_CONSOLE=1 (default on if OTLP endpoint missing).

Install: pip install -r requirements-optional-otel.txt
"""
from __future__ import annotations

import logging
import os
from contextlib import AbstractContextManager, nullcontext
from typing import Any, Mapping, Optional, Union

logger = logging.getLogger(__name__)

_provider_initialized = False


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def init_otel_if_enabled(service_name: str = "mkm-bitcoin-trading-daemon") -> None:
    """Configure TracerProvider once when MKM_OTEL_ENABLED=1. Safe no-op if packages missing."""
    global _provider_initialized
    if _provider_initialized:
        return
    if not _env_truthy("MKM_OTEL_ENABLED"):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except ImportError:
        logger.info("OpenTelemetry SDK not installed; MKM_OTEL_ENABLED ignored.")
        _provider_initialized = True
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    endpoint = (
        os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip()
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    )
    otlp_ok = False
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            otlp_ok = True
            logger.info("OpenTelemetry: OTLP HTTP exporter -> %s", endpoint)
        except ImportError:
            logger.warning(
                "OTLP HTTP exporter unavailable; install opentelemetry-exporter-otlp-proto-http. "
                "Falling back to console unless MKM_OTEL_CONSOLE=0."
            )

    console_off = os.environ.get("MKM_OTEL_CONSOLE", "1").strip().lower() in ("0", "false", "no", "off")
    if not otlp_ok and not console_off:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("OpenTelemetry: console span exporter enabled (default when OTLP absent).")

    trace.set_tracer_provider(provider)
    _provider_initialized = True
    logger.info("OpenTelemetry: TracerProvider ready (service=%s).", service_name)


def span(
    name: str,
    attributes: Optional[Mapping[str, Any]] = None,
) -> Union[AbstractContextManager[Any], Any]:
    """Return a span context manager, or nullcontext when OTel off / not initialized."""
    if not _env_truthy("MKM_OTEL_ENABLED"):
        return nullcontext()
    try:
        from opentelemetry import trace
    except ImportError:
        return nullcontext()

    try:
        tracer = trace.get_tracer(__name__)
        attrs: Optional[dict[str, str]] = None
        if attributes:
            attrs = {str(k): str(v) for k, v in attributes.items() if v is not None}
        return tracer.start_as_current_span(name, attributes=attrs)
    except Exception as e:
        logger.debug("otel span skipped: %s", e)
        return nullcontext()
