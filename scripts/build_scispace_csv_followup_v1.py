#!/usr/bin/env python3
"""Follow-up on SciSpace CSV ingest: top10 pyobyeong, SCAT bench, trading dedup, ARC pointer."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs/research/raw/scispace_exports_2026-06-24"
OUT_PYO = ROOT / "docs/research/raw/SASANG_PYOBYEONG_TOP10_NL_PROXY_2026-06-24.md"
OUT_SCAT = ROOT / "reports/constitution/btrack_pilot/sasang_scat_voice_face_bench_v1.json"
OUT_TRADE = ROOT / "reports/constitution/btrack_pilot/trading_rl_llm_scispace_dedup_v1.json"
OUT_ARC = ROOT / "reports/constitution/btrack_pilot/arc_architects_ttt_lora_pointer_v1.json"
OUT_MANIFEST = ROOT / "reports/constitution/btrack_pilot/scispace_csv_followup_manifest_v1.json"

NOTEBOOK_UUID = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"

# Scoring keywords for pyobyeong relevance
PYO_KEYWORDS = [
    ("pyobyeong", 8),
    ("constitutional symptom", 8),
    ("표리", 6),
    ("표리병증", 8),
    ("discourse on the constitutional", 10),
    ("dongyi suse bowon", 7),
    ("donguisusebowon", 7),
    ("동의수세보원", 7),
    ("sasangin", 4),
    ("taeeumin", 3),
    ("soyangin", 3),
    ("soeumin", 3),
    ("taeyangin", 3),
    ("mangeum", 3),
    ("표증", 5),
    ("병증", 4),
]

SCAT_KEYWORDS = ["scat", "sasang constitutional analysis tool", "concordance", "agreement", "일치"]
VOICE_FACE_SKIP = ["alzheimer", "parkinson", "dementia", "covid", "depression disorder"]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_csv(name: str) -> list[dict[str, str]]:
    with (RAW / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip().lower())


def score_pyobyeong(row: dict[str, str]) -> int:
    blob = " ".join(
        str(row.get(k, "") or "") for k in ("title", "Insights", "Conclusions", "Results", "Contributions")
    ).lower()
    score = 0
    for kw, w in PYO_KEYWORDS:
        if kw in blob or kw in row.get("title", "").lower():
            score += w
    return score


def build_pyobyeong_top10() -> list[dict]:
    rows = _read_csv("sasang_pyobyeong_historical_76.csv")
    ranked = sorted(rows, key=score_pyobyeong, reverse=True)
    top = ranked[:10]
    out: list[dict] = []
    for i, r in enumerate(top, 1):
        out.append(
            {
                "rank": i,
                "score": score_pyobyeong(r),
                "title": r.get("title", "").strip(),
                "authors": r.get("authors", "").strip(),
                "insights": (r.get("Insights") or "")[:500],
                "conclusions": (r.get("Conclusions") or "")[:500],
            }
        )
    return out


def write_pyobyeong_proxy(top10: list[dict]) -> None:
    lines = [
        "# [PAPER_PROXY] 사상체질 표리병증 — SciSpace Top 10 (B-track)",
        "",
        f"**Generated:** {_utc()}  ",
        "**Track:** B · `[PAPER_PROXY]` · `send_gate: HOLD`  ",
        "**Rule:** Secondary summaries only — not `[CANON]` · not clinical diagnosis.",
        "",
        "---",
        "",
    ]
    for item in top10:
        lines.extend(
            [
                f"## {item['rank']}. {item['title']}",
                "",
                f"- **Authors:** {item['authors'] or 'n/a'}",
                f"- **Relevance score:** {item['score']}",
                "",
                "### Insights (excerpt)",
                item["insights"] or "_none_",
                "",
                "### Conclusions (excerpt)",
                item["conclusions"] or "_none_",
                "",
                "---",
                "",
            ]
        )
    OUT_PYO.write_text("\n".join(lines), encoding="utf-8")


def extract_accuracy(text: str) -> list[str]:
    if not text:
        return []
    hits = re.findall(r"\d+(?:\.\d+)?\s*%", text)
    return hits[:6]


def build_scat_bench() -> dict:
    rows = _read_csv("sasang_voice_face_constitution_66.csv")
    entries: list[dict] = []
    for r in rows:
        title = r.get("title", "")
        tl = title.lower()
        if any(x in tl for x in VOICE_FACE_SKIP):
            continue
        blob = " ".join(
            str(r.get(k, "") or "") for k in ("title", "Results", "Limitations", "Methods Used")
        ).lower()
        if not any(k in blob or k in tl for k in SCAT_KEYWORDS + ["voice", "facial", "face", "sasang constitution"]):
            continue
        results = r.get("Results") or ""
        limitations = r.get("Limitations") or ""
        acc = extract_accuracy(results)
        entries.append(
            {
                "title": title.strip(),
                "authors": (r.get("authors") or "").strip()[:120],
                "accuracy_pct_snippets": acc,
                "results_excerpt": results[:400].replace("\n", " "),
                "limitations_excerpt": limitations[:300].replace("\n", " "),
                "modality": "SCAT" if "scat" in blob else ("voice" if "voice" in blob else "face"),
            }
        )
    # sort: SCAT first, then most accuracy snippets
    entries.sort(key=lambda e: (0 if e["modality"] == "SCAT" else 1, -len(e["accuracy_pct_snippets"])))
    return {
        "schema": "sasang_scat_voice_face_bench_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "source_csv": "sasang_voice_face_constitution_66.csv",
        "row_count_filtered": len(entries),
        "headline": {
            "scat_expert_agreement_note": "SCAT vs expert: ~65.9% male / ~59.4% female (top SCAT paper in export)",
            "caveat": "SciSpace Results column — verify primary paper before Track A or clinical copy",
        },
        "entries": entries[:20],
        "reproduce": "py scripts/build_scispace_csv_followup_v1.py",
    }


def build_trading_dedup() -> dict:
    intra = _read_csv("trading_rl_llm_sentiment_160.csv")
    eq = _read_csv("trading_equities_ml_20.csv")
    titles_intra = {_norm_title(r["title"]) for r in intra if r.get("title")}
    titles_eq = {_norm_title(r["title"]) for r in eq if r.get("title")}

    # Existing MS B-track anchors in repo (paper titles / project names)
    existing_norm = {
        _norm_title("Language Model Guided Reinforcement Learning in Quantitative Trading"),
        _norm_title("FinRL-DeepSeek: LLM-Infused Risk-Sensitive Reinforcement Learning for Trading Agents"),
        _norm_title("pre_news_shadow"),
        _norm_title("swarm sentiment b-track"),
    }
    # Also scan docs for known citations
    for p in [
        ROOT / "docs/final/SCISPACE_SASANG_LITERATURE_HELPFUL_ITEMS_2026-03-29.md",
    ]:
        if p.is_file():
            for m in re.finditer(r"10\.\d{4,}/[^\s`]+", p.read_text(encoding="utf-8", errors="replace")):
                existing_norm.add(m.group(0).lower())

    def classify(rows: list[dict], bundle: str) -> list[dict]:
        out = []
        for r in rows:
            t = r.get("title", "").strip()
            tn = _norm_title(t)
            tags = []
            blob = (r.get("TL;DR") or "") + (r.get("Insights") or "") + (r.get("Methods Used") or "")
            bl = blob.lower()
            if "llm" in bl or "language model" in bl:
                tags.append("llm")
            if "reinforcement" in bl or "deep reinforcement" in bl:
                tags.append("rl")
            if "sentiment" in bl or "news" in bl:
                tags.append("sentiment")
            if "intraday" in bl or "intraday" in tn:
                tags.append("intraday")
            if "sharpe" in bl:
                tags.append("sharpe")
            if "crypto" in bl or "bitcoin" in bl:
                tags.append("crypto")
            out.append(
                {
                    "title": t,
                    "bundle": bundle,
                    "tags": tags,
                    "in_equities_subset": tn in titles_eq,
                    "already_in_repo_anchor": tn in existing_norm,
                    "queue_priority": (
                        "high"
                        if ("llm" in tags and "rl" in tags) and ("sentiment" in tags or "news" in tags)
                        else "medium"
                        if "rl" in tags
                        else "low"
                    ),
                }
            )
        return out

    classified = classify(intra, "trading_rl_llm_sentiment_160")
    high = [c for c in classified if c["queue_priority"] == "high" and not c["already_in_repo_anchor"]]
    high.sort(key=lambda x: len(x["tags"]), reverse=True)

    return {
        "schema": "trading_rl_llm_scispace_dedup_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "research_only": True,
        "counts": {
            "intraday_unique": len(titles_intra),
            "equities_unique": len(titles_eq),
            "overlap": len(titles_intra & titles_eq),
            "high_priority_new": len(high[:30]),
        },
        "overlap_titles": sorted(titles_intra & titles_eq)[:15],
        "queue_candidates_high": high[:25],
        "note": "No auto-ingest to live trading; cross-ref pre_news_shadow / atproto sentiment separately",
        "reproduce": "py scripts/build_scispace_csv_followup_v1.py",
    }


def build_arc_pointer() -> dict:
    arc_rows = _read_csv("arc_prize_ttt_lora_20.csv")
    return {
        "schema": "arc_architects_ttt_lora_pointer_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "mkm_cross_ref": "mkm_control_integrity golden/LoRA eval — pattern reference only",
        "primary_repo": "https://github.com/da-fr/arc-prize-2024",
        "paper_pdf": "https://da-fr.github.io/arc-prize-2024/the_architects.pdf",
        "hf_model": "https://huggingface.co/da-fr/Mistral-NeMo-Minitron-8B-ARChitects-Full-bnb-4bit",
        "entry_scripts": [
            "training_code/run_finetune_Nemo-full.py",
            "training_code/run_evaluation_Nemo-full.py",
        ],
        "techniques": ["test-time training", "LoRA rank 256/64", "4-bit quantization", "unsloth"],
        "scispace_export_titles": [r.get("title", "") for r in arc_rows[:5]],
        "reproduce": "py scripts/build_scispace_csv_followup_v1.py",
    }


def main() -> int:
    top10 = build_pyobyeong_top10()
    write_pyobyeong_proxy(top10)

    scat_doc = build_scat_bench()
    OUT_SCAT.parent.mkdir(parents=True, exist_ok=True)
    OUT_SCAT.write_text(json.dumps(scat_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    trade_doc = build_trading_dedup()
    OUT_TRADE.write_text(json.dumps(trade_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    arc_doc = build_arc_pointer()
    OUT_ARC.write_text(json.dumps(arc_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "scispace_csv_followup_manifest_v1",
        "generated_at_utc": _utc(),
        "artifacts": {
            "pyobyeong_nl_proxy": str(OUT_PYO.relative_to(ROOT)).replace("\\", "/"),
            "scat_bench": str(OUT_SCAT.relative_to(ROOT)).replace("\\", "/"),
            "trading_dedup": str(OUT_TRADE.relative_to(ROOT)).replace("\\", "/"),
            "arc_pointer": str(OUT_ARC.relative_to(ROOT)).replace("\\", "/"),
        },
        "pyobyeong_top10_titles": [x["title"] for x in top10],
        "nl_notebook_uuid": NOTEBOOK_UUID,
        "nl_upload": "pending — run nlm source add or MCP add_source",
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(OUT_MANIFEST)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
