#!/usr/bin/env python3
"""Post to X via official API (tweepy) — preferred over browser paste for UR GTM posts 2-4.

Secrets (DPAPI via security_agent_manager or env):
  MKM_X_API_KEY / MKM_X_API_SECRET
  MKM_X_ACCESS_TOKEN / MKM_X_ACCESS_TOKEN_SECRET

Developer portal: https://developer.x.com/ → App → User authentication (OAuth 1.0a)
  Scopes: tweet.read, tweet.write, users.read, offline.access
Store (interactive DPAPI):
  powershell -File scripts\\Invoke-EncryptedSecretStore.ps1 -Action set -Key MKM_X_API_KEY
  (repeat for MKM_X_API_SECRET, MKM_X_ACCESS_TOKEN, MKM_X_ACCESS_TOKEN_SECRET)

Paste SSOT: reports/human_paste/universal_root_x_post_{2,3,4}.txt
Post 2 media: reports/human_paste/universal_root_smoke_terminal_evidence.png
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/x_api_post_v1_latest.json"
PASTE = ROOT / "reports/human_paste"

UR_POSTS: dict[int, dict[str, Path | None]] = {
    2: {
        "text": PASTE / "universal_root_x_post_2.txt",
        "media": PASTE / "universal_root_smoke_terminal_evidence.png",
    },
    3: {"text": PASTE / "universal_root_x_post_3.txt", "media": None},
    4: {"text": PASTE / "universal_root_x_post_4.txt", "media": None},
}

X_CHAR_LIMIT = 280
POST_GAP_SEC = 3.0
CORRECTION_PASTE = PASTE / "universal_root_x_public_correction_v1.txt"
DEFAULT_CORRECTION_REPLY_TO = "2068734802661175789"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_secret(name: str) -> str | None:
    val = (os.environ.get(name) or "").strip()
    if val:
        return val
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from security_agent_manager import get_security_agent  # type: ignore

        got = get_security_agent().get_env_var(name)
        if got and got.strip():
            return got.strip()
    except Exception:
        pass
    return None


def _x_creds() -> dict[str, str]:
    keys = {
        "MKM_X_API_KEY": _resolve_secret("MKM_X_API_KEY"),
        "MKM_X_API_SECRET": _resolve_secret("MKM_X_API_SECRET"),
        "MKM_X_ACCESS_TOKEN": _resolve_secret("MKM_X_ACCESS_TOKEN"),
        "MKM_X_ACCESS_TOKEN_SECRET": _resolve_secret("MKM_X_ACCESS_TOKEN_SECRET"),
    }
    missing = [k for k, v in keys.items() if not v]
    if missing:
        raise RuntimeError(f"missing_x_api_credentials:{','.join(missing)}")
    return {
        "consumer_key": keys["MKM_X_API_KEY"] or "",
        "consumer_secret": keys["MKM_X_API_SECRET"] or "",
        "access_token": keys["MKM_X_ACCESS_TOKEN"] or "",
        "access_token_secret": keys["MKM_X_ACCESS_TOKEN_SECRET"] or "",
    }


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").strip()


def _parse_posts(raw: str) -> list[int]:
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        n = int(part)
        if n not in UR_POSTS:
            raise ValueError(f"unsupported_post_number:{n}")
        out.append(n)
    return out or [2, 3, 4]


def _load_post_spec(num: int) -> dict[str, Any]:
    spec = UR_POSTS[num]
    text_path = spec["text"]
    media_path = spec.get("media")
    if not isinstance(text_path, Path) or not text_path.is_file():
        raise FileNotFoundError(f"paste_missing:{text_path}")
    text = _read(text_path)
    if len(text) > X_CHAR_LIMIT:
        raise ValueError(f"tweet_too_long:post_{num}:{len(text)}>{X_CHAR_LIMIT}")
    media: Path | None = None
    if media_path is not None:
        if not isinstance(media_path, Path) or not media_path.is_file():
            raise FileNotFoundError(f"media_missing:{media_path}")
        media = media_path
    return {
        "number": num,
        "text": text,
        "text_file": str(text_path.relative_to(ROOT)).replace("\\", "/"),
        "media_file": str(media.relative_to(ROOT)).replace("\\", "/") if media else None,
        "char_len": len(text),
    }


def _split_for_tweets(text: str, limit: int = X_CHAR_LIMIT) -> list[str]:
    """Split long correction paste into a reply thread (each chunk <= limit)."""
    chunks: list[str] = []
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    buf = ""
    for para in paras:
        if len(para) > limit:
            if buf:
                chunks.append(buf.strip())
                buf = ""
            rest = para
            while rest:
                if len(rest) <= limit:
                    chunks.append(rest)
                    break
                cut = rest.rfind(" ", 0, limit)
                if cut <= 0:
                    cut = limit
                chunks.append(rest[:cut].strip())
                rest = rest[cut:].strip()
        elif buf and len(buf) + 2 + len(para) > limit:
            chunks.append(buf.strip())
            buf = para
        else:
            buf = f"{buf}\n\n{para}".strip() if buf else para
    if buf:
        chunks.append(buf.strip())
    for chunk in chunks:
        if len(chunk) > limit:
            raise ValueError(f"chunk_too_long:{len(chunk)}>{limit}")
    return chunks


def _load_correction_thread(text_file: Path | None = None) -> list[dict[str, Any]]:
    path = text_file or CORRECTION_PASTE
    if not path.is_file():
        raise FileNotFoundError(f"paste_missing:{path}")
    text = _read(path)
    parts = _split_for_tweets(text)
    if not parts:
        raise ValueError("correction_empty")
    loaded: list[dict[str, Any]] = []
    for idx, part in enumerate(parts, start=1):
        loaded.append(
            {
                "number": f"correction_{idx}",
                "text": part,
                "text_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "media_file": None,
                "char_len": len(part),
                "thread_index": idx,
                "thread_total": len(parts),
            }
        )
    return loaded


def _upload_media(api: Any, path: Path) -> str:
    uploaded = api.media_upload(filename=str(path))
    media_id = getattr(uploaded, "media_id", None) or getattr(uploaded, "media_id_string", None)
    if not media_id:
        raise RuntimeError("media_upload_failed:no_media_id")
    return str(media_id)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--posts", default="2,3,4", help="Comma-separated post numbers (default 2,3,4)")
    ap.add_argument(
        "--correction-reply",
        action="store_true",
        help="Post correction paste as reply thread (default reply-to post 2 tweet)",
    )
    ap.add_argument(
        "--reply-to",
        default=DEFAULT_CORRECTION_REPLY_TO,
        help="Tweet id to reply to (first chunk only; rest chain)",
    )
    ap.add_argument(
        "--text-file",
        type=Path,
        default=None,
        help="Custom text file for --correction-reply (default universal_root_x_public_correction_v1.txt)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Validate paste files only; no API")
    ap.add_argument("--verify-auth", action="store_true", help="With dry-run: also verify API credentials + get_me")
    ap.add_argument(
        "--acknowledge-send",
        action="store_true",
        help="R4: commander ack required for live submit (send_gate default HOLD)",
    )
    ap.add_argument("--gap-sec", type=float, default=POST_GAP_SEC)
    args = ap.parse_args()

    correction_mode = args.correction_reply
    post_nums: list[int] = []
    loaded: list[dict[str, Any]] = []
    try:
        if correction_mode:
            loaded = _load_correction_thread(args.text_file)
        else:
            post_nums = _parse_posts(args.posts)
            for n in post_nums:
                loaded.append(_load_post_spec(n))
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    report: dict[str, Any] = {
        "schema": "x_api_post_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "track": "B-track",
        "generated_at_utc": _utc(),
        "mode": "correction_reply" if correction_mode else "posts",
        "posts_requested": post_nums if not correction_mode else None,
        "correction_reply_to": args.reply_to if correction_mode else None,
        "posts_loaded": loaded,
        "dry_run": args.dry_run,
        "verify_auth": args.verify_auth,
        "acknowledge_send": args.acknowledge_send,
        "ok": False,
        "results": [],
    }

    if args.dry_run and not args.verify_auth:
        report["ok"] = True
        report["status"] = "dry_run"
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "status": "dry_run", "posts": loaded}, ensure_ascii=False))
        return 0

    if not args.dry_run and not args.acknowledge_send:
        report["error"] = "send_gate_hold"
        report["status"] = "blocked_governance"
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": report["error"]}, ensure_ascii=False))
        return 5

    try:
        import tweepy  # type: ignore
    except ImportError:
        report["error"] = "tweepy_not_installed: pip install -r scripts/requirements-mkm-x-api.txt"
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": report["error"]}, ensure_ascii=False))
        return 2

    try:
        creds = _x_creds()
    except RuntimeError as exc:
        report["error"] = str(exc)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": report["error"]}, ensure_ascii=False))
        return 3

    auth = tweepy.OAuth1UserHandler(
        creds["consumer_key"],
        creds["consumer_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )
    api_v1 = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["consumer_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )

    me = client.get_me()
    user = me.data if me else None
    report["authenticated_as"] = getattr(user, "username", None) if user else None
    report["authenticated_id"] = getattr(user, "id", None) if user else None

    if args.dry_run and args.verify_auth:
        report["ok"] = bool(report["authenticated_as"])
        report["status"] = "verify_auth"
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {"ok": report["ok"], "status": "verify_auth", "user": report["authenticated_as"]},
                ensure_ascii=False,
            )
        )
        return 0 if report["ok"] else 4

    results: list[dict[str, Any]] = []
    reply_parent: str | None = str(args.reply_to).strip() if correction_mode else None
    for idx, spec in enumerate(loaded):
        if idx > 0 and args.gap_sec > 0:
            time.sleep(args.gap_sec)
        num = spec["number"]
        media_ids: list[str] | None = None
        if spec.get("media_file"):
            media_path = ROOT / str(spec["media_file"]).replace("/", os.sep)
            media_ids = [_upload_media(api_v1, media_path)]
        kwargs: dict[str, Any] = {"text": spec["text"]}
        if media_ids:
            kwargs["media_ids"] = media_ids
        if correction_mode and reply_parent:
            kwargs["in_reply_to_tweet_id"] = reply_parent
        try:
            resp = client.create_tweet(**kwargs)
        except Exception as exc:
            err_name = type(exc).__name__
            err_msg = str(exc)
            report["error"] = f"{err_name}:{err_msg}"
            report["status"] = "post_failed"
            report["results"] = results
            report["ok"] = False
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"ok": False, "error": report["error"], "partial_results": results}, ensure_ascii=False))
            if "402" in err_msg or "Payment Required" in err_msg:
                return 6
            return 1
        tweet_id = getattr(resp, "data", {}) or {}
        tid = tweet_id.get("id") if isinstance(tweet_id, dict) else getattr(tweet_id, "id", None)
        if correction_mode and tid:
            reply_parent = str(tid)
        url = f"https://x.com/i/web/status/{tid}" if tid else None
        row = {
            "post": num,
            "tweet_id": tid,
            "url": url,
            "char_len": spec["char_len"],
            "media_file": spec.get("media_file"),
            "thread_index": spec.get("thread_index"),
            "thread_total": spec.get("thread_total"),
            "in_reply_to": kwargs.get("in_reply_to_tweet_id"),
        }
        results.append(row)

    report["ok"] = True
    report["status"] = "posted"
    report["results"] = results
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": "posted", "results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
