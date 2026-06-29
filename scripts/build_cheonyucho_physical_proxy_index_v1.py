#!/usr/bin/env python3
"""Index CHEONYUCHO_PHYSICAL_* nl_proxy files and sync probe P1-01 state."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"
DEFAULT_PROBE = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json"
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_physical_proxy_index_v1_latest.json"
P101_ANCHOR_SLUG = "PARK1985_NLK_reply2_2026"
P101_BODY_SLUG_PREFIX = "PARK1985_NLK_BODY_"

PROXY_GLOB = "CHEONYUCHO_PHYSICAL_*_nl_proxy.md"
VALIDATION_RE = re.compile(r"## Validation\s*\n\s*```json\s*\n(.*?)\n```", re.DOTALL)
META_RE = {
    "call_no": re.compile(r"\*\*call_no:\*\*\s*(.+)", re.MULTILINE),
    "page": re.compile(r"\*\*page:\*\*\s*(.+)", re.MULTILINE),
    "transcript_sha256": re.compile(r"\*\*transcript_sha256:\*\*\s*`([^`]+)`"),
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_proxy(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    validation: dict = {}
    m = VALIDATION_RE.search(text)
    if m:
        try:
            validation = json.loads(m.group(1))
        except json.JSONDecodeError:
            validation = {"parse_error": True}
    meta: dict[str, str | None] = {}
    for key, rx in META_RE.items():
        hit = rx.search(text)
        val = hit.group(1).strip() if hit else None
        if val in ("—", "-", ""):
            val = None
        meta[key] = val
    slug = path.stem.replace("_nl_proxy", "").replace("CHEONYUCHO_PHYSICAL_", "")
    return {
        "slug": slug,
        "path": _rel(path),
        "paste_proxy_path": _rel(path),
        "transcript_sha256": meta.get("transcript_sha256"),
        "library_call_no": meta.get("call_no"),
        "page": meta.get("page"),
        "markers_found": validation.get("markers_found", []),
        "warnings": validation.get("warnings", []),
        "hanja_ratio": validation.get("hanja_ratio"),
        "accept_paste": validation.get("accept_paste"),
    }


def build_index() -> dict:
    proxies = sorted(RAW.glob(PROXY_GLOB))
    entries = [parse_proxy(p) for p in proxies]
    nlk_reply = [e for e in entries if "NLK_reply" in e["slug"]]
    p344 = next((e for e in entries if "SASANG_CLINICAL_P344" in e["slug"]), None)
    verdict = {
        "rear_index": "absent_nlk_confirmed",
        "원문db_fulltext_search": "not_supported_nlk_confirmed",
        "next_human_action": "협약도서관 PC CNTS-00047835836 본문·각주 수동 grep → bind --scan/--paste-file",
    }
    if p344:
        verdict["partial_p344_proxy"] = p344["path"]
        verdict["partial_p344_hanja_ratio"] = p344.get("hanja_ratio")
    return {
        "schema": "cheonyucho_physical_proxy_index_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "hanja_canon_status": "not_acquired",
        "proxy_count": len(entries),
        "nlk_park1985_call_no": "199.1-이617ㄱ",
        "p1_01_verdict": verdict,
        "proxies": entries,
        "nlk_reply_slugs": [e["slug"] for e in nlk_reply],
        "reproduce": "py scripts/build_cheonyucho_physical_proxy_index_v1.py",
    }


def p101_anchor_from_index(index: dict) -> dict | None:
    proxies = index.get("proxies") or []
    body = sorted(
        (p for p in proxies if str(p.get("slug", "")).startswith(P101_BODY_SLUG_PREFIX)),
        key=lambda p: p.get("slug", ""),
        reverse=True,
    )
    preferred = body[0] if body else None
    if preferred is None:
        preferred = next((p for p in proxies if p.get("slug") == P101_ANCHOR_SLUG), None)
    if preferred is None:
        preferred = next(
            (p for p in proxies if p.get("library_call_no") == "199.1-이617ㄱ" and "NLK" in p.get("slug", "")),
            None,
        )
    if preferred is None:
        return None
    return {
        k: preferred.get(k)
        for k in ("transcript_sha256", "library_call_no", "page", "paste_proxy_path")
        if preferred.get(k)
    }


def patch_probe(probe_path: Path, index: dict, *, index_out: Path) -> None:
    if not probe_path.is_file():
        return
    probe = json.loads(probe_path.read_text(encoding="utf-8-sig"))
    checklist = probe.get("checklist") or []
    for item in checklist:
        if item.get("id") != "P1-01":
            continue
        item["status"] = "nl_briefing_only"
        item["physical_proxy_index"] = _rel(index_out)
        item["note"] = (
            "NLK 1차: 후반 색인 없음; 2차: 원문DB 본문검색 불가 — "
            "협약도서관 수동 열람·페이지 캡처만"
        )
        item["next_action"] = index["p1_01_verdict"]["next_human_action"]
        break
    p101_anchor = p101_anchor_from_index(index)
    if p101_anchor:
        probe["physical_anchor"] = p101_anchor
        probe["last_run_physical"] = {
            "bound_at_utc": index.get("generated_at_utc"),
            "artifact": _rel(index_out),
            "p1_01_anchor_slug": P101_ANCHOR_SLUG,
            "transcript_validation_warnings": next(
                (p.get("warnings") for p in index.get("proxies", []) if p.get("slug") == P101_ANCHOR_SLUG),
                [],
            ),
        }
    probe["physical_proxy_index"] = _rel(index_out)
    probe["updated_at_utc"] = _utc()
    probe_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    ap.add_argument("--no-patch-probe", action="store_true")
    args = ap.parse_args()

    index = build_index()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.no_patch_probe:
        patch_probe(args.probe, index, index_out=args.out)

    print(
        json.dumps(
            {
                "ok": True,
                "proxy_count": index["proxy_count"],
                "out": _rel(args.out),
                "p1_01_status": "nl_briefing_only",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
