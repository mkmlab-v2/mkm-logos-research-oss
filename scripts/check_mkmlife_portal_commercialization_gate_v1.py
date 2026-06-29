#!/usr/bin/env python3
"""mkmlife.com portal commercialization gate v1 — offline SSOT checks.

B-track observation facade only; does not assert Track A compression quality or live trading GO.
Writes reports/mkmlife_portal_commercialization_gate_v1_latest.json (exit 0 = pass).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOT_RESOLVED = ROOT.resolve()


def _rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_RESOLVED)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


from mkm_consumer_facade_v1 import (  # noqa: E402
    CONSUMER_FORBIDDEN_DECK_SURFACE_STRINGS,
    CONSUMER_FORBIDDEN_SURFACE_STRINGS,
    PUBLIC_UI_KO,
    TRACK_A_FORBIDDEN_SURFACE_NUMBERS,
    TRADING_FORBIDDEN_SURFACE_PHRASES,
)

DEFAULT_DECK = ROOT / "projects/mkm/mkm-life/public/data/mkmlife_news_observation_deck_v1.json"
DEFAULT_VOCAB = ROOT / "projects/mkm/mkm-life/lib/mkmlife-consumer-vocabulary-v1.ts"
DEFAULT_HOME_PAGE = ROOT / "projects/mkm/mkm-life/app/page.tsx"
DEFAULT_SITE_FOOTER = ROOT / "projects/mkm/mkm-life/components/SiteFooter.tsx"
DEFAULT_SITE_HEADER = ROOT / "projects/mkm/mkm-life/components/SiteHeader.tsx"
DEFAULT_FAMILY_LINKS = ROOT / "projects/mkm/mkm-life/lib/mkmlife-family-links-v1.ts"
DEFAULT_SKIM_TS = ROOT / "projects/mkm/mkm-life/lib/mkmlife-skim-read-v1.ts"
DEFAULT_OUT = ROOT / "reports/mkmlife_portal_commercialization_gate_v1_latest.json"

REQUIRED_SKIM_MARKERS = (
    "MKMLIFE_SKIM_READ_STORAGE_KEY",
    "mkmlife_skim_read_v1",
    "resolveSkimViewMode",
)
REQUIRED_UI_FILES = (
    ROOT / "projects/mkm/mkm-life/components/news-deck/SkimReadToggle.tsx",
    ROOT / "projects/mkm/mkm-life/components/news-deck/ObservationDeckCard.tsx",
    ROOT / "projects/mkm/mkm-life/components/home/HomeLifePortal.tsx",
    ROOT / "projects/mkm/mkm-life/components/news-deck/NewsObservationDeck.tsx",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _find_hits(text: str, needles: frozenset[str] | set[str]) -> list[str]:
    return sorted({n for n in needles if n in text})


def _scan_deck(deck_path: Path) -> dict[str, Any]:
    doc = json.loads(deck_path.read_text(encoding="utf-8"))
    issues: list[str] = []
    if doc.get("schema") != "mkmlife_news_observation_deck_v1":
        issues.append(f"schema={doc.get('schema')!r}")
    if doc.get("hypothesis_tag") != "[HYPO]":
        issues.append(f"hypothesis_tag={doc.get('hypothesis_tag')!r}")
    pub = doc.get("public_ui") or {}
    for key, expected in PUBLIC_UI_KO.items():
        if pub.get(key) != expected:
            issues.append(f"public_ui.{key} drift")
    cards = doc.get("cards") or []
    card_hits: list[dict[str, Any]] = []
    for card in cards:
        blob = json.dumps(card, ensure_ascii=False)
        forbidden = _find_hits(blob, CONSUMER_FORBIDDEN_SURFACE_STRINGS | CONSUMER_FORBIDDEN_DECK_SURFACE_STRINGS)
        track_a = _find_hits(blob, TRACK_A_FORBIDDEN_SURFACE_NUMBERS)
        trading = _find_hits(blob, TRADING_FORBIDDEN_SURFACE_PHRASES)
        if forbidden or track_a or trading:
            card_hits.append(
                {
                    "card_id": card.get("card_id"),
                    "forbidden": forbidden,
                    "track_a": track_a,
                    "trading": trading,
                }
            )
    if not cards:
        issues.append("cards empty")
    return {
        "path": _rel_path(deck_path),
        "card_count": len(cards),
        "generated_at_utc": doc.get("generated_at_utc"),
        "deck_status": doc.get("deck_status"),
        "public_ui_ok": not any(x.startswith("public_ui.") for x in issues),
        "issues": issues,
        "card_forbidden_hits": card_hits,
        "ok": not issues and not card_hits,
    }


def _scan_text_file(path: Path, *, extra_forbidden: frozenset[str] | None = None) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    needles = set(CONSUMER_FORBIDDEN_SURFACE_STRINGS)
    if extra_forbidden:
        needles |= set(extra_forbidden)
    hits = _find_hits(text, frozenset(needles))
    track_a = _find_hits(text, TRACK_A_FORBIDDEN_SURFACE_NUMBERS)
    trading = _find_hits(text, TRADING_FORBIDDEN_SURFACE_PHRASES)
    # page.tsx folded tail may mention compression in enterprise context — flag only Track A frozen KPI pair
    return {
        "path": _rel_path(path),
        "forbidden_hits": hits,
        "track_a_hits": track_a,
        "trading_hits": trading,
        "ok": not hits and not track_a and not trading,
    }


def _scan_skim_module(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    missing = [m for m in REQUIRED_SKIM_MARKERS if m not in text]
    return {
        "path": _rel_path(path),
        "missing_markers": missing,
        "ok": not missing,
    }


def _scan_ui_wiring() -> dict[str, Any]:
    missing = [_rel_path(p) for p in REQUIRED_UI_FILES if not p.is_file()]
    return {"missing_files": missing, "ok": not missing}


def _scan_site_footer_ops_gate(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    if "shouldShowMkmlifeOpsTail" not in text:
        issues.append("missing shouldShowMkmlifeOpsTail import/guard")
    if "showOpsNav" not in text:
        issues.append("missing showOpsNav conditional")
    if "/intelligence-dashboard" not in text:
        issues.append("missing intelligence-dashboard route (ops-only expected)")
    if re.search(
        r"<Link href=\{withLang\('/intelligence-dashboard'\)\}>\{t\.dashboard\}</Link>",
        text,
    ) and "showOpsNav" not in text:
        issues.append("unconditional intelligence-dashboard link")
    return {"path": _rel_path(path), "issues": issues, "ok": not issues}


def _scan_site_header_en_ia(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    if "News deck" in text:
        issues.append("EN menu still uses News deck")
    if "Observation deck" not in text:
        issues.append("missing Observation deck EN label")
    return {"path": _rel_path(path), "issues": issues, "ok": not issues}


def _scan_family_links_alignment(path: Path, home_page_path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    home = home_page_path.read_text(encoding="utf-8")
    issues: list[str] = []
    if "jema12.com" in text.lower() or "JEMA12" in text:
        issues.append("legacy JEMA12 in family links SSOT")
    for required in ("https://jema-ai.com", "https://jemaai.cloud"):
        if required not in text:
            issues.append(f"missing {required}")
    if "MKMLIFE_FAMILY_LINKS_V1" not in home:
        issues.append("home page not wired to MKMLIFE_FAMILY_LINKS_V1")
    if "jema12.com" in home.lower():
        issues.append("home page still references jema12.com")
    return {"path": _rel_path(path), "issues": issues, "ok": not issues}


def _scan_vocab_sync(vocab_path: Path) -> dict[str, Any]:
    text = vocab_path.read_text(encoding="utf-8")
    guard_path = vocab_path.parent / "mkmlife-consumer-guard-v1.server.ts"
    guard_text = guard_path.read_text(encoding="utf-8") if guard_path.is_file() else ""
    issues: list[str] = []
    if "NEWS_DECK_PUBLIC_UI" not in text:
        issues.append("NEWS_DECK_PUBLIC_UI missing")
    if "CONSUMER_FORBIDDEN_DECK_SURFACE_STRINGS" not in text:
        issues.append("CONSUMER_FORBIDDEN_DECK_SURFACE_STRINGS missing")
    if "태음인" not in guard_text:
        issues.append("guard.server.ts missing sasang forbidden guard")
    lead = PUBLIC_UI_KO["lead"]
    if lead not in text:
        issues.append("PUBLIC_UI lead not mirrored in TS")
    return {
        "path": _rel_path(vocab_path),
        "guard_path": _rel_path(guard_path) if guard_path.is_file() else None,
        "issues": issues,
        "ok": not issues,
    }


def run_gate(
    *,
    deck_path: Path,
    vocab_path: Path,
    home_page_path: Path,
    site_footer_path: Path,
    site_header_path: Path,
    family_links_path: Path,
    skim_ts_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    deck_path = deck_path.resolve()
    vocab_path = vocab_path.resolve()
    home_page_path = home_page_path.resolve()
    site_footer_path = site_footer_path.resolve()
    site_header_path = site_header_path.resolve()
    family_links_path = family_links_path.resolve()
    skim_ts_path = skim_ts_path.resolve()
    out_path = out_path.resolve()
    checks = {
        "deck_json": _scan_deck(deck_path),
        "consumer_vocabulary_ts": _scan_vocab_sync(vocab_path),
        "skim_read_module": _scan_skim_module(skim_ts_path),
        "ui_wiring": _scan_ui_wiring(),
        "home_page_copy": _scan_text_file(home_page_path),
        "site_footer_ops_gate": _scan_site_footer_ops_gate(site_footer_path),
        "site_header_en_ia": _scan_site_header_en_ia(site_header_path),
        "family_links_alignment": _scan_family_links_alignment(family_links_path, home_page_path),
    }
    failed = [name for name, row in checks.items() if not row.get("ok")]
    report = {
        "schema": "mkmlife_portal_commercialization_gate_v1",
        "generated_at_utc": _utc_now(),
        "lane": "research_only",
        "hypothesis_tag": "[HYPO]",
        "track_wall": "B-track UI facade — not Track A commercialization or live trading GO",
        "overall_ok": len(failed) == 0,
        "failed_checks": failed,
        "checks": checks,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="mkmlife portal commercialization gate (offline)")
    ap.add_argument("--deck-json", type=Path, default=DEFAULT_DECK)
    ap.add_argument("--vocab-ts", type=Path, default=DEFAULT_VOCAB)
    ap.add_argument("--home-page", type=Path, default=DEFAULT_HOME_PAGE)
    ap.add_argument("--site-footer", type=Path, default=DEFAULT_SITE_FOOTER)
    ap.add_argument("--site-header", type=Path, default=DEFAULT_SITE_HEADER)
    ap.add_argument("--family-links-ts", type=Path, default=DEFAULT_FAMILY_LINKS)
    ap.add_argument("--skim-ts", type=Path, default=DEFAULT_SKIM_TS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    report = run_gate(
        deck_path=args.deck_json,
        vocab_path=args.vocab_ts,
        home_page_path=args.home_page,
        site_footer_path=args.site_footer,
        site_header_path=args.site_header,
        family_links_path=args.family_links_ts,
        skim_ts_path=args.skim_ts,
        out_path=args.out_json,
    )
    print(json.dumps({"overall_ok": report["overall_ok"], "failed_checks": report["failed_checks"]}, ensure_ascii=False))
    return 0 if report["overall_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
