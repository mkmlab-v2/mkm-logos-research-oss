#!/usr/bin/env python3
"""Build mkmlife Observation Deck JSON from news_observation_v1 JSONL.

B-track only — thin deck (5 cards default) for mkmlife.com/news-deck.
Quality gate reads offline NEWS-RT bench snapshot; HOLD when proxy below floor.
Does not promote to Track A or live trading.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS_JSONL = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_BENCH = ROOT / "docs/final/artifacts/saving_the_news_news_rt_bench_result_v1_latest.json"
DEFAULT_PHASE1 = ROOT / "docs/final/artifacts/saving_the_news_phase1_poc_status_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkmlife_news_observation_deck_v1_latest.json"
MKMLIFE_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data"
JACCARD_FLOOR_DEFAULT = 0.40

_SOURCE_LABEL_KO: dict[str, str] = {
    "external_feed_bbc_world": "BBC 세계",
    "bbc_world": "BBC 세계",
    "external_feed_bbc_business": "BBC 경제",
    "bbc_business": "BBC 경제",
    "fixture_feed": "테스트 피드",
}

_CATEGORY_LABEL_KO: dict[str, tuple[str, str]] = {
    "external_feed_bbc_world": ("world", "세계"),
    "bbc_world": ("world", "세계"),
    "external_feed_bbc_business": ("finance", "경제"),
    "bbc_business": ("finance", "경제"),
}


def _category_from_source_id(source_id: str | None) -> tuple[str | None, str | None]:
    if not source_id:
        return None, None
    sid = source_id.strip().lower()
    if sid in _CATEGORY_LABEL_KO:
        return _CATEGORY_LABEL_KO[sid]
    if "business" in sid or "finance" in sid:
        return "finance", "경제"
    if "world" in sid:
        return "world", "세계"
    return None, None

_ASK_PREFILL_KO = (
    "오늘의 뉴스 관측 맥락(B-track·[HYPO])을 바탕으로, "
    "내 상황에 맞는 다음 한 가지 질문을 정리해 주세요. "
    "(원문 헤드라인은 카드의 「원문 보기」 링크에서 확인해 주세요.)"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get("schema_version") == "news_observation_v1":
            rows.append(row)
    return rows


def _headline(canonical_text: str) -> str:
    parts = [p.strip() for p in canonical_text.split("|") if p.strip()]
    text = parts[0] if parts else canonical_text.strip()
    return text[:160]


def _has_hangul(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


def _source_label_ko(source_id: str | None) -> str:
    if not source_id:
        return "외부 피드"
    return _SOURCE_LABEL_KO.get(source_id, source_id.replace("_", " "))


def _content_lang(text: str) -> str:
    return "ko" if _has_hangul(text) else "en"


def _headline_display_ko(headline: str, source_id: str | None) -> tuple[str, str | None]:
    """Korean UI title; returns (display_ko, headline_original when source is non-Korean)."""
    if _has_hangul(headline):
        return headline, None
    label = _source_label_ko(source_id)
    return f"{label} 속보 관측 (원문 영문·링크에서 확인)", headline


def _summary_display_ko(canonical: str, headline_original: str | None) -> str:
    if _has_hangul(canonical):
        return _compress_summary(canonical)
    excerpt = (headline_original or _headline(canonical))[:140].strip()
    if not excerpt:
        return "연구용 압축 요약(영문 원문 기반). 상세는 원문 링크를 확인하세요."
    return f"연구용 압축 요약(영문 원문 기반): {excerpt}…"


def _compress_summary(text: str, *, ratio: float = 0.55, min_len: int = 80, max_len: int = 280) -> str:
    words = re.findall(r"[A-Za-z0-9가-힣]+", text)
    seen: set[str] = set()
    kept: list[str] = []
    for w in words:
        wl = w.lower()
        if wl in seen:
            continue
        seen.add(wl)
        kept.append(w)
    compact = " ".join(kept) or text.strip()
    target_len = max(min_len, int(len(text) * ratio))
    target_len = min(target_len, max_len)
    if len(compact) <= target_len:
        out = compact
    else:
        out = compact[:target_len].strip()
    if len(out) < min_len and len(text) >= min_len:
        return text[:max_len].strip()
    return out[:max_len]


def _ask_prefill(lang: str = "ko") -> str:
    if lang == "en":
        return (
            "Based on this B-track news observation (see card link for original headline), "
            "help me shape one personal question for my situation."
        )
    return _ASK_PREFILL_KO


def _row_sort_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("as_of_utc") or ""), str(row.get("observation_id") or ""))


def _select_rows_for_deck(
    rows: list[dict[str, Any]],
    *,
    max_cards: int,
    selection: str,
) -> tuple[list[dict[str, Any]], str]:
    """Pick up to max_cards rows. round_robin balances category when 2+ axes present."""
    valid = [r for r in rows if str(r.get("canonical_text") or "").strip()]
    if not valid:
        return [], selection

    if selection == "recent":
        ordered = sorted(valid, key=_row_sort_key, reverse=True)
        return ordered[:max_cards], "recent"

    by_cat: dict[str, list[dict[str, Any]]] = {}
    for row in valid:
        cat, _ = _category_from_source_id(str(row.get("source_id") or ""))
        key = cat or "other"
        by_cat.setdefault(key, []).append(row)
    for pool in by_cat.values():
        pool.sort(key=_row_sort_key, reverse=True)

    if len(by_cat) <= 1:
        ordered = sorted(valid, key=_row_sort_key, reverse=True)
        return ordered[:max_cards], "recent_single_category"

    order = [c for c in ("world", "finance", "other") if c in by_cat]
    order.extend(k for k in sorted(by_cat) if k not in order)
    picked: list[dict[str, Any]] = []
    indices = dict.fromkeys(order, 0)
    while len(picked) < max_cards:
        advanced = False
        for cat in order:
            if len(picked) >= max_cards:
                break
            idx = indices[cat]
            pool = by_cat[cat]
            if idx < len(pool):
                picked.append(pool[idx])
                indices[cat] = idx + 1
                advanced = True
        if not advanced:
            break
    return picked, "round_robin_by_category"


def _bench_metrics(bench_path: Path, phase1_path: Path) -> dict[str, Any]:
    bench = _load_json(bench_path)
    phase1 = _load_json(phase1_path)
    snap = bench.get("metrics") if isinstance(bench.get("metrics"), dict) else bench
    p1 = phase1.get("bench_snapshot") if isinstance(phase1.get("bench_snapshot"), dict) else {}
    saving = snap.get("token_saving_ratio")
    if saving is None:
        saving = p1.get("token_saving_ratio")
    jaccard = snap.get("jaccard_fidelity_proxy")
    if jaccard is None:
        jaccard = p1.get("jaccard_fidelity_proxy")
    return {
        "bench_json": _rel(bench_path) if bench_path.is_file() else None,
        "phase1_json": _rel(phase1_path) if phase1_path.is_file() else None,
        "token_saving_ratio": saving,
        "jaccard_fidelity_proxy": jaccard,
        "measurement_status": str(
            bench.get("measurement_status") or p1.get("measurement_status") or "offline_cohort"
        ),
    }


def build_deck(
    rows: list[dict[str, Any]],
    *,
    max_cards: int,
    jaccard_floor: float,
    bench_metrics: dict[str, Any],
    lang: str,
    selection: str = "round_robin",
) -> dict[str, Any]:
    selected_rows, selection_mode = _select_rows_for_deck(
        rows, max_cards=max_cards, selection=selection
    )
    cards: list[dict[str, Any]] = []
    for row in selected_rows:
        canonical = str(row.get("canonical_text") or "").strip()
        if not canonical:
            continue
        obs_id = str(row.get("observation_id") or "")
        headline = _headline(canonical)
        source_id = row.get("source_id")
        sid_str = str(source_id) if source_id else None
        display_ko, headline_original = _headline_display_ko(headline, sid_str)
        prefill = _ask_prefill(lang)
        category, category_label_ko = _category_from_source_id(sid_str)
        card_id = hashlib.sha256(f"{obs_id}:{headline}".encode("utf-8")).hexdigest()[:12]
        card: dict[str, Any] = {
            "card_id": card_id,
            "observation_id": obs_id,
            "headline_display_ko": display_ko,
            "headline_ko": display_ko,
            "compressed_summary": _summary_display_ko(canonical, headline_original),
            "content_lang": _content_lang(headline),
            "source_label_ko": _source_label_ko(sid_str),
            "as_of_utc": row.get("as_of_utc"),
            "source_id": source_id,
            "source_record_url": row.get("source_record_url"),
            "hypothesis_tag": row.get("hypothesis_tag") or "[HYPO]",
            "ask_one_prefill_ko": prefill,
            "oracle_sphere_href": f"/oracle-sphere?context={obs_id}",
            "ask_one_href": f"/ask-one?prefill={_url_quote(prefill)}",
        }
        if headline_original:
            card["headline_original"] = headline_original
        if category:
            card["category"] = category
        if category_label_ko:
            card["category_label_ko"] = category_label_ko
        cards.append(card)

    jaccard = bench_metrics.get("jaccard_fidelity_proxy")
    deck_status = "WATCH"
    hold_reason: str | None = None
    if isinstance(jaccard, (int, float)) and float(jaccard) < jaccard_floor:
        deck_status = "HOLD"
        hold_reason = f"jaccard_fidelity_proxy {float(jaccard):.4f} < floor {jaccard_floor}"

    return {
        "schema": "mkmlife_news_observation_deck_v1",
        "generated_at_utc": _utc_now(),
        "lane": "research_only",
        "hypothesis_tag": "[HYPO]",
        "deck_status": deck_status,
        "hold_reason": hold_reason,
        "disclaimer_ko": (
            "B-track 관측 덱입니다. 투자·실매매·의료 판단 근거가 아니며, "
            "성경(Logos) 렌즈는 [NON_GATING] 보조 해설입니다."
        ),
        "disclaimer_en": (
            "B-track observation deck only. Not for trading, medical, or investment decisions. "
            "Logos lens is [NON_GATING] auxiliary context."
        ),
        "quality_gate": {
            "jaccard_fidelity_proxy_floor": jaccard_floor,
            "token_saving_ratio": bench_metrics.get("token_saving_ratio"),
            "jaccard_fidelity_proxy": jaccard,
            "measurement_status": bench_metrics.get("measurement_status"),
            "note": "Offline NEWS-RT cohort — not live breaking-news stream.",
        },
        "deck_selection": {
            "mode": selection_mode,
            "max_cards": max_cards,
            "cohort_row_count": len(rows),
        },
        "cards": cards,
        "refs": {
            "news_jsonl": _rel(DEFAULT_NEWS_JSONL),
            "news_rt_bench": bench_metrics.get("bench_json"),
            "phase1_status": bench_metrics.get("phase1_json"),
            "blueprint": "docs/research/saving_the_news_blueprint_v1.md",
        },
    }


def _url_quote(text: str) -> str:
    from urllib.parse import quote

    return quote(text, safe="")


def main() -> int:
    ap = argparse.ArgumentParser(description="news_observation_v1 -> mkmlife Observation Deck JSON")
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS_JSONL)
    ap.add_argument("--bench-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--phase1-json", type=Path, default=DEFAULT_PHASE1)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-cards", type=int, default=5)
    ap.add_argument("--jaccard-floor", type=float, default=JACCARD_FLOOR_DEFAULT)
    ap.add_argument("--lang", choices=("ko", "en"), default="ko")
    ap.add_argument(
        "--deck-selection",
        choices=("round_robin", "recent"),
        default="round_robin",
        help="round_robin: balance category on deck; recent: newest N only.",
    )
    ap.add_argument("--copy-mkmlife-public", action="store_true")
    args = ap.parse_args()

    news_path = args.news_jsonl.resolve()
    rows = _load_jsonl(news_path)
    if not rows:
        raise SystemExit(f"no news_observation rows: {news_path}")

    metrics = _bench_metrics(args.bench_json.resolve(), args.phase1_json.resolve())
    deck = build_deck(
        rows,
        max_cards=max(1, args.max_cards),
        jaccard_floor=float(args.jaccard_floor),
        bench_metrics=metrics,
        lang=args.lang,
        selection=args.deck_selection,
    )

    out_path = args.output_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": _rel(out_path), "cards": len(deck["cards"]), "deck_status": deck["deck_status"]}, ensure_ascii=False))

    if args.copy_mkmlife_public:
        MKMLIFE_PUBLIC.mkdir(parents=True, exist_ok=True)
        dest = MKMLIFE_PUBLIC / "mkmlife_news_observation_deck_v1.json"
        dest.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {_rel(dest)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
