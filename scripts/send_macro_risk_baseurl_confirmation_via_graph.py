#!/usr/bin/env python3
"""Send Macro Risk Base URL confirmation email via Microsoft Graph API.

Required env vars:
  - GRAPH_TENANT_ID
  - GRAPH_CLIENT_ID
  - GRAPH_CLIENT_SECRET
  - GRAPH_SENDER_UPN          (e.g. sender@company.com)

Optional env vars:
  - GRAPH_RECIPIENT_EMAIL     (default: admin@no1kmedi.com)
  - GRAPH_MAIL_SUBJECT
  - GRAPH_MAIL_BODY_FILE      (default: docs/final/artifacts/macro_risk_warning_api_base_url_confirmation_email_live_v1.md)
"""

from __future__ import annotations

import json
import os
import urllib.error
from pathlib import Path
from typing import Any
from urllib import parse, request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BODY_FILE = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_base_url_confirmation_email_live_v1.md"
DEFAULT_SUBJECT = "[Action Required] Macro Risk Warning API 파일럿 Base URL 확정 요청"
DEFAULT_RECIPIENT = "admin@no1kmedi.com"


def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise SystemExit(f"Missing required env var: {name}")
    return val


def _http_post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    encoded = parse.urlencode(data).encode("utf-8")
    req = request.Request(url, data=encoded, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with request.urlopen(req, timeout=20) as resp:  # nosec B310 (trusted Graph endpoint)
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _http_post_json(url: str, token: str, payload: dict[str, Any]) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=20) as resp:  # nosec B310 (trusted Graph endpoint)
            status = getattr(resp, "status", 202)
            body = resp.read().decode("utf-8")
            return status, body
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        return int(getattr(exc, "code", 0) or 0), detail
    except Exception as exc:
        return 0, str(exc)


def _get_graph_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    token_doc = _http_post_form(token_url, data)
    token = str(token_doc.get("access_token", "")).strip()
    if not token:
        raise SystemExit(f"Failed to get Graph token: {token_doc}")
    return token


def _read_body_text(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Body file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def main() -> int:
    tenant_id = _require_env("GRAPH_TENANT_ID")
    client_id = _require_env("GRAPH_CLIENT_ID")
    client_secret = _require_env("GRAPH_CLIENT_SECRET")
    sender_upn = _require_env("GRAPH_SENDER_UPN")

    recipient = os.environ.get("GRAPH_RECIPIENT_EMAIL", DEFAULT_RECIPIENT).strip() or DEFAULT_RECIPIENT
    subject = os.environ.get("GRAPH_MAIL_SUBJECT", DEFAULT_SUBJECT).strip() or DEFAULT_SUBJECT
    body_file = Path(os.environ.get("GRAPH_MAIL_BODY_FILE", str(DEFAULT_BODY_FILE)))
    if not body_file.is_absolute():
        body_file = ROOT / body_file

    body_text = _read_body_text(body_file)
    token = _get_graph_token(tenant_id, client_id, client_secret)

    send_url = f"https://graph.microsoft.com/v1.0/users/{parse.quote(sender_upn)}/sendMail"
    payload: dict[str, Any] = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body_text},
            "toRecipients": [{"emailAddress": {"address": recipient}}],
        },
        "saveToSentItems": True,
    }

    status, body = _http_post_json(send_url, token, payload)
    if status not in {200, 202}:
        raise SystemExit(f"Graph sendMail failed (status={status}): {body}")

    print("graph_mail_send: PASS")
    print(f"sender={sender_upn}")
    print(f"recipient={recipient}")
    print(f"subject={subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

