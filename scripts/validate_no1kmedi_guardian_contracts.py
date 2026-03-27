#!/usr/bin/env python3
"""Static contract checks for no1kmedi guardian routes.

This repository can be used in lightweight operational mode where the
`projects/no1kmedi` app code is intentionally absent. In that case, we skip
contract validation and return success so the gate remains signal-only.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _must_include(text: str, needle: str, label: str, errors: list[str]) -> None:
    if needle not in text:
        errors.append(f"{label}: missing `{needle}`")


def main() -> int:
    errors: list[str] = []

    main_route = ROOT / "projects" / "no1kmedi" / "src" / "app" / "api" / "guardian" / "ai-guardian" / "route.ts"
    chat_route = ROOT / "projects" / "no1kmedi" / "src" / "app" / "api" / "guardian" / "ai-guardian" / "chat" / "route.ts"
    partner_chat = ROOT / "projects" / "no1kmedi" / "src" / "app" / "api" / "guardian" / "partner-clinics" / "chat" / "route.ts"

    target_files = [main_route, chat_route, partner_chat]
    if not any(p.is_file() for p in target_files):
        print("ℹ️ no1kmedi guardian sources not present in this repository; skipping strict contract checks")
        return 0

    for p in target_files:
        if not p.is_file():
            errors.append(f"missing file: {p}")
            continue
        text = _read(p)
        _must_include(text, "generateClinicalText", str(p), errors)

    if main_route.is_file():
        text = _read(main_route)
        _must_include(text, "JSON.parse", "ai-guardian/route.ts", errors)
        _must_include(text, "try {", "ai-guardian/route.ts", errors)
        _must_include(text, "provider_meta", "ai-guardian/route.ts", errors)

    if chat_route.is_file():
        text = _read(chat_route)
        _must_include(text, "meta:", "ai-guardian/chat/route.ts", errors)
        _must_include(text, "fallback_used", "ai-guardian/chat/route.ts", errors)

    if partner_chat.is_file():
        text = _read(partner_chat)
        _must_include(text, "meta:", "partner-clinics/chat/route.ts", errors)
        _must_include(text, "fallback_used", "partner-clinics/chat/route.ts", errors)

    if errors:
        print("❌ no1kmedi guardian contract validation failed")
        for e in errors:
            print(f"- {e}")
        return 1

    print("✅ no1kmedi guardian contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
