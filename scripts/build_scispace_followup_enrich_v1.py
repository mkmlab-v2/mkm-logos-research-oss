#!/usr/bin/env python3
"""Phase-2 enrich: SCAT top-3 bibliographic links + pre_news_shadow literature queue."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_SCAT = ROOT / "reports/constitution/btrack_pilot/sasang_scat_voice_face_bench_v1.json"
OUT_PRE_NEWS = (
    ROOT / "reports/constitution/btrack_pilot/pre_news_shadow_scispace_literature_review_v1.json"
)
OUT_MANIFEST = ROOT / "reports/constitution/btrack_pilot/scispace_followup_enrich_manifest_v1.json"

# Curated bibliographic anchors (web/KCI lookup 2026-06-24) — research_only
SCAT_TOP3_LINKS: dict[str, dict[str, str]] = {
    "Comparison between Diagnostic Results of the Sasang Constitutional Analysis Tool (SCAT) and a Sasang Constitution Expert": {
        "doi": "10.7730/JSCM.2013.25.3.158",
        "doi_url": "https://doi.org/10.7730/JSCM.2013.25.3.158",
        "kci_url": "https://koreascience.or.kr/article/JAKO201330251817812.page",
        "venue": "J Sasang Constitut Med 2013;25(3):158-166",
    },
    "Development of an integrated Sasang constitution diagnosis method using face, body shape, voice, and questionnaire information": {
        "doi": "10.1186/1472-6882-12-85",
        "doi_url": "https://doi.org/10.1186/1472-6882-12-85",
        "kci_url": "",
        "venue": "BMC Complement Altern Med 2012;12:85",
        "pmc_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3473991/",
    },
    "The Concordance and Validity Assessment of Diagnosis for the Expert in Sasang Constitution": {
        "doi": "10.7730/JSCM.2014.26.3.295",
        "doi_url": "https://doi.org/10.7730/JSCM.2014.26.3.295",
        "kci_url": "https://journal.kci.go.kr/JSCIM/archive/articlePdf?artiId=ART001917072",
        "venue": "J Sasang Constitut Med 2014;26(3):295-303",
    },
}

PRE_NEWS_TOP5 = [
    {
        "rank": 1,
        "title": "Trend-Heuristic Reinforcement Learning Framework for News-Oriented Stock Portfolio Management",
        "authors": "Wei Ding et al.",
        "doi": "10.1109/ICASSP48485.2024.10447993",
        "doi_url": "https://doi.org/10.1109/ICASSP48485.2024.10447993",
        "venue": "IEEE ICASSP 2024",
        "pre_news_relevance": "news sentiment + trend heuristics for portfolio RL",
        "source_bundle": "trading_rl_llm_sentiment_160",
    },
    {
        "rank": 2,
        "title": "Financial News-Driven LLM Reinforcement Learning for Portfolio Management",
        "authors": "arxiv 2411.11059",
        "doi": "10.48550/arXiv.2411.11059",
        "doi_url": "https://doi.org/10.48550/arXiv.2411.11059",
        "arxiv_url": "https://arxiv.org/abs/2411.11059",
        "venue": "arXiv preprint Nov 2024",
        "pre_news_relevance": "LLM sentiment from news into RL portfolio trading",
        "source_bundle": "trading_rl_llm_sentiment_160 (overlap)",
    },
    {
        "rank": 3,
        "title": "Language Model Guided Reinforcement Learning in Quantitative Trading",
        "authors": "Darmanin et al.",
        "doi": "10.48550/arXiv.2508.02366",
        "doi_url": "https://doi.org/10.48550/arXiv.2508.02366",
        "arxiv_url": "https://arxiv.org/abs/2508.02366",
        "venue": "arXiv preprint Aug 2025",
        "pre_news_relevance": "LLM strategy guidance for intraday RL (SR/MDD eval)",
        "source_bundle": "trading_rl_llm_sentiment_160",
    },
    {
        "rank": 4,
        "title": "FinRL-DeepSeek: LLM-Infused Risk-Sensitive Reinforcement Learning for Trading Agents",
        "authors": "Mostapha Benhenda",
        "doi": "10.48550/arXiv.2502.07393",
        "doi_url": "https://doi.org/10.48550/arXiv.2502.07393",
        "arxiv_url": "https://arxiv.org/abs/2502.07393",
        "repo_url": "https://github.com/benstaf/FinRL_DeepSeek",
        "venue": "arXiv preprint Feb 2025",
        "pre_news_relevance": "FNSPID news → LLM risk signals + CPPO Nasdaq-100",
        "source_bundle": "trading_rl_llm_sentiment_160",
    },
    {
        "rank": 5,
        "title": "How Sentiment Indicators Improve Algorithmic Trading Performance",
        "authors": "Gómez-Martínez et al.",
        "doi": "10.1177/21582440251369559",
        "doi_url": "https://doi.org/10.1177/21582440251369559",
        "venue": "SAGE Open 2025;15(3)",
        "pre_news_relevance": "CNN Fear & Greed + crypto sentiment for Nasdaq Mini futures",
        "source_bundle": "trading_rl_llm_sentiment_160",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_title_key(t: str) -> str:
    return t.strip().rstrip(".")


def _title_match(entry_title: str, canon_title: str) -> bool:
    a = _norm_title_key(entry_title).lower()
    b = _norm_title_key(canon_title).lower()
    if a == b or a.startswith(b[:50]) or b.startswith(a[:50]):
        return True
    # Truncated SciSpace export titles
    needles = (
        "scat) and a sasang constitution expert",
        "integrated sasang constitution diagnosis method",
        "concordance and validity assessment of diagnosis for the expert",
    )
    return any(n in a for n in needles) and any(n in b for n in needles) or (
        "concordance and validity" in a and "expert" in a and "sasang constitution" in a
    )


def enrich_scat_bench(doc: dict) -> tuple[dict, int]:
    patched = 0
    seen_keys: set[str] = set()
    for entry in doc.get("entries", []):
        title = entry.get("title", "")
        for key, links in SCAT_TOP3_LINKS.items():
            if key in seen_keys:
                continue
            if _title_match(title, key):
                entry["bibliographic"] = {**links, "verified_at_utc": _utc(), "source": "web_kci_lookup"}
                seen_keys.add(key)
                patched += 1
                break
    doc["top3_bibliographic_enriched_at_utc"] = _utc()
    return doc, patched


def build_pre_news_review() -> dict:
    return {
        "schema": "pre_news_shadow_scispace_literature_review_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "research_only": True,
        "purpose": "Monthly pre_news_shadow literature pointer queue from SciSpace CSV dedup (news/LLM/RL)",
        "upstream": "reports/constitution/btrack_pilot/trading_rl_llm_scispace_dedup_v1.json",
        "selection_criteria": "news-oriented + LLM sentiment + RL; not Track A promotion",
        "papers": PRE_NEWS_TOP5,
        "reproduce": "py scripts/build_scispace_followup_enrich_v1.py",
    }


def main() -> int:
    if not OUT_SCAT.is_file():
        raise SystemExit(f"missing SCAT bench: {OUT_SCAT}")

    scat_doc = json.loads(OUT_SCAT.read_text(encoding="utf-8"))
    scat_doc, patched = enrich_scat_bench(scat_doc)
    OUT_SCAT.write_text(json.dumps(scat_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pre_news = build_pre_news_review()
    OUT_PRE_NEWS.parent.mkdir(parents=True, exist_ok=True)
    OUT_PRE_NEWS.write_text(json.dumps(pre_news, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "scispace_followup_enrich_manifest_v1",
        "generated_at_utc": _utc(),
        "scat_entries_patched": patched,
        "artifacts": {
            "scat_bench": str(OUT_SCAT.relative_to(ROOT)).replace("\\", "/"),
            "pre_news_literature_review": str(OUT_PRE_NEWS.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "scat_patched": patched, "pre_news": str(OUT_PRE_NEWS)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
