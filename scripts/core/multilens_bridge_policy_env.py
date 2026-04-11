"""Read optional dev flag for 4D bridge policy (apply_gematria_4d_bridge_policy) from the environment."""

from __future__ import annotations

import os


def env_apply_gematria_4d_bridge_policy() -> bool:
    """True when MKM_APPLY_GEMATRIA_4D_BRIDGE_POLICY is 1/true/yes/on (case-insensitive)."""
    v = (os.environ.get("MKM_APPLY_GEMATRIA_4D_BRIDGE_POLICY") or "").strip().lower()
    return v in ("1", "true", "yes", "on")
