#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B-track isolated probe: fetch Bluesky (ATProto) posts for Bitcoin/crypto discourse samples.

CRITICAL: Output is experiment-lane only. Do not wire scores into live trading or
start_24h_daemon.py without constitution gates and explicit promotion.

Requires: pip install "atproto>=0.0.67"  (gallery embed; older SDK fails pydantic on search_posts)
Auth:     BSKY_HANDLE or BSKY_EMAIL (or BLUESKY_*), plus BSKY_APP_PASSWORD (Bluesky App Password)

Default out: projects/bitcoin-trading/memory/v2/btrack/raw_feeds/atproto/YYYYMMDD_atproto_sentiment_raw.jsonl

Automation (optional): Invoke-BTrackAtprotoBlueskyProbe.ps1; Register-BTrackAtprotoBlueskyProbeTask.ps1
(weekly Sunday 09:00 default; not listed in automation_registry.json).

Downstream (separate steps; not implemented here): normalize discourse to Swarm metrics JSONL per
docs/final/SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json; validate with scripts/validate_swarm_sentiment_dummy.py
or scripts/Validate-SwarmSentimentBTrack.ps1. Label live extractions [HYPO] until promoted.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "v2"
    / "btrack"
    / "raw_feeds"
    / "atproto"
)

SOURCE_ID = "atproto_bluesky_v1"
CHANNEL_MARKER = "atproto_bluesky_v1"


def _env_identifier() -> str | None:
    """Bluesky login identifier: handle (e.g. user.bsky.social) or account email."""
    return (
        os.environ.get("BSKY_HANDLE")
        or os.environ.get("BLUESKY_HANDLE")
        or os.environ.get("BSKY_EMAIL")
        or os.environ.get("BSKY_IDENTIFIER")
        or os.environ.get("BLUESKY_EMAIL")
    )


def _env_password() -> str | None:
    return os.environ.get("BSKY_APP_PASSWORD") or os.environ.get("BLUESKY_APP_PASSWORD")


def _load_client():
    try:
        from atproto import Client  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "Missing dependency: install with  py -m pip install atproto\n"
            f"Import error: {e}"
        ) from e
    identifier = (_env_identifier() or "").strip()
    password = (_env_password() or "").strip()
    if not identifier or not password:
        raise SystemExit(
            "Set BSKY_HANDLE or BSKY_EMAIL (identifier) and BSKY_APP_PASSWORD in the environment."
        )
    client = Client()
    client.login(identifier, password)
    return client


def _namespace_from_dict(value: Any) -> Any:
    """Best-effort dict → attribute object for raw search_posts fallback."""
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _namespace_from_dict(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_namespace_from_dict(v) for v in value]
    return value


def _search_posts_page(client: Any, kwargs: dict[str, Any]) -> tuple[list[Any], str | None]:
    """Typed search with raw JSON fallback when pydantic rejects newer embed lexicons."""
    from atproto_client.models.app.bsky.feed.search_posts import Params  # type: ignore

    try:
        res = client.app.bsky.feed.search_posts(Params(**kwargs))
        posts = getattr(res, "posts", None) or []
        cursor = getattr(res, "cursor", None)
        return list(posts), cursor
    except Exception as exc:
        name = type(exc).__name__
        if name not in {"ValidationError"} and "validation" not in str(exc).lower():
            raise
        raw = client.invoke_query("app.bsky.feed.searchPosts", params=kwargs)
        if isinstance(raw, dict):
            posts_raw = raw.get("posts") or []
            cursor = raw.get("cursor")
        else:
            posts_raw = getattr(raw, "posts", None) or []
            cursor = getattr(raw, "cursor", None)
        posts: list[Any] = []
        for item in posts_raw:
            if hasattr(item, "record"):
                posts.append(item)
            elif isinstance(item, dict):
                posts.append(_namespace_from_dict(item))
            else:
                posts.append(item)
        return posts, cursor


def _iter_search_batches(
    client: Any,
    *,
    q: str | None,
    tag: str | None,
    per_request: int,
    max_posts: int,
    sort: str,
) -> Iterable[Any]:
    """Paginate search_posts until max_posts or no cursor."""
    cursor: str | None = None
    got = 0
    while got < max_posts:
        take = min(per_request, max_posts - got, 100)
        if take <= 0:
            break
        kwargs: dict[str, Any] = {"limit": take, "sort": sort}
        if q is not None:
            kwargs["q"] = q
        if tag is not None:
            kwargs["tag"] = tag
        if cursor:
            kwargs["cursor"] = cursor
        posts, cursor = _search_posts_page(client, kwargs)
        for p in posts:
            yield p
            got += 1
            if got >= max_posts:
                return
        if not cursor or not posts:
            return


