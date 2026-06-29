#!/usr/bin/env python3
"""Morning KOSPI slim digest via email (Graph → Gmail SMTP → legacy Hostinger)."""

from __future__ import annotations

import argparse
import json
import os
import smtplib
import sys
import urllib.error
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib import parse, request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
DEFAULT_OUT = ROOT / "reports" / "kospi_morning_email_digest_latest.json"
DEFAULT_RECIPIENT = "moksorinw@gmail.com"


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, val)


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _resolve_secret(name: str) -> str:
    direct = os.getenv(name, "").strip()
    if direct:
        return direct
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from security_agent_manager import get_security_agent  # type: ignore

        got = get_security_agent().get_env_var(name)
        if got and str(got).strip():
            return str(got).strip()
    except Exception:
        pass
    return ""


def _default_recipient() -> str:
    for key in ("MKM_KOSPI_MORNING_EMAIL_TO", "MKM_MKMLIFE_SUPPORT_FORWARD_TO"):
        val = _resolve_secret(key) or os.getenv(key, "").strip()
        if val:
            return val
    return DEFAULT_RECIPIENT


def _build_body(workspace: Path) -> str:
    sys.path.insert(0, str(ROOT / "scripts"))
    import send_telegram_minimal_ops_digest_v1 as tg  # noqa: WPS433

    os.environ.setdefault("MKM_TELEGRAM_PROPHECY_SLIM", "1")
    os.environ.setdefault("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "0")
    os.environ.setdefault("MKM_TELEGRAM_PROPHECY_INCLUDE_MISSION_C_SHADOW", "0")
    os.environ.setdefault("MKM_TELEGRAM_MORNING_KOSPI_ONLY", "1")
    return tg.build_digest_prophecy(workspace)


def _graph_ready() -> bool:
    return all(
        _resolve_secret(k)
        for k in ("GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET", "GRAPH_SENDER_UPN")
    )


def _gmail_ready() -> bool:
    return bool(_resolve_secret("GMAIL_SMTP_USER") and _resolve_secret("GMAIL_APP_PASSWORD"))


def _hostinger_ready() -> bool:
    return bool(
        _resolve_secret("HOSTINGER_SMTP_HOST")
        and _resolve_secret("HOSTINGER_SMTP_USER")
        and _resolve_secret("HOSTINGER_SMTP_PASS")
    )


def _http_post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    encoded = parse.urlencode(data).encode("utf-8")
    req = request.Request(url, data=encoded, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with request.urlopen(req, timeout=20) as resp:  # nosec B310
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(url: str, token: str, payload: dict[str, Any]) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=20) as resp:  # nosec B310
            return int(getattr(resp, "status", 202)), resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        return int(getattr(exc, "code", 0) or 0), detail
    except Exception as exc:  # pragma: no cover
        return 0, str(exc)


def _send_graph(*, subject: str, body: str, recipient: str) -> Tuple[bool, str]:
    tenant = _resolve_secret("GRAPH_TENANT_ID")
    client = _resolve_secret("GRAPH_CLIENT_ID")
    secret = _resolve_secret("GRAPH_CLIENT_SECRET")
    sender = _resolve_secret("GRAPH_SENDER_UPN")
    if not all([tenant, client, secret, sender]):
        return False, "missing_graph_credentials"
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    token_doc = _http_post_form(
        token_url,
        {
            "client_id": client,
            "client_secret": secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
    )
    token = str(token_doc.get("access_token", "")).strip()
    if not token:
        return False, f"graph_token_failed:{token_doc}"
    send_url = f"https://graph.microsoft.com/v1.0/users/{parse.quote(sender)}/sendMail"
    payload: dict[str, Any] = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": recipient}}],
        },
        "saveToSentItems": True,
    }
    status, detail = _http_post_json(send_url, token, payload)
    if status in {200, 202}:
        return True, "graph_sent"
    return False, f"graph_send_failed:{status}:{detail[:200]}"


def _send_gmail_smtp(*, subject: str, body: str, recipient: str) -> Tuple[bool, str]:
    user = _resolve_secret("GMAIL_SMTP_USER")
    password = _resolve_secret("GMAIL_APP_PASSWORD")
    if not user or not password:
        return False, "missing_gmail_credentials"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = user
    message["To"] = recipient
    message.set_content(body)
    host = _resolve_secret("GMAIL_SMTP_HOST") or "smtp.gmail.com"
    port = int(_resolve_secret("GMAIL_SMTP_PORT") or "587")
    try:
        with smtplib.SMTP(host, port, timeout=20) as client:
            client.starttls()
            client.login(user, password)
            client.send_message(message)
        return True, "gmail_smtp_sent"
    except smtplib.SMTPAuthenticationError as exc:
        return False, f"gmail_auth_failed:{exc.smtp_code}"
    except Exception as exc:  # pragma: no cover
        return False, f"gmail_error:{exc}"


