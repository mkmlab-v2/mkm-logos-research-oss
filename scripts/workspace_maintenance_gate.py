# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.82, K:0.45, M:0.55}
# Balance: 82
# Purpose: Single env gate so scheduled chains skip artifact writes during focused work.
# Keywords: maintenance, ops, workspace, scheduled-tasks
"""When MKM_WORKSPACE_MAINTENANCE is truthy, scheduled writers should no-op (exit 0)."""

from __future__ import annotations

import os


def is_workspace_maintenance_active() -> bool:
    v = os.environ.get("MKM_WORKSPACE_MAINTENANCE", "").strip().lower()
    return v in ("1", "true", "yes", "on")
