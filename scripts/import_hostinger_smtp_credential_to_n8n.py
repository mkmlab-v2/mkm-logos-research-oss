#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.7, M:0.6}
# Balance: 91
# Purpose: Import Hostinger SMTP credential into local n8n from process env.
# Keywords: n8n, smtp, credential, import, secure

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _require_env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise SystemExit(f"Missing required env var: {name}")
    return v


def _to_bool(v: str) -> bool:
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> int:
    host = _require_env("HOSTINGER_SMTP_HOST")
    port = int(_require_env("HOSTINGER_SMTP_PORT"))
    secure = _to_bool(_require_env("HOSTINGER_SMTP_SECURE"))
    user = _require_env("HOSTINGER_SMTP_USER")
    password = _require_env("HOSTINGER_SMTP_PASS")
    sender = os.environ.get("HOSTINGER_SMTP_SENDER", "").strip() or user

    credential = [
        {
            "id": "hostinger-smtp-credential-v1",
            "name": "Hostinger SMTP",
            "type": "smtp",
            "data": {
                "host": host,
                "port": port,
                "secure": secure,
                "user": user,
                "password": password,
                "sender": sender,
            },
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        tmp = Path(f.name)
        f.write(json.dumps(credential, ensure_ascii=False, indent=2))

    n8n_exec = shutil.which("n8n") or shutil.which("n8n.cmd") or "n8n"

    try:
        proc = subprocess.run(
            [n8n_exec, "import:credentials", "--input", str(tmp)],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

    if proc.returncode != 0:
        raise SystemExit(f"n8n credential import failed ({proc.returncode}): {proc.stdout}\n{proc.stderr}")

    print("n8n_credential_import: PASS")
    print("credential_name=Hostinger SMTP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