def _send_hostinger_smtp(*, subject: str, body: str, recipient: str) -> Tuple[bool, str]:
    host = _resolve_secret("HOSTINGER_SMTP_HOST")
    port_raw = _resolve_secret("HOSTINGER_SMTP_PORT") or "465"
    user = _resolve_secret("HOSTINGER_SMTP_USER")
    password = _resolve_secret("HOSTINGER_SMTP_PASS")
    sender = _resolve_secret("HOSTINGER_SMTP_SENDER") or user
    if not all([host, user, password]):
        return False, "missing_hostinger_credentials"
    try:
        port = int(port_raw)
    except ValueError:
        return False, "invalid_smtp_port"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)
    use_ssl = _truthy("HOSTINGER_SMTP_SECURE", default=True)
    errors: list[str] = []
    attempts = [(port, use_ssl)]
    if port != 587:
        attempts.append((587, False))
    for try_port, try_ssl in attempts:
        try:
            if try_ssl:
                with smtplib.SMTP_SSL(host, try_port, timeout=20) as client:
                    client.login(user, password)
                    client.send_message(message)
            else:
                with smtplib.SMTP(host, try_port, timeout=20) as client:
                    client.starttls()
                    client.login(user, password)
                    client.send_message(message)
            return True, f"hostinger_smtp_sent:{try_port}"
        except smtplib.SMTPAuthenticationError as exc:
            errors.append(f"auth:{try_port}:{exc.smtp_code}")
        except Exception as exc:  # pragma: no cover
            errors.append(f"error:{try_port}:{exc}")
    if errors and all(e.startswith("auth:") for e in errors):
        return False, "hostinger_auth_failed:" + ";".join(errors)
    return False, ";".join(errors) if errors else "hostinger_send_failed"


def _send_mail(*, subject: str, body: str, recipient: str) -> Tuple[bool, str]:
    transport = os.getenv("MKM_KOSPI_MORNING_EMAIL_TRANSPORT", "auto").strip().lower()
    order: list[str]
    if transport == "graph":
        order = ["graph"]
    elif transport == "gmail":
        order = ["gmail"]
    elif transport == "hostinger":
        order = ["hostinger"]
    else:
        order = ["graph", "gmail", "hostinger"]

    errors: list[str] = []
    for mode in order:
        if mode == "graph":
            if not _graph_ready():
                errors.append("graph:not_configured")
                continue
            ok, detail = _send_graph(subject=subject, body=body, recipient=recipient)
        elif mode == "gmail":
            if not _gmail_ready():
                errors.append("gmail:not_configured")
                continue
            ok, detail = _send_gmail_smtp(subject=subject, body=body, recipient=recipient)
        else:
            if not _hostinger_ready():
                errors.append("hostinger:not_configured")
                continue
            ok, detail = _send_hostinger_smtp(subject=subject, body=body, recipient=recipient)
        if ok:
            return True, detail
        errors.append(f"{mode}:{detail}")
    return False, "all_transports_failed:" + ";".join(errors)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Send even if MKM_KOSPI_MORNING_EMAIL_ENABLED is off")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    _load_dotenv()

    if not args.force and not _truthy("MKM_KOSPI_MORNING_EMAIL_ENABLED", default=False):
        print("SKIP: MKM_KOSPI_MORNING_EMAIL_ENABLED not set")
        return 0

    workspace = args.workspace_root.resolve()
    body = _build_body(workspace)
    print(body)
    cal = datetime.now(KST).strftime("%Y-%m-%d")
    subject = f"[MKM] 장전 코스피 · {cal}"
    recipient = _default_recipient()
    report: Dict[str, Any] = {
        "schema": "kospi_morning_email_digest_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subject": subject,
        "recipient_masked": f"***{recipient.rsplit('@', 1)[0][-2:]}@{recipient.rsplit('@', 1)[-1]}"
        if "@" in recipient
        else "unset",
        "char_count": len(body),
        "dry_run": args.dry_run,
        "ok": False,
    }
    preview = workspace / "reports" / "kospi_morning_email_digest_preview_latest.txt"
    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_text(body + "\n", encoding="utf-8")
    report["preview_path"] = str(preview.relative_to(workspace)).replace("\\", "/")

    if args.dry_run:
        report["ok"] = True
        report["result"] = "dry_run"
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {preview}")
        print("DRY RUN: not sent")
        return 0

    ok, detail = _send_mail(subject=subject, body=body, recipient=recipient)
    report["ok"] = ok
    report["result"] = detail
    report["transport_hint"] = os.getenv("MKM_KOSPI_MORNING_EMAIL_TRANSPORT", "auto")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print(f"ERROR: {detail}", file=sys.stderr)
        if "hostinger_auth_failed" in detail:
            print(
                "NOTE: Hostinger mail may be expired — use Graph/Gmail (default auto) or set "
                "MKM_KOSPI_MORNING_EMAIL_TO=moksorinw@gmail.com",
                file=sys.stderr,
            )
        return 1
    print(f"OK: {detail} -> {recipient}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
