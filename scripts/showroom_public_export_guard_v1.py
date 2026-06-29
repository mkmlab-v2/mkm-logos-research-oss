"""Public showroom export allowlist guard — forbidden keys/paths in deploy JSON."""

from __future__ import annotations

import re
from typing import Any

FORBIDDEN_KEY_SUBSTRINGS = (
    "vector_4d",
    "unified_4d",
    "gematria",
    "hebrew_value",
    "greek_value",
    "physical_constants",
    "materialize_canon",
    "athena_run_v1",
    "ecc_execution",
)

FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"scripts/[a-z0-9_./\\-]+\.py", re.I),
    re.compile(r"docs/final/CONSTITUTION", re.I),
    re.compile(r"docs/research/", re.I),
    re.compile(r"docs/final/artifacts/", re.I),
    re.compile(r"\.env(?:\.|$)", re.I),
)

ALLOWED_ROOT_KEYS_WITH_REPRO = frozenset({"reproduce"})


def scan_forbidden(obj: Any, *, path: str = "$") -> list[str]:
    """Return list of violation messages. Empty = pass."""
    violations: list[str] = []

    if isinstance(obj, dict):
        for key, val in obj.items():
            key_lower = str(key).lower()
            for sub in FORBIDDEN_KEY_SUBSTRINGS:
                if sub in key_lower:
                    violations.append(f"{path}.{key}: forbidden key substring {sub!r}")
            child_path = f"{path}.{key}"
            if key not in ALLOWED_ROOT_KEYS_WITH_REPRO or path != "$":
                violations.extend(scan_forbidden(val, path=child_path))
            elif path == "$" and key == "reproduce":
                if isinstance(val, str):
                    for pat in FORBIDDEN_VALUE_PATTERNS:
                        if pat.search(val):
                            violations.append(f"{path}.reproduce: forbidden path in reproduce string")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            violations.extend(scan_forbidden(item, path=f"{path}[{i}]"))
    elif isinstance(obj, str):
        for pat in FORBIDDEN_VALUE_PATTERNS:
            if pat.search(obj):
                violations.append(f"{path}: forbidden value pattern {pat.pattern!r}")

    return violations
