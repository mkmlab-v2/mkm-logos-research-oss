"""Phase C AnimateDiff tier profiles (smoke | mq | hq) — B-track [HYPO] research only."""

from __future__ import annotations

from typing import Any

TIER_PROFILES: dict[str, dict[str, Any]] = {
    "smoke": {
        "num_frames": 8,
        "width": 256,
        "height": 144,
        "steps": 8,
        "fps": 8,
        "bitrate_k": 600,
        "guidance": 7.5,
        "note": "pipeline smoke; not showroom quality",
    },
    "mq": {
        "num_frames": 16,
        "width": 512,
        "height": 288,
        "steps": 20,
        "fps": 12,
        "bitrate_k": 1200,
        "guidance": 7.5,
        "note": "medium research bake; still shorter than prod 12s loop",
    },
    "hq": {
        "num_frames": 24,
        "width": 768,
        "height": 432,
        "steps": 25,
        "fps": 12,
        "bitrate_k": 1800,
        "guidance": 7.0,
        "note": "high research bake; GPU-heavy; not production LUT",
    },
}


def resolve_tier(name: str) -> dict[str, Any]:
    key = (name or "smoke").strip().lower()
    if key not in TIER_PROFILES:
        raise ValueError(f"unknown tier {name!r}; expected smoke|mq|hq")
    return dict(TIER_PROFILES[key], tier=key)
