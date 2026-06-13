#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B-track news bias-transparency shadow pipeline v0 ([HYPO] · research_only).

Fetches 3–5 RSS feeds (geography/category axes only — no ideology bins), clusters
headlines within a 24h window, optionally calls Gemini Flash (per cluster) + Pro
(synthesis), writes shadow JSON only.

NEVER auto-writes mkmlife public deck JSON. Human promotion required.

Examples:
  py scripts/test_news_neutralizer_v1.py --dry-run --fixture
  py scripts/test_news_neutralizer_v1.py --dry-run
  py scripts/test_news_neutralizer_v1.py --live --billing azure
  py scripts/test_news_neutralizer_v1.py --live --billing developer
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mkmlife.rss_minimal import parse_feed_items  # noqa: E402

try:
    from news_neutralizer_llm_v1 import llm_json, load_workspace_dotenv, resolve_billing  # noqa: E402
except ImportError:
    sys.path.insert(0, str(ROOT / "scripts"))
    from news_neutralizer_llm_v1 import llm_json, load_workspace_dotenv, resolve_billing  # noqa: E402

DEFAULT_SOURCES = ROOT / "data/mkmlife/rss_sources_neutralizer_v1.json"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/news_neutralizer_rss_fixture_v1.json"
DEFAULT_OUT = ROOT / "reports/news_neutralizer_shadow_v1_latest.json"

DEFAULT_FLASH_MODEL = "gemini-2.5-flash"
DEFAULT_PRO_MODEL = "gemini-2.5-pro"

STOPWORDS = frozenset(
    """
    a an the and or but in on at to for of with by from as is are was were be been
    being have has had do does did will would could should may might must can this
    that these those it its they them their he she his her we our you your not no
    """.split()
)

BANNED_COPY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("investment_advice_en", re.compile(r"\b(investment advice|buy now|sell now|guaranteed returns?)\b", re.I)),
    ("trade_pick_en", re.compile(r"\b(buy signal|sell signal|take profit|stop loss)\b", re.I)),
    ("trade_pick_ko", re.compile(r"(매수\s*추천|매도\s*추천|지금\s*사|지금\s*팔|수익\s*보장|투자\s*조언)")),
    ("portal_claim_ko", re.compile(r"(뉴스\s*포털(?!.*(아님|아니|대체\s*아님))|언론사\s*대체(?!.*아님)|편향\s*제거\s*완료|100%?\s*중립)")),
]

REQUIRED_DISCLAIMER_FRAGMENTS = (
    "관측",
    "투자",
    "[HYPO]",
)

BIAS_PROMPT_TEMPLATE = """You analyze news headline clusters for B-track bias transparency only.
Do NOT give investment, trading, or medical advice. Do NOT claim to remove bias — only surface framing differences.
Output JSON with keys: shared_facts (array of neutral fact strings), framing_signals (array of objects with source_feed_id, signal_ko, confidence in low|medium|high), bias_transparency_note_ko (Korean, must include [HYPO]).
Cluster headlines by source:
{cluster_json}
"""

