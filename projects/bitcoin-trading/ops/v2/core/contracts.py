from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DecisionType = Literal["KEEP_RUNNING", "REQUEST_RESTART", "PAUSE_WITH_KILL_SWITCH"]


class WatchdogOutput(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    action_hint: Literal["KEEP", "RESTART", "PAUSE"]
    issues: list[str] = Field(default_factory=list)


class BrainSyncOutput(BaseModel):
    sync_fresh: bool
    note_path: str
    summary: str


class AthenaOutput(BaseModel):
    decision: DecisionType
    reason: str
    requires_human_approval: bool = False
