from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from .core_schema import DomainInsight, LogosCoreInsight


class DomainAdapter(Protocol):
    domain: str

    def transform(self, core: LogosCoreInsight) -> DomainInsight:
        ...


class FinanceAdapter:
    domain = "finance"

    def transform(self, core: LogosCoreInsight) -> DomainInsight:
        risk_band = core["risk_band"]
        if risk_band == "high":
            actions = ["reduce gross exposure", "tighten stop discipline", "avoid leverage expansion"]
            constraints = ["no aggressive position scaling", "approval gate required for execute"]
        elif risk_band == "medium":
            actions = ["maintain neutral position sizing", "prefer staged entries"]
            constraints = ["single-position risk cap must hold"]
        else:
            actions = ["allow selective risk-on", "keep trailing stop protection"]
            constraints = ["no override of hard risk guardrails"]
        return {
            "ts_utc": datetime.now(UTC).isoformat(),
            "domain": "finance",
            "summary": f"Logos core implies {risk_band} market caution.",
            "actions": actions,
            "constraints": constraints,
            "confidence": core["confidence"],
        }


class HealthAdapter:
    domain = "health"

    def transform(self, core: LogosCoreInsight) -> DomainInsight:
        return {
            "ts_utc": datetime.now(UTC).isoformat(),
            "domain": "health",
            "summary": "Use logos rhythm for recovery-first daily pacing.",
            "actions": ["reduce decision density", "prioritize sleep and hydration", "schedule deep work in fixed blocks"],
            "constraints": ["avoid high-stress multitasking windows"],
            "confidence": core["confidence"],
        }


class LifeAdapter:
    domain = "life"

    def transform(self, core: LogosCoreInsight) -> DomainInsight:
        return {
            "ts_utc": datetime.now(UTC).isoformat(),
            "domain": "life",
            "summary": "Apply logos constraints before major commitments.",
            "actions": ["delay irreversible decisions", "collect one extra objective signal", "prefer reversible experiments"],
            "constraints": ["keep downside bounded before expansion"],
            "confidence": core["confidence"],
        }


def default_adapters() -> list[DomainAdapter]:
    return [FinanceAdapter(), HealthAdapter(), LifeAdapter()]