SYNTHESIS_PROMPT_TEMPLATE = """Synthesize a B-track observation brief from bias analyses. No investment advice. Not a news portal.
Output JSON with keys: topic_summary_ko, verified_facts (array), parallel_perspectives (array of label_ko, summary_ko, source_urls), our_view_opinion_ko (must end with or contain [OPINION]), disclaimer_ko (must mention 관측, 투자·실매매 아님, and [HYPO]).
Bias analyses:
{analyses_json}
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _fetch(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "mkm-news-neutralizer/1.0 (+research-only)"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _parse_utc(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def normalize_title(title: str) -> str:
    t = (title or "").lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    tokens = [w for w in t.split() if w and w not in STOPWORDS]
    return " ".join(tokens)


def title_tokens(title: str) -> set[str]:
    norm = normalize_title(title)
    return {w for w in norm.split() if len(w) >= 3}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def cluster_items(items: list[dict[str, Any]], *, threshold: float = 0.35) -> list[list[dict[str, Any]]]:
    remaining = list(items)
    clusters: list[list[dict[str, Any]]] = []
    while remaining:
        seed = remaining.pop(0)
        seed_tokens = title_tokens(str(seed.get("title") or ""))
        group = [seed]
        keep: list[dict[str, Any]] = []
        for it in remaining:
            sim = jaccard(seed_tokens, title_tokens(str(it.get("title") or "")))
            if sim >= threshold:
                group.append(it)
            else:
                keep.append(it)
        remaining = keep
        clusters.append(group)
    return clusters


def filter_window(items: list[dict[str, Any]], *, hours: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[dict[str, Any]] = []
    for it in items:
        pub = _parse_utc(str(it.get("published_utc") or ""))
        if pub is None or pub >= cutoff:
            out.append(it)
    return out


def load_rss_items(
    *,
    sources_path: Path,
    fixture_path: Path | None,
    timeout: float,
    max_per_feed: int,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    errors: list[str] = []
    if fixture_path and fixture_path.is_file():
        doc = json.loads(fixture_path.read_text(encoding="utf-8-sig"))
        raw_items = doc.get("items") if isinstance(doc.get("items"), list) else []
        items: list[dict[str, Any]] = []
        for i, it in enumerate(raw_items):
            if not isinstance(it, dict):
                continue
            title = str(it.get("title") or "").strip()
            if not title:
                continue
            pub = (
                datetime.now(timezone.utc) - timedelta(hours=i)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            items.append(
                {
                    "title": title,
                    "link": str(it.get("link") or "").strip(),
                    "description": str(it.get("description") or "").strip(),
                    "published_utc": pub,
                    "source_feed_id": str(it.get("source_feed_id") or "fixture"),
                    "category": str(it.get("category") or "world"),
                }
            )
        return items, ["fixture"], errors

    cfg = json.loads(sources_path.read_text(encoding="utf-8-sig"))
    feeds = cfg.get("feeds") if isinstance(cfg.get("feeds"), list) else []
    items = []
    providers: list[str] = []
    for feed in feeds:
        if not isinstance(feed, dict) or not feed.get("enabled"):
            continue
        fid = str(feed.get("id") or "unknown")
        url = str(feed.get("url") or "").strip()
        if not url:
            errors.append(f"{fid}: missing url")
            continue
        providers.append(fid)
        try:
            raw = _fetch(url, timeout)
            parsed = parse_feed_items(raw)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            errors.append(f"{fid}: fetch failed: {exc}")
            continue
        for it in parsed[: max(1, max_per_feed)]:
            title = str(it.get("title") or "").strip()
            if not title:
                continue
            row: dict[str, Any] = {
                "title": title,
                "link": str(it.get("link") or "").strip(),
                "description": str(it.get("description") or title).strip(),
                "published_utc": str(it.get("published_utc") or _utc_now()),
                "source_feed_id": fid,
                "category": str(feed.get("category") or "world"),
            }
            items.append(row)
    return items, providers, errors


def build_cluster_records(groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group in groups:
        group_sorted = sorted(
            group,
            key=lambda x: _parse_utc(str(x.get("published_utc") or "")) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        rep = group_sorted[0]
        urls = []
        feed_ids = []
        for it in group_sorted:
            link = str(it.get("link") or "").strip()
            if link and link not in urls:
                urls.append(link)
            fid = str(it.get("source_feed_id") or "")
            if fid and fid not in feed_ids:
                feed_ids.append(fid)
        pub_max = str(rep.get("published_utc") or "")
        records.append(
            {
                "cluster_id": str(uuid.uuid4()),
                "representative_headline": str(rep.get("title") or ""),
                "member_count": len(group),
                "source_urls": urls,
                "source_feed_ids": feed_ids,
                "published_utc_max": pub_max,
                "members": [
                    {
                        "title": it.get("title"),
                        "link": it.get("link"),
                        "source_feed_id": it.get("source_feed_id"),
                        "published_utc": it.get("published_utc"),
                    }
                    for it in group_sorted
                ],
            }
        )
    return records


def lint_public_copy_v1(text: str) -> list[str]:
    violations: list[str] = []
    for label, pattern in BANNED_COPY_PATTERNS:
        if pattern.search(text or ""):
            violations.append(label)
    return violations


def _normalize_synthesis_for_lint_v1(synthesis: dict[str, Any]) -> None:
    """Ensure live LLM synthesis meets lint contract without re-calling the model."""
    disclaimer = str(synthesis.get("disclaimer_ko") or "")
    if "[HYPO]" not in disclaimer:
        if "(HYPO)" in disclaimer:
            disclaimer = disclaimer.replace("(HYPO)", "[HYPO]")
        else:
            disclaimer = f"{disclaimer.rstrip()} [HYPO]"
    if "관측" not in disclaimer:
        disclaimer = f"본 관측은 B-track 연구용입니다. {disclaimer}"
    if "투자" not in disclaimer:
        disclaimer = f"{disclaimer.rstrip()} 투자·실매매 권유가 아닙니다."
    synthesis["disclaimer_ko"] = disclaimer

    opinion = str(synthesis.get("our_view_opinion_ko") or "")
    if "[OPINION]" not in opinion:
        synthesis["our_view_opinion_ko"] = f"{opinion.rstrip()} [OPINION]"


def lint_shadow_doc_v1(doc: dict[str, Any]) -> list[str]:
    chunks: list[str] = []
    syn = doc.get("synthesis") if isinstance(doc.get("synthesis"), dict) else {}
    for key in ("topic_summary_ko", "our_view_opinion_ko", "disclaimer_ko"):
        val = syn.get(key)
        if isinstance(val, str):
            chunks.append(val)
    for ba in doc.get("bias_analyses") or []:
        if not isinstance(ba, dict):
            continue
        note = ba.get("bias_transparency_note_ko")
        if isinstance(note, str):
            chunks.append(note)
        for sig in ba.get("framing_signals") or []:
            if isinstance(sig, dict) and isinstance(sig.get("signal_ko"), str):
                chunks.append(sig["signal_ko"])
    violations: list[str] = []
    for chunk in chunks:
        violations.extend(lint_public_copy_v1(chunk))
    disclaimer = str(syn.get("disclaimer_ko") or "")
    for frag in REQUIRED_DISCLAIMER_FRAGMENTS:
        if frag not in disclaimer:
            violations.append(f"missing_disclaimer_fragment:{frag}")
    opinion = str(syn.get("our_view_opinion_ko") or "")
    if "[OPINION]" not in opinion:
        violations.append("missing_opinion_tag")
    return sorted(set(violations))


def _stub_bias_analysis(cluster: dict[str, Any], *, prompt_hash: str) -> dict[str, Any]:
    members = cluster.get("members") if isinstance(cluster.get("members"), list) else []
    facts = [str(cluster.get("representative_headline") or "")]
    signals = []
    for m in members[:4]:
        if not isinstance(m, dict):
            continue
        signals.append(
            {
                "source_feed_id": str(m.get("source_feed_id") or "unknown"),
                "signal_ko": f"헤드라인 프레이밍 차이 관측 — {m.get('title', '')[:80]} [HYPO]",
                "confidence": "low",
            }
        )
    return {
        "cluster_id": cluster.get("cluster_id"),
        "shared_facts": facts,
        "framing_signals": signals or [
            {"source_feed_id": "shadow", "signal_ko": "단일 출처 — 교차 프레이밍 비교 불가 [HYPO]", "confidence": "low"}
        ],
        "bias_transparency_note_ko": (
            "편향 제거가 아니라 출처별 프레이밍 차이를 투명화한 B-track 관측입니다 [HYPO]. "
            "투자·실매매·의료 조언이 아닙니다."
        ),
        "hypothesis_tag": "[HYPO]",
        "model_id": "dry_run_stub",
        "prompt_hash_sha256": prompt_hash,
    }


def _stub_synthesis(analyses: list[dict[str, Any]], *, prompt_hash: str) -> dict[str, Any]:
    facts: list[str] = []
    perspectives: list[dict[str, Any]] = []
    for ba in analyses[:3]:
        for f in ba.get("shared_facts") or []:
            if isinstance(f, str) and f not in facts:
                facts.append(f)
        for sig in (ba.get("framing_signals") or [])[:1]:
            if isinstance(sig, dict):
                perspectives.append(
                    {
                        "label_ko": f"출처 {sig.get('source_feed_id', 'unknown')}",
                        "summary_ko": str(sig.get("signal_ko") or ""),
                        "source_urls": [],
                    }
                )
    return {
        "topic_summary_ko": "24h RSS 헤드라인 클러스터에 대한 B-track 편향 투명화 shadow 요약 [HYPO]",
        "verified_facts": facts[:5] or ["관측 가능한 헤드라인만 수집 — 원문 링크에서 확인 필요"],
        "parallel_perspectives": perspectives or [
            {
                "label_ko": "교차 출처",
                "summary_ko": "동일 주제 클러스터가 없어 단일 관측만 기록 [HYPO]",
                "source_urls": [],
            }
        ],
        "our_view_opinion_ko": (
            "MKM은 헤드라인 무한 스크롤 미디어·매매 시그널 서비스가 아니라, "
            "멀티신호 관측 덱 연구 레일의 shadow 산출입니다 [OPINION]"
        ),
        "disclaimer_ko": (
            "B-track 관측 전용 — 투자·실매매·의료 판단을 대체하지 않습니다. "
            "헤드라인 피드·포털 대체가 아니며 human 승격 전 public deck에 반영되지 않습니다 [HYPO]."
        ),
        "hypothesis_tag": "[HYPO]",
        "model_id": "dry_run_stub",
        "prompt_hash_sha256": prompt_hash,
    }


def _run_live_llm(
    args: argparse.Namespace,
    *,
    clusters: list[dict[str, Any]],
    bias_prompt_hash: str,
    synth_prompt_hash: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], str, dict[str, str]]:
    system = "B-track news bias transparency assistant. JSON only. No investment advice."
    load_workspace_dotenv()
    if args.azure_inter_call_sleep >= 0:
        os.environ["MKM_AZURE_LLM_INTER_CALL_SLEEP_SEC"] = str(args.azure_inter_call_sleep)
    billing_surface = resolve_billing(args.billing)
    analyses: list[dict[str, Any]] = []
    model_flash = ""
    for cluster in clusters[: args.max_clusters]:
        user = BIAS_PROMPT_TEMPLATE.format(cluster_json=json.dumps(cluster, ensure_ascii=False))
        parsed, _, _, model_label = llm_json(
            billing=args.billing,
            system=system,
            user=user,
            timeout=args.gemini_timeout,
            flash_model=args.flash_model,
            pro_model=args.pro_model,
            azure_deployment=args.azure_deployment,
            use_pro_model=False,
        )
        model_flash = model_label
        parsed["cluster_id"] = cluster.get("cluster_id")
        parsed["hypothesis_tag"] = "[HYPO]"
        parsed["model_id"] = model_label
        parsed["prompt_hash_sha256"] = bias_prompt_hash
        parsed["billing_surface"] = billing_surface
        analyses.append(parsed)
    synth_user = SYNTHESIS_PROMPT_TEMPLATE.format(analyses_json=json.dumps(analyses, ensure_ascii=False))
    synthesis, _, _, model_pro = llm_json(
        billing=args.billing,
        system=system,
        user=synth_user,
        timeout=args.gemini_timeout,
        flash_model=args.flash_model,
        pro_model=args.pro_model,
        azure_deployment=args.azure_deployment,
        use_pro_model=True,
    )
    synthesis["hypothesis_tag"] = "[HYPO]"
    synthesis["model_id"] = model_pro
    synthesis["prompt_hash_sha256"] = synth_prompt_hash
    synthesis["billing_surface"] = billing_surface
    model_info = {"flash": model_flash, "pro": model_pro, "billing_surface": billing_surface}
    mode = "live_azure" if billing_surface == "azure" else f"live_{billing_surface}"
    return analyses, synthesis, mode, model_info


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    fixture = DEFAULT_FIXTURE if args.fixture else None
    items, providers, errors = load_rss_items(
        sources_path=args.sources_json,
        fixture_path=fixture,
        timeout=args.timeout_sec,
        max_per_feed=args.max_per_feed,
    )
    items = filter_window(items, hours=args.window_hours)
    groups = cluster_items(items, threshold=args.cluster_threshold)
    clusters = build_cluster_records(groups)

    bias_prompt_hash = _sha256_text(BIAS_PROMPT_TEMPLATE)
    synth_prompt_hash = _sha256_text(SYNTHESIS_PROMPT_TEMPLATE)

    mode = "fixture" if args.fixture else ("dry_run" if args.dry_run or not args.live else "live")
    analyses: list[dict[str, Any]] = []
    synthesis: dict[str, Any] = {}
    live_error: str | None = None
    model_info: dict[str, str] = {
        "flash": "dry_run_stub",
        "pro": "dry_run_stub",
        "billing_surface": "dry_run_stub",
    }

    if args.live and not args.dry_run:
        try:
            analyses, synthesis, mode, model_info = _run_live_llm(
                args,
                clusters=clusters,
                bias_prompt_hash=bias_prompt_hash,
                synth_prompt_hash=synth_prompt_hash,
            )
        except Exception as exc:
            live_error = str(exc)
            if not args.live_fallback_dry_run:
                raise RuntimeError(live_error) from exc
            mode = "live_fallback_dry_run"
            analyses = []
            for cluster in clusters[: args.max_clusters]:
                analyses.append(_stub_bias_analysis(cluster, prompt_hash=bias_prompt_hash))
            synthesis = _stub_synthesis(analyses, prompt_hash=synth_prompt_hash)
            synthesis["live_fallback_reason"] = live_error[:500]
            model_info = {
                "flash": "dry_run_stub",
                "pro": "dry_run_stub",
                "billing_surface": f"fallback_after_{args.billing}",
            }
    else:
        for cluster in clusters[: args.max_clusters]:
            analyses.append(_stub_bias_analysis(cluster, prompt_hash=bias_prompt_hash))
        synthesis = _stub_synthesis(analyses, prompt_hash=synth_prompt_hash)

    if synthesis:
        _normalize_synthesis_for_lint_v1(synthesis)

    doc: dict[str, Any] = {
        "schema": "news_neutralizer_shadow_v1",
        "generated_at_utc": _utc_now(),
        "lane": "research_only",
        "hypothesis_tag": "[HYPO]",
        "promotion_required": True,
        "auto_deck_publish": False,
        "window_hours": args.window_hours,
        "ingest": {
            "adapter": "test_news_neutralizer_v1",
            "sources_json": _rel(args.sources_json),
            "fixture": bool(args.fixture),
            "items_in_window": len(items),
            "clusters_built": len(clusters),
            "fetch_errors": errors,
        },
        "clusters": [
            {k: v for k, v in c.items() if k != "members"} for c in clusters[: args.max_clusters]
        ],
        "bias_analyses": analyses,
        "synthesis": synthesis,
        "provenance": {
            "mode": mode,
            "rss_sources": providers,
            "billing_requested": args.billing,
            "billing_surface": model_info.get("billing_surface"),
            "live_error": live_error,
            "models": {
                "flash": model_info.get("flash", "dry_run_stub"),
                "pro": model_info.get("pro", "dry_run_stub"),
            },
            "prompt_hashes": {
                "bias_analysis": bias_prompt_hash,
                "synthesis": synth_prompt_hash,
            },
        },
    }
    violations = lint_shadow_doc_v1(doc)
    doc["copy_lint"] = {"passed": len(violations) == 0, "violations": violations}
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="B-track news neutralizer shadow v0")
    ap.add_argument("--sources-json", type=Path, default=DEFAULT_SOURCES)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window-hours", type=int, default=24)
    ap.add_argument("--max-per-feed", type=int, default=10)
    ap.add_argument("--max-clusters", type=int, default=5)
    ap.add_argument("--cluster-threshold", type=float, default=0.35)
    ap.add_argument("--timeout-sec", type=float, default=20.0)
    ap.add_argument("--gemini-timeout", type=int, default=120)
    ap.add_argument("--flash-model", default=DEFAULT_FLASH_MODEL)
    ap.add_argument("--pro-model", default=DEFAULT_PRO_MODEL)
    ap.add_argument("--dry-run", action="store_true", help="No LLM calls (default unless --live)")
    ap.add_argument("--live", action="store_true", help="Call LLM via --billing surface")
    ap.add_argument(
        "--billing",
        choices=("auto", "azure", "developer", "vertex"),
        default="auto",
        help="LLM billing: auto prefers Azure when AZURE_OPENAI_* set (MKM_LLM_PRIORITY=azure_first)",
    )
    ap.add_argument(
        "--azure-inter-call-sleep",
        type=int,
        default=-1,
        help="Seconds between Azure LLM calls (default: env MKM_AZURE_LLM_INTER_CALL_SLEEP_SEC or 20)",
    )
    ap.add_argument(
        "--azure-deployment",
        default="",
        help="Override AZURE_OPENAI_DEPLOYMENT for this run",
    )
    ap.add_argument(
        "--live-fallback-dry-run",
        action="store_true",
        default=True,
        help="On live API failure, fall back to stub (default: true)",
    )
    ap.add_argument(
        "--no-live-fallback-dry-run",
        action="store_false",
        dest="live_fallback_dry_run",
        help="Fail hard when --live LLM call errors",
    )
    ap.add_argument("--fixture", action="store_true", help="Use tests/fixtures RSS fixture (no network)")
    ap.add_argument("--strict-lint", action="store_true", help="Exit 1 if copy_lint fails")
    args = ap.parse_args()

    if not args.live:
        args.dry_run = True

    try:
        doc = run_pipeline(args)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out_path = args.output_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": _rel(out_path), "copy_lint_passed": doc["copy_lint"]["passed"]}))

    if args.strict_lint and not doc["copy_lint"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
