#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry B power-user infra compliance gate — block cloud IDE + PHI co-occurrence.

research_only · send_gate: HOLD on block · Track B local harness only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "docs/final/artifacts/infra_compliance_gate_v1_latest.json"

CLOUD_IDE_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"replit\.com", re.I),
    re.compile(r"\bREPLIT_", re.I),
    re.compile(r"github\.dev", re.I),
    re.compile(r"codespaces", re.I),
    re.compile(r"gitpod\.io", re.I),
    re.compile(r"stackblitz\.com", re.I),
)

PHI_PAYMENT_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d{6}[\s-]?\d{7}"),
    re.compile(r"patient_name|환자명|주민등록|주민번호", re.I),
    re.compile(r"\bPHI\b|\bPII\b"),
    re.compile(r"결제(?:카드|정보)|card_number|\bcvv\b", re.I),
    re.compile(r"soap_note|clinical_chart|patient_care_bundle", re.I),
)

SENSITIVE_FILENAMES: frozenset[str] = frozenset(
    {".env", ".env.local", "replit.nix", ".replit"}
)


@dataclass(frozen=True)
class ScanResult:
    ok: bool
    blocked: bool
    cloud_hits: tuple[str, ...]
    phi_hits: tuple[str, ...]
    path: str | None
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "blocked": self.blocked,
            "send_gate": "HOLD" if self.blocked else "HOLD",
            "cloud_hits": list(self.cloud_hits),
            "phi_hits": list(self.phi_hits),
            "path": self.path,
            "reasons": list(self.reasons),
        }


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pattern_labels(patterns: tuple[re.Pattern[str], ...], text: str) -> tuple[str, ...]:
    return tuple(p.pattern for p in patterns if p.search(text))


def _strip_env_comments(text: str) -> str:
    """Ignore # comment lines when scanning .env-style payloads."""
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))


def _is_env_like(path: str | None) -> bool:
    if not path or path == "<stdin>":
        return path == "<stdin>"
    name = Path(path).name
    return name in SENSITIVE_FILENAMES or name.endswith(".env")


def analyze_text(text: str, *, path: str | None = None) -> ScanResult:
    payload = _strip_env_comments(text) if _is_env_like(path) else text

    cloud_hits = _pattern_labels(CLOUD_IDE_MARKERS, payload)
    phi_hits = _pattern_labels(PHI_PAYMENT_MARKERS, payload)
    reasons: list[str] = []

    blocked = bool(cloud_hits and phi_hits)
    if blocked:
        reasons.append("cloud_ide_and_phi_co_occurrence")

    if _is_env_like(path) and phi_hits and not blocked:
        blocked = True
        reasons.append("phi_in_sensitive_env_file")

    ok = not blocked
    return ScanResult(
        ok=ok,
        blocked=blocked,
        cloud_hits=cloud_hits,
        phi_hits=phi_hits,
        path=path,
        reasons=tuple(reasons),
    )


def scan_file(path: Path) -> ScanResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    return analyze_text(text, path=str(path))


def scan_paths(paths: list[Path]) -> list[ScanResult]:
    results: list[ScanResult] = []
    for path in paths:
        if path.is_file():
            results.append(scan_file(path))
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and _is_env_like(str(child)):
                    results.append(scan_file(child))
    return results


def build_report(results: list[ScanResult]) -> dict[str, Any]:
    blocked = [r for r in results if r.blocked]
    return {
        "schema": "infra_compliance_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": not blocked,
        "blocked_count": len(blocked),
        "scanned": len(results),
        "results": [r.to_dict() for r in results],
        "reproduce": "py scripts/infra_compliance_gate_v1.py <paths...>",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", type=Path, help="Files or dirs to scan")
    ap.add_argument("--stdin", action="store_true", help="Read payload from stdin")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    results: list[ScanResult] = []
    if args.stdin:
        text = sys.stdin.read()
        results.append(analyze_text(text, path="<stdin>"))
    elif args.paths:
        results = scan_paths(list(args.paths))
    else:
        ap.error("provide paths or --stdin")

    report = build_report(results)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {"ok": report["ok"], "blocked_count": report["blocked_count"], "send_gate": "HOLD"}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
