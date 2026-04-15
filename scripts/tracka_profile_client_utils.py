# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 92
# Purpose: Resolve TrackA profile metadata with legacy fallback for clients.
# Keywords: tracka, profile, client, compatibility, fallback
#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def extract_tracka_profile_meta(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return normalized TrackA profile metadata.

    Resolution order:
    1) `tracka_profile_meta` (new contract)
    2) `trackaProfileMeta` (camelCase compatibility)
    3) legacy flat keys (`tracka_profile`, `tracka_profile_source`, `tracka_profile_override_env`)

    Supports direct payload or wrapper payloads that contain `integrity_flags`.
    """
    root = _as_dict(payload)
    if not root:
        return {"profile": "", "source": "", "override_env": {}}

    # Allow callers to pass a full API body or just integrity_flags.
    flags = _as_dict(root.get("integrity_flags"))
    node = flags if flags else root

    meta = _as_dict(node.get("tracka_profile_meta"))
    if not meta:
        meta = _as_dict(node.get("trackaProfileMeta"))
    if meta:
        return {
            "profile": str(meta.get("profile", "")),
            "source": str(meta.get("source", "")),
            "override_env": _as_dict(meta.get("override_env")),
        }

    return {
        "profile": str(node.get("tracka_profile", "")),
        "source": str(node.get("tracka_profile_source", "")),
        "override_env": _as_dict(node.get("tracka_profile_override_env")),
    }
