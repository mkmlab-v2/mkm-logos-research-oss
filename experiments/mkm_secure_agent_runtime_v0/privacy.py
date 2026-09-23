"""Deterministic local privacy scanner for MKM Secure Agent Runtime V0.2.

This is a fail-closed prefilter, not a complete DLP/PHI classifier.
It intentionally does not claim reliable person-name detection.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class Signal:
    kind: str
    start: int
    end: int
    severity: str


@dataclass(frozen=True)
class ScanResult:
    state: str
    release_decision: str
    signals: list[Signal]
    signal_counts: dict[str, int]
    medical_context: bool
    manual_review_required: bool
    limitations: list[str]

    def to_dict(self) -> dict:
        value = asdict(self)
        return value


_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "PRIVATE_KEY",
        "SECRET",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
    (
        "AWS_ACCESS_KEY",
        "SECRET",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "GITHUB_TOKEN",
        "SECRET",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,255}\b"),
    ),
    (
        "API_SECRET_ASSIGNMENT",
        "SECRET",
        re.compile(
            r"(?i)\b(?:api[_-]?key|password|passwd|secret|access[_-]?token|auth[_-]?token)\b"
            r"\s*[:=]\s*['\"]?[^\s'\"]{8,}"
        ),
    ),
    (
        "OPENAI_STYLE_TOKEN",
        "SECRET",
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "KOREAN_RRN_LIKE",
        "PERSONAL",
        re.compile(r"(?<!\d)\d{6}-?[1-8]\d{6}(?!\d)"),
    ),
    (
        "KOREAN_MOBILE_PHONE",
        "PERSONAL",
        re.compile(r"(?<!\d)01[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)"),
    ),
    (
        "EMAIL",
        "PERSONAL",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
]

_MEDICAL_CONTEXT = re.compile(
    r"(?i)(환자|진료|진단|처방|투약|복약|병력|증상|통증|검사|차트|의무기록|"
    r"병원|의원|한의원|의사|한의사|medical|patient|diagnos|prescri|medicat)"
)


def _signals(text: str) -> list[Signal]:
    rows: list[Signal] = []
    for kind, severity, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            rows.append(Signal(kind, match.start(), match.end(), severity))
    rows.sort(key=lambda x: (x.start, x.end, x.kind))
    return rows


def scan_text(text: str) -> ScanResult:
    signals = _signals(text)
    counts: dict[str, int] = {}
    for signal in signals:
        counts[signal.kind] = counts.get(signal.kind, 0) + 1

    has_secret = any(s.severity == "SECRET" for s in signals)
    has_personal = any(s.severity == "PERSONAL" for s in signals)
    medical = bool(_MEDICAL_CONTEXT.search(text))

    if has_secret:
        state = "SECRET"
        release = "DENY"
    elif has_personal and medical:
        state = "PHI"
        release = "HOLD"
    elif has_personal:
        state = "PERSONAL"
        release = "HOLD"
    else:
        state = "INTERNAL"
        release = "ALLOW"

    limitations = [
        "PERSON_NAME_DETECTION_NOT_ESTABLISHED",
        "DETERMINISTIC_PREFILTER_NOT_COMPLETE_DLP",
    ]
    return ScanResult(
        state=state,
        release_decision=release,
        signals=signals,
        signal_counts=counts,
        medical_context=medical,
        manual_review_required=state in {"PHI", "PERSONAL"},
        limitations=limitations,
    )


_REPLACEMENTS = {
    "PRIVATE_KEY": "[REDACTED_PRIVATE_KEY]",
    "AWS_ACCESS_KEY": "[REDACTED_AWS_KEY]",
    "GITHUB_TOKEN": "[REDACTED_GITHUB_TOKEN]",
    "API_SECRET_ASSIGNMENT": "[REDACTED_SECRET_ASSIGNMENT]",
    "OPENAI_STYLE_TOKEN": "[REDACTED_API_TOKEN]",
    "KOREAN_RRN_LIKE": "[REDACTED_RRN]",
    "KOREAN_MOBILE_PHONE": "[REDACTED_PHONE]",
    "EMAIL": "[REDACTED_EMAIL]",
}


def redact_text(text: str) -> tuple[str, ScanResult]:
    result = scan_text(text)
    spans = []
    for signal in result.signals:
        spans.append((signal.start, signal.end, _REPLACEMENTS.get(signal.kind, "[REDACTED]")))

    # Merge overlaps fail-closed: the first/highest-width replacement covers the span.
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    merged: list[tuple[int, int, str]] = []
    for start, end, replacement in spans:
        if merged and start < merged[-1][1]:
            if end > merged[-1][1]:
                prev = merged[-1]
                merged[-1] = (prev[0], end, prev[2])
            continue
        merged.append((start, end, replacement))

    out = text
    for start, end, replacement in reversed(merged):
        out = out[:start] + replacement + out[end:]
    return out, result
