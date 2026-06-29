#!/usr/bin/env python3
"""Append-only JSONL persistence for smartfarm pilot logs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def append_jsonl(path: Path | str | None, row: dict[str, Any]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {"logged_at_utc": datetime.now(UTC).isoformat(), **row}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
