#!/usr/bin/env python3
"""Bootstrap PATIENT_INTAKE_SOLAPI_TEST_WEBHOOK_URL in repo .env (append if missing)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
NO1KMEDI_ENV = ROOT / "projects/no1kmedi/.env.local"
DEFAULT_HOST = "http://srv1101456.hstgr.cloud:5678"
WEBHOOK_PATH = "/webhook/patient-intake-notification"
KEY = "PATIENT_INTAKE_SOLAPI_TEST_WEBHOOK_URL"
KAKAO_KEY = "KAKAO_CLINIC_INTAKE_WEBHOOK_URL"


def _read_env(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _derive_base(existing: str) -> str:
    for line in existing.splitlines():
        if line.strip().startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() in ("N8N_WEBHOOK_URL", "COMPRESSION_PILOT_AUDIT_LEAD_WEBHOOK_URL"):
            raw = val.strip().strip('"').strip("'")
            if raw:
                parsed = urlparse(raw)
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}"
    return DEFAULT_HOST


def _upsert(text: str, key: str, value: str) -> tuple[str, bool]:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    line = f"{key}={value}"
    if pattern.search(text):
        return pattern.sub(line, text), False
    suffix = "" if text.endswith("\n") or not text else "\n"
    block = f"\n# Patient intake internal PoC webhook (auto-bootstrap)\n{line}\n"
    return text + suffix + block, True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--base-url", default="", help="Override n8n base, e.g. http://host:5678")
    args = ap.parse_args()

    base = (args.base_url or _derive_base(_read_env(ENV))).rstrip("/")
    url = f"{base}{WEBHOOK_PATH}"

    env_text = _read_env(ENV)
    env_text, added1 = _upsert(env_text, KEY, url)
    env_text, added2 = _upsert(env_text, KAKAO_KEY, url)

    no1k_text = _read_env(NO1KMEDI_ENV)
    no1k_text, added3 = _upsert(no1k_text, KEY, url)
    no1k_text, added4 = _upsert(no1k_text, KAKAO_KEY, url)

    if not args.dry_run:
        if added1 or added2:
            ENV.write_text(env_text, encoding="utf-8")
        if added3 or added4 or not NO1KMEDI_ENV.is_file():
            NO1KMEDI_ENV.parent.mkdir(parents=True, exist_ok=True)
            NO1KMEDI_ENV.write_text(no1k_text if no1k_text else f"{KEY}={url}\n{KAKAO_KEY}={url}\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "webhook_url": url,
                "env_updated": not args.dry_run and (added1 or added2),
                "no1kmedi_env_local_updated": not args.dry_run and (added3 or added4 or not NO1KMEDI_ENV.is_file()),
                "n8n_workflow": "projects/no1kmedi/ops/n8n/patient_intake_notification_webhook_v1.json",
                "deploy_note": "Import workflow to n8n before expecting HTTP 200",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
