"""Logos inquiry S4 chunk streaming v1 — SSE event sequence (P0-1b)."""
from __future__ import annotations

import re
from typing import Any, Iterator

from core.logos_inquiry_report_v1 import (  # noqa: WPS433
    SCHEMA as REPORT_SCHEMA,
    build_inquiry_report,
)

STREAM_SCHEMA = "logos_inquiry_stream_v1"
DEFAULT_CHUNK_CHARS = 48


def chunk_s4_body(text: str, *, chunk_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    """Split S4 body into stream chunks (sentence-aware when possible)."""
    clean = (text or "").strip()
    if not clean:
        return []
    parts = re.split(r"(?<=[.!?…])\s+", clean)
    chunks: list[str] = []
    buf = ""
    for part in parts:
        candidate = f"{buf} {part}".strip() if buf else part
        if len(candidate) <= chunk_chars:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
        if len(part) <= chunk_chars:
            buf = part
        else:
            for i in range(0, len(part), chunk_chars):
                chunks.append(part[i : i + chunk_chars])
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def build_provisional_s5(*, chain_exit_code: int = 0, artifact_path: str) -> dict[str, Any]:
    return {
        "section_id": "S5_jema_integrity_signoff",
        "title_ko": "JEMA Integrity Signoff (무결성 서명)",
        "signoff_status": "provisional",
        "chain_exit_code": chain_exit_code,
        "artifact_path": artifact_path,
        "sections_payload_sha256": None,
        "freeze_verify_command": "py scripts/check_logos_corpus_knowledge_freeze_manifest_v1.py",
        "note_ko": "S4 스트림 완료 후 final seal — 중간 provisional.",
    }


def build_stream_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    sections = report.get("sections") or {}
    return {
        "S1": sections.get("S1"),
        "S2": sections.get("S2"),
        "S3": sections.get("S3"),
        "S4_placeholder": {
            "section_id": "S4_dynamic_synthesis",
            "title_ko": "Dynamic Synthesis (고차원 통찰)",
            "body_ko": "",
            "streaming": "active",
        },
        "S5": build_provisional_s5(
            chain_exit_code=(sections.get("S5") or {}).get("chain_exit_code", 0),
            artifact_path=(sections.get("S5") or {}).get("artifact_path", ""),
        ),
        "governance": report.get("governance"),
    }


def iter_stream_events(
    report: dict[str, Any],
    *,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
) -> Iterator[dict[str, Any]]:
    """Yield ordered SSE payload objects (event name in 'event' field)."""
    seq = 0
    yield {
        "schema": STREAM_SCHEMA,
        "event": "snapshot",
        "seq": seq,
        "snapshot": build_stream_snapshot(report),
    }
    s4 = (report.get("sections") or {}).get("S4") or {}
    body = str(s4.get("body_ko") or "")
    bullets = s4.get("bullets_ko") or []
    for index, text in enumerate(chunk_s4_body(body, chunk_chars=chunk_chars)):
        seq += 1
        yield {
            "schema": STREAM_SCHEMA,
            "event": "s4_delta",
            "seq": seq,
            "delta": {"index": index, "text": text},
        }
    seq += 1
    yield {
        "schema": STREAM_SCHEMA,
        "event": "s4_done",
        "seq": seq,
        "s4": {"body_ko": body, "bullets_ko": bullets},
    }
    final = dict(report)
    final_s5 = (final.get("sections") or {}).get("S5") or {}
    if isinstance(final_s5, dict):
        final_s5 = {**final_s5, "signoff_status": "final"}
    seq += 1
    yield {
        "schema": STREAM_SCHEMA,
        "event": "done",
        "seq": seq,
        "report": final,
    }


def build_stream_sequence_from_payload(
    payload: dict[str, Any],
    *,
    query: str,
    intake: dict[str, Any] | None = None,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
) -> list[dict[str, Any]]:
    report = build_inquiry_report(payload, query=query, intake=intake)
    return list(iter_stream_events(report, chunk_chars=chunk_chars))
