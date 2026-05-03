from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_sha256(obj: Any) -> str:
    """Deterministic JSON → sha256 hex (UTF-8, sorted keys, no whitespace)."""
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def digest_tag(hex_digest: str) -> str:
    return f"sha256:{hex_digest}"