def _post_to_row(
    pv: Any,
    *,
    collected_at: str,
    query_label: str,
) -> dict[str, Any]:
    rec = getattr(pv, "record", None)
    text = getattr(rec, "text", "") if rec is not None else ""
    langs = getattr(rec, "langs", None) if rec is not None else None
    created = getattr(rec, "created_at", None) if rec is not None else None
    author = getattr(pv, "author", None)
    handle = getattr(author, "handle", None) if author is not None else None
    return {
        "source_id": SOURCE_ID,
        "channel_marker": CHANNEL_MARKER,
        "non_collision": (
            "B-track experiment only; not promoted to live trading or constitution-locked facts."
        ),
        "bias_weight_hints": {
            "developer_heavy": None,
            "media_centric": None,
            "note": "manual or downstream calibration; not inferred in this probe",
        },
        "query_used": query_label,
        "collected_at_utc": collected_at,
        "uri": getattr(pv, "uri", None),
        "cid": getattr(pv, "cid", None),
        "created_at": created,
        "author_handle": handle,
        "text": text,
        "text_len": len(text),
        "langs": list(langs) if langs else [],
        "reply_count": getattr(pv, "reply_count", None),
        "repost_count": getattr(pv, "repost_count", None),
        "like_count": getattr(pv, "like_count", None),
    }


def _dedupe_posts(posts: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for p in posts:
        u = getattr(p, "uri", None)
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(p)
    return out


def _default_queries() -> list[tuple[str | None, str | None, str]]:
    """(q, tag, label) — align with draft spec: bitcoin + crypto/trading hashtags."""
    return [
        ("bitcoin", None, 'q="bitcoin"'),
        (None, "bitcoin", "tag=bitcoin"),
        (None, "crypto", "tag=crypto"),
        (None, "trading", "tag=trading"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Bluesky ATProto B-track sample collector (probe).")
    parser.add_argument("--limit", type=int, default=100, help="Target unique posts (default 100).")
    parser.add_argument(
        "--sort",
        choices=("latest", "top"),
        default="latest",
        help="Bluesky search sort (default latest).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for JSONL output.",
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Write .jsonl.gz instead of .jsonl.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate env/deps only; no network or disk write.",
    )
    args = parser.parse_args()

    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.dry_run:
        ident = _env_identifier()
        p = _env_password()
        print("dry-run: atproto import check…")
        try:
            import atproto  # noqa: F401
        except ImportError:
            print("dry-run: atproto not installed (py -m pip install atproto)")
            return 2
        print("dry-run: BSKY identifier (handle/email) set:", bool(ident))
        print("dry-run: BSKY_APP_PASSWORD set:", bool(p))
        print("dry-run: out dir would be:", args.out_dir)
        return 0

    client = _load_client()

    raw: list[Any] = []
    for q, tag, label in _default_queries():
        if len(_dedupe_posts(raw)) >= args.limit:
            break
        need = args.limit - len(_dedupe_posts(raw))
        for pv in _iter_search_batches(
            client,
            q=q,
            tag=tag,
            per_request=min(100, max(need, 1)),
            max_posts=need + 5,
            sort=args.sort,
        ):
            raw.append(pv)
            if len(_dedupe_posts(raw)) >= args.limit:
                break

    posts = _dedupe_posts(raw)[: args.limit]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = ".jsonl.gz" if args.compress else ".jsonl"
    out_path = args.out_dir / f"{day}_atproto_sentiment_raw{suffix}"

    rows = [_post_to_row(p, collected_at=collected_at, query_label="multi_query_v1") for p in posts]

    opener = gzip.open if args.compress else open
    mode = "wt" if args.compress else "w"
    encoding = "utf-8"
    with opener(out_path, mode, encoding=encoding, newline="\n") as f:  # type: ignore[arg-type]
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # stdout summary (no sentiment model; descriptive only)
    lens = [r["text_len"] for r in rows]
    avg_len = sum(lens) / len(lens) if lens else 0.0
    handles = [r["author_handle"] or "" for r in rows]
    unique_authors = len({h for h in handles if h})

    print(json.dumps(
        {
            "source_id": SOURCE_ID,
            "written": str(out_path),
            "n_posts": len(rows),
            "unique_authors": unique_authors,
            "avg_text_len": round(avg_len, 2),
            "sort": args.sort,
            "isolation": "B-track probe only",
        },
        ensure_ascii=False,
    ))

    if rows:
        sample = rows[0]["text"][:240].replace("\n", " ")
        print("sample_text_prefix:", sample + ("…" if len(rows[0]["text"]) > 240 else ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())
