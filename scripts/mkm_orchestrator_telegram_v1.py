#!/usr/bin/env python3
"""Telegram helpers for MKM-Orchestrator: HITL prompts (send) and optional GO ingestion."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = ROOT / ".env"


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def load_env_for_workspace(ws: Path) -> None:
    """Prefer workspace_root/.env, then repo root .env."""
    p = ws.resolve() / ".env"
    if p.is_file():
        _load_env_from_dotenv(p)
    else:
        _load_env_from_dotenv(DOTENV_PATH)


def _load_env_from_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if not key:
            continue
        if key in os.environ:
            continue
        os.environ[key] = value


def _audit(workspace_root: Path, event: str, **detail: object) -> None:
    p = workspace_root / "reports" / "mkm_orchestrator_audit.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "mkm_orchestrator_audit_v1",
        "ts_utc": _utc_now(),
        "event": event,
        "workspace_root": str(workspace_root),
    }
    row.update({k: v for k, v in detail.items() if v is not None})
    with p.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def telegram_send(bot_token: str, chat_id: str, text: str) -> None:
    base = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    )
    req = request.Request(f"{base}?{payload}", method="POST")
    try:
        with request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="ignore").strip()
            if resp.status >= 300:
                raise RuntimeError(f"Telegram send failed: HTTP {resp.status}, body={body}")
    except error.URLError as exc:
        raise RuntimeError(f"Telegram request failed: {exc}") from exc


def orchestrator_notify_enabled() -> bool:
    """Require explicit MKM_ORCHESTRATOR_TELEGRAM_NOTIFY=1 plus TELEGRAM_* credentials."""
    raw = os.getenv("MKM_ORCHESTRATOR_TELEGRAM_NOTIFY", "").strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return False
    return bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip()) and bool(
        os.getenv("TELEGRAM_CHAT_ID", "").strip()
    )


def notify_needs_approval(
    workspace_root: Path,
    task_id: str,
    title: str,
    idempotency_key: str,
    *,
    dry_run: bool = False,
) -> str:
    """
    Returns: sent | skipped_no_credentials | skipped_disabled | dry_run | error:...
    """
    load_env_for_workspace(workspace_root)
    ws = workspace_root.resolve()

    if dry_run:
        _audit(ws, "telegram_notify_skipped", reason="dry_run", task_id=task_id)
        return "dry_run"

    if not orchestrator_notify_enabled():
        _audit(ws, "telegram_notify_skipped", reason="notify_disabled_or_missing_env", task_id=task_id)
        return "skipped_disabled"

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        _audit(ws, "telegram_notify_skipped", reason="missing_token_or_chat_id", task_id=task_id)
        return "skipped_no_credentials"

    body = (
        f"MKM-Orchestrator: 승인 필요\n"
        f"- task_id: `{task_id}`\n"
        f"- title: {title}\n"
        f"- idempotency_key: `{idempotency_key}`\n\n"
        f"승인하려면 이 채팅에 다음을 보내세요:\n"
        f"GO {task_id}\n\n"
        f"(또는 로컬) py scripts/approve_mkm_orchestrator_task_v1.py --task-id {task_id}"
    )

    try:
        telegram_send(token, chat_id, body)
    except Exception as exc:
        _audit(ws, "telegram_notify_error", task_id=task_id, error=str(exc)[:300])
        return f"error:{exc}"

    _audit(ws, "telegram_notify_sent", task_id=task_id)
    return "sent"


_GO_RE = re.compile(r"^GO\s+(\S+)\s*$", re.IGNORECASE)


def parse_go_command(text: str) -> str | None:
    if not text:
        return None
    m = _GO_RE.match(text.strip())
    if not m:
        return None
    return m.group(1).strip()


def telegram_get_updates(bot_token: str, offset: int, timeout: int = 0) -> dict:
    q = parse.urlencode({"offset": offset, "timeout": timeout})
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates?{q}"
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    return json.loads(raw)


def _allowed_user_ids() -> set[int]:
    raw = os.getenv("MKM_ORCHESTRATOR_TELEGRAM_ALLOWED_USER_IDS", "").strip()
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def _offset_path(ws: Path) -> Path:
    return ws / "reports" / "mkm_orchestrator_telegram_offset.txt"


def cmd_ingest(workspace_root: Path, *, dry_run: bool) -> int:
    """Poll once for GO <task_id>, run approve CLI."""
    load_env_for_workspace(workspace_root)
    ws = workspace_root.resolve()
    offset_path = _offset_path(ws)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id_env = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id_env:
        _audit(ws, "telegram_ingest_skipped", reason="missing_credentials")
        return 0

    try:
        expected_chat = int(str(chat_id_env).strip())
    except ValueError:
        _audit(ws, "telegram_ingest_error", reason="invalid_TELEGRAM_CHAT_ID")
        return 1

    next_offset = 0
    if offset_path.is_file():
        try:
            last = int(offset_path.read_text(encoding="utf-8").strip())
            next_offset = last + 1
        except ValueError:
            next_offset = 0

    try:
        data = telegram_get_updates(token, next_offset, timeout=0)
    except Exception as exc:
        _audit(ws, "telegram_ingest_error", error=str(exc)[:300])
        return 1

    if not data.get("ok"):
        _audit(ws, "telegram_ingest_error", reason="telegram_api_not_ok", body=str(data)[:300])
        return 1

    results = data.get("result") or []
    max_id = -1
    approved_any = False

    allowed_users = _allowed_user_ids()
    approve_py = ws / "scripts" / "approve_mkm_orchestrator_task_v1.py"

    for upd in results:
        uid = upd.get("update_id")
        if isinstance(uid, int):
            max_id = max(max_id, uid)

        msg = upd.get("message") or upd.get("edited_message")
        if not isinstance(msg, dict):
            continue

        chat = msg.get("chat") or {}
        try:
            chat_id = int(chat.get("id"))
        except (TypeError, ValueError):
            continue

        if chat_id != expected_chat:
            continue

        from_user = msg.get("from") or {}
        uid_u = from_user.get("id")
        if allowed_users:
            try:
                if int(uid_u) not in allowed_users:
                    _audit(ws, "telegram_ingest_rejected_user", chat_id=chat_id, from_id=uid_u)
                    continue
            except (TypeError, ValueError):
                continue

        text = msg.get("text") or ""
        task_id = parse_go_command(text)
        if not task_id:
            continue

        if dry_run:
            _audit(ws, "telegram_ingest_dry_run_would_approve", task_id=task_id)
            approved_any = True
            continue

        if not approve_py.is_file():
            _audit(ws, "telegram_ingest_error", reason="approve_script_missing")
            return 1

        r = subprocess.run(
            [sys.executable, str(approve_py), "--task-id", task_id, "--workspace-root", str(ws)],
            cwd=str(ws),
            timeout=60,
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            _audit(ws, "telegram_approval_ingested", task_id=task_id, exit_code=0)
            approved_any = True
        else:
            _audit(
                ws,
                "telegram_approval_ingest_failed",
                task_id=task_id,
                exit_code=r.returncode,
                stderr=(r.stderr or "")[:400],
            )

    if max_id >= 0:
        offset_path.parent.mkdir(parents=True, exist_ok=True)
        if not dry_run:
            offset_path.write_text(str(max_id), encoding="utf-8")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_notify = sub.add_parser("notify", help="Send needs-approval prompt")
    p_notify.add_argument("--workspace-root", type=Path, default=ROOT)
    p_notify.add_argument("--task-id", required=True)
    p_notify.add_argument("--title", default="")
    p_notify.add_argument("--idempotency-key", default="")
    p_notify.add_argument("--dry-run", action="store_true")

    p_ingest = sub.add_parser("ingest", help="One-shot getUpdates + GO task_id -> approve")
    p_ingest.add_argument("--workspace-root", type=Path, default=ROOT)
    p_ingest.add_argument("--dry-run", action="store_true")

    p_ping = sub.add_parser("send-test", help="Send a short test message (credentials check)")
    p_ping.add_argument("--workspace-root", type=Path, default=ROOT)

    args = ap.parse_args()

    if args.cmd == "notify":
        r = notify_needs_approval(
            args.workspace_root,
            args.task_id,
            args.title or args.task_id,
            args.idempotency_key or f"{args.task_id}-v1",
            dry_run=args.dry_run,
        )
        print(r)
        return 0 if not str(r).startswith("error:") else 1

    if args.cmd == "ingest":
        return cmd_ingest(args.workspace_root, dry_run=args.dry_run)

    if args.cmd == "send-test":
        load_env_for_workspace(args.workspace_root)
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            print("SKIP: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
            return 1
        telegram_send(token, chat_id, f"MKM-Orchestrator ping {_utc_now()}")
        print("OK: sent")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
