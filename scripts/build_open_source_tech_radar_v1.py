#!/usr/bin/env python3
"""Open-source tech radar v1 — B-track research_only; default offline refresh.

Refreshes docs/final/artifacts/open_source_tech_radar_latest.json from MKM watchlist
+ optional prior snapshot. Network fetch is opt-in (--fetch or MKM_OSS_TECH_RADAR_FETCH=1).
Does not promote Track A or enable live trading.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "open_source_tech_radar_latest.json"
BUILD_REPORT = ROOT / "reports" / "open_source_tech_radar_build_v1_latest.json"

GITHUB_WATCHLIST = (
    "docling-project/docling",
    "k2-fsa/sherpa-onnx",
    "supertone-inc/supertonic",
    "Manavarya09/design-extract",
    "pascalorg/editor",
    "langchain-ai/langgraph",
    "run-llama/llama_index",
)

HF_WATCHLIST = (
    "Supertone/supertonic-3",
    "openai/gpt-oss-20b",
    "meta-llama/Llama-3.2-1B-Instruct",
    "Qwen/Qwen3-4B-Instruct-2507",
)

UPGRADE_TARGETS = (
    {
        "name": "Forge-style guardrail lane",
        "why": "Reduce tool-call/runtime failures with explicit validation and recovery policy.",
        "priority": "P0",
    },
    {
        "name": "Docling + docling-mcp (document ingress)",
        "why": "Local PDF/OCR ingress for B2B and air-gap; replaces paid cloud OCR for scoped PoC.",
        "priority": "P0",
    },
    {
        "name": "Sherpa-ONNX (local STT ingress)",
        "why": "Symmetric pair to Supertonic TTS; feeds stt_routing_audit_log_v1 route=local.",
        "priority": "P0",
    },
    {
        "name": "CodeGraph-like local context map",
        "why": "Lower token and search overhead for large codebase operations.",
        "priority": "P1",
    },
    {
        "name": "smolagents rapid sandbox",
        "why": "Fast experimental agent loops in isolated tasks.",
        "priority": "P1",
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _composite_score(score_raw: float, comments_raw: float) -> float:
    return round(
        75 * math.log10(max(score_raw, 1.0)) + 25 * math.log10(max(comments_raw, 1.0)),
        4,
    )


def _http_json(url: str, *, timeout_sec: float = 12.0) -> dict[str, Any] | None:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "mkm-open-source-tech-radar-v1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def _github_entry(full_name: str, *, fetch: bool) -> dict[str, Any] | None:
    if fetch:
        data = _http_json(f"https://api.github.com/repos/{full_name}")
        if data:
            stars = float(data.get("stargazers_count") or 0)
            forks = float(data.get("forks_count") or 0)
            return {
                "source": "github",
                "id": full_name,
                "title": full_name,
                "url": data.get("html_url") or f"https://github.com/{full_name}",
                "score_raw": stars,
                "comments_raw": forks,
                "meta": {
                    "language": data.get("language"),
                    "open_issues": data.get("open_issues"),
                    "pushed_at": data.get("pushed_at"),
                    "description": (data.get("description") or "")[:240],
                },
                "score": _composite_score(stars, forks),
            }
    return None


def _hf_entry(model_id: str, *, fetch: bool) -> dict[str, Any] | None:
    if fetch:
        data = _http_json(f"https://huggingface.co/api/models/{model_id}")
        if data:
            downloads = float(data.get("downloads") or 0)
            likes = float(data.get("likes") or 0)
            return {
                "source": "huggingface",
                "id": model_id,
                "title": model_id,
                "url": f"https://huggingface.co/{model_id}",
                "score_raw": downloads,
                "comments_raw": likes,
                "meta": {
                    "pipeline_tag": data.get("pipeline_tag"),
                    "library_name": data.get("library_name"),
                    "last_modified": data.get("lastModified") or data.get("last_modified"),
                },
                "score": _composite_score(downloads, likes),
            }
    return None


def _load_previous(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    if doc.get("schema_version") != "open_source_tech_radar_v1":
        return None
    return doc


def _entries_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = f"{row.get('source')}:{row.get('id')}"
        out[key] = row
    return out


def _flatten_previous(previous: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not previous:
        return []
    rows: list[dict[str, Any]] = []
    top = previous.get("top_by_source") or {}
    if isinstance(top, dict):
        for bucket in top.values():
            if isinstance(bucket, list):
                rows.extend(bucket)
    global_top = previous.get("global_top")
    if isinstance(global_top, list):
        rows.extend(global_top)
    return rows


def build_radar(*, include_fetch: bool, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = _entries_by_id(_flatten_previous(previous))
    fetch_errors: list[str] = []

    for repo in GITHUB_WATCHLIST:
        entry = _github_entry(repo, fetch=include_fetch)
        if entry:
            merged[f"github:{repo}"] = entry
        elif include_fetch:
            fetch_errors.append(f"github:{repo}")

    for model_id in HF_WATCHLIST:
        entry = _hf_entry(model_id, fetch=include_fetch)
        if entry:
            merged[f"huggingface:{model_id}"] = entry
        elif include_fetch:
            fetch_errors.append(f"huggingface:{model_id}")

    all_rows = sorted(merged.values(), key=lambda r: float(r.get("score") or 0), reverse=True)
    github_rows = [r for r in all_rows if r.get("source") == "github"][:12]
    hf_rows = [r for r in all_rows if r.get("source") == "huggingface"][:12]
    hn_rows = [r for r in all_rows if r.get("source") == "hackernews"][:5]

    if include_fetch and not hn_rows:
        hn = _http_json("https://hacker-news.firebaseio.com/v0/topstories.json")
        if isinstance(hn, list) and hn:
            story = _http_json(f"https://hacker-news.firebaseio.com/v0/item/{hn[0]}.json")
            if isinstance(story, dict) and story.get("title"):
                score_raw = float(story.get("score") or 0)
                comments_raw = float(story.get("descendants") or 0)
                hn_rows = [
                    {
                        "source": "hackernews",
                        "id": str(story.get("id")),
                        "title": str(story.get("title"))[:240],
                        "url": story.get("url") or f"https://news.ycombinator.com/item?id={story.get('id')}",
                        "score_raw": score_raw,
                        "comments_raw": comments_raw,
                        "meta": {
                            "by": story.get("by"),
                            "unix_time": story.get("time"),
                        },
                        "score": _composite_score(score_raw, comments_raw),
                    }
                ]

    build_mode = "fetch_ok" if include_fetch and not fetch_errors else (
        "fetch_partial" if include_fetch else "offline_refresh"
    )

    return {
        "schema_version": "open_source_tech_radar_v1",
        "generated_at_utc": _utc_now(),
        "build_mode": build_mode,
        "previous_generated_at_utc": (previous or {}).get("generated_at_utc"),
        "mkm_watchlist": {
            "github": list(GITHUB_WATCHLIST),
            "huggingface": list(HF_WATCHLIST),
        },
        "fetch_errors": fetch_errors,
        "source_counts": {
            "hackernews": len(hn_rows),
            "github": len(github_rows),
            "huggingface": len(hf_rows),
            "total": len(hn_rows) + len(github_rows) + len(hf_rows),
        },
        "top_by_source": {
            "huggingface": hf_rows[:5],
            "github": github_rows[:5],
            "hackernews": hn_rows[:1],
        },
        "global_top": all_rows[:10],
        "upgrade_targets": list(UPGRADE_TARGETS),
        "disclaimer": "research_only",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch GitHub/HF/HN watchlist (network); merges with prior snapshot",
    )
    args = ap.parse_args()
    env_fetch = os.environ.get("MKM_OSS_TECH_RADAR_FETCH", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    include_fetch = bool(args.fetch or env_fetch)
    previous = _load_previous(args.out_json)
    doc = build_radar(include_fetch=include_fetch, previous=previous)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        out_rel = str(args.out_json.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        out_rel = str(args.out_json).replace("\\", "/")
    report = {
        "schema": "open_source_tech_radar_build_v1",
        "generated_at_utc": doc["generated_at_utc"],
        "build_mode": doc["build_mode"],
        "out_json": out_rel,
        "source_counts": doc["source_counts"],
        "fetch_errors": doc["fetch_errors"],
        "reproduce": "py scripts/build_open_source_tech_radar_v1.py",
        "reproduce_fetch": "py scripts/build_open_source_tech_radar_v1.py --fetch",
        "research_only": True,
    }
    BUILD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    BUILD_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out_json} mode={doc['build_mode']} total={doc['source_counts']['total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
