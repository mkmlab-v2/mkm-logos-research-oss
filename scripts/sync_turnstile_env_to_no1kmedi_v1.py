#!/usr/bin/env python3
"""Sync Turnstile sitekey/secret into projects/no1kmedi env files (no stdout secrets).

Sources (first hit):
  reports/cloudflare_turnstile_jema_ai_secret_LOCAL.json
  docs/final/artifacts/turnstile_jema_ai_widget_provision_v1_latest.json (sitekey only)

  py scripts/sync_turnstile_env_to_no1kmedi_v1.py
  py scripts/sync_turnstile_env_to_no1kmedi_v1.py --target production
  py scripts/sync_turnstile_env_to_no1kmedi_v1.py --target all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "reports" / "cloudflare_turnstile_jema_ai_secret_LOCAL.json"
PROVISION = ROOT / "docs" / "final" / "artifacts" / "turnstile_jema_ai_widget_provision_v1_latest.json"
NO1KMEDI = ROOT / "projects" / "no1kmedi"
KEYS = ("NEXT_PUBLIC_TURNSTILE_SITEKEY", "TURNSTILE_SECRET_KEY")
DEV_SKIP_KEY = "KM_TURNSTILE_SKIP_VERIFY"
COMMENT = "# Cloudflare Turnstile (jema-ai.com lead forms)"


def _load_pairs() -> dict[str, str]:
    out: dict[str, str] = {}
    if LOCAL.is_file():
        doc = json.loads(LOCAL.read_text(encoding="utf-8"))
        sk = str(doc.get("TURNSTILE_SITEKEY") or "").strip()
        sec = str(doc.get("TURNSTILE_SECRET_KEY") or "").strip()
        if sk:
            out["NEXT_PUBLIC_TURNSTILE_SITEKEY"] = sk
        if sec:
            out["TURNSTILE_SECRET_KEY"] = sec
    if PROVISION.is_file() and "NEXT_PUBLIC_TURNSTILE_SITEKEY" not in out:
        doc = json.loads(PROVISION.read_text(encoding="utf-8"))
        sk = str(doc.get("sitekey") or "").strip()
        if sk:
            out["NEXT_PUBLIC_TURNSTILE_SITEKEY"] = sk
    return out


def _upsert_env(path: Path, pairs: dict[str, str], *, remove_keys: tuple[str, ...] = ()) -> None:
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
    present = {k: False for k in pairs}
    remove = {k for k in remove_keys}
    new_lines: list[str] = []
    for ln in lines:
        stripped = ln.strip()
        hit = False
        for key in pairs:
            if stripped.startswith(f"{key}="):
                new_lines.append(f"{key}={pairs[key]}")
                present[key] = True
                hit = True
                break
        if hit:
            continue
        if any(stripped.startswith(f"{key}=") for key in remove):
            continue
        new_lines.append(ln)
    missing = [k for k in pairs if not present[k]]
    if missing:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(COMMENT)
        for key in missing:
            new_lines.append(f"{key}={pairs[key]}")
    path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def _sync_target(target: Path, pairs: dict[str, str], *, include_dev_skip: bool) -> None:
    sync_pairs = dict(pairs)
    remove: tuple[str, ...] = ()
    if include_dev_skip:
        sync_pairs[DEV_SKIP_KEY] = "1"
    else:
        remove = (DEV_SKIP_KEY,)
    _upsert_env(target, sync_pairs, remove_keys=remove)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--target",
        choices=("local", "production", "all"),
        default="local",
        help="local=.env.local+dev bypass; production=.env.production (no bypass); all=both",
    )
    args = ap.parse_args()

    pairs = _load_pairs()
    if not pairs.get("NEXT_PUBLIC_TURNSTILE_SITEKEY"):
        print("sync_turnstile_env: missing sitekey", file=sys.stderr)
        return 1
    if not pairs.get("TURNSTILE_SECRET_KEY"):
        print("sync_turnstile_env: missing secret", file=sys.stderr)
        return 1

    targets: list[tuple[Path, bool]] = []
    if args.target in ("local", "all"):
        targets.append((NO1KMEDI / ".env.local", True))
    if args.target in ("production", "all"):
        targets.append((NO1KMEDI / ".env.production", False))

    for path, include_dev_skip in targets:
        _sync_target(path, pairs, include_dev_skip=include_dev_skip)
        print(f"sync_turnstile_env: ok target={path} dev_skip={include_dev_skip}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
