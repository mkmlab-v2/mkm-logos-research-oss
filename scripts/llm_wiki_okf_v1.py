#!/usr/bin/env python3
"""Shared OKF v0.1 frontmatter helpers for MKM llm_wiki and export bundles."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "\n" + "\n".join(f"  - {item}" for item in items)


def render_frontmatter(fields: dict[str, Any]) -> str:
    """Render YAML frontmatter block (without outer ---)."""
    lines: list[str] = []
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:{_yaml_list([str(v) for v in value])}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            text = str(value)
            if any(c in text for c in ":{}[]#&*!|>'\"%@`"):
                text = json_quote(text)
            lines.append(f"{key}: {text}")
    return "\n".join(lines)


def json_quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def wrap_concept_document(body: str, fields: dict[str, Any]) -> str:
    fm = render_frontmatter(fields)
    body = body.strip()
    return f"---\n{fm}\n---\n\n{body}\n"
