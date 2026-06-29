#!/usr/bin/env python3
"""Normalize .env Figma keys for clinic LOI (no secret values in stdout)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"

FIGMA_KEYS = (
    "FIGMA_ACCESS_TOKEN",
    "MKM_FIGMA_ACCESS_TOKEN",
    "MKM_CLINIC_LOI_FIGMA_FILE_KEY",
    "MKM_FIGMA_TEAM_ID",
)


def _parse_env_lines(text: str) -> list[str]:
    return text.splitlines()


def _extract_bare_figd_token(lines: list[str]) -> str | None:
    pat = re.compile(r"^figd_[A-Za-z0-9_-]{20,}$")
    for line in lines:
        s = line.strip()
        if pat.match(s):
            return s
    return None


def _read_existing_token(lines: list[str]) -> str | None:
    for line in lines:
        m = re.match(r"^(FIGMA_ACCESS_TOKEN|MKM_FIGMA_ACCESS_TOKEN)=(.*)$", line.strip())
        if m:
            val = m.group(2).strip().strip('"').strip("'")
            if val:
                return val
    return None


def bootstrap(token: str | None, file_key: str | None, team_id: str = "1342307617365175074") -> dict[str, bool]:
    if not ENV.is_file():
        raise FileNotFoundError(ENV)
    lines = _parse_env_lines(ENV.read_text(encoding="utf-8"))
    bare = _extract_bare_figd_token(lines)
    use_token = token or bare
    if not use_token and not file_key:
        return {"ok": False, "token_set": False, "file_key_set": False}
    if not use_token:
        use_token = _read_existing_token(lines)
    if not use_token and file_key:
        # file-key-only refresh (token block already in .env)
        use_token = None

    new_lines: list[str] = []
    seen = set()
    for line in lines:
        s = line.strip()
        if re.match(r"^figd_[A-Za-z0-9_-]{20,}$", s):
            continue
        m = re.match(r"^([A-Za-z0-9_]+)=(.*)$", s)
        if m and m.group(1) in FIGMA_KEYS:
            seen.add(m.group(1))
            continue
        new_lines.append(line)

    block = [
        "",
        "# Clinic LOI Figma (auto bootstrap)",
        f"MKM_FIGMA_TEAM_ID={team_id}",
    ]
    if use_token:
        block.extend(
            [
                f"FIGMA_ACCESS_TOKEN={use_token}",
                f"MKM_FIGMA_ACCESS_TOKEN={use_token}",
            ]
        )
    if file_key:
        block.append(f"MKM_CLINIC_LOI_FIGMA_FILE_KEY={file_key}")
    new_lines.extend(block)
    ENV.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    return {
        "ok": bool(use_token or file_key),
        "token_set": bool(use_token),
        "file_key_set": bool(file_key),
        "removed_bare_figd_line": bool(bare),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file-key", default="")
    ap.add_argument("--token", default="")
    args = ap.parse_args()
    fk = args.file_key.strip() or None
    tok = args.token.strip() or None
    result = bootstrap(tok, fk)
    print(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
