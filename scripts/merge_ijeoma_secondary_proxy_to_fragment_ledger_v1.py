#!/usr/bin/env python3
"""Merge IJEOMA_SECONDARY_PROXY_v1 fragments into CHEONYUCHO_FRAGMENT_LEDGER (idempotent)."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROXY = ROOT / "docs/research/raw/IJEOMA_SECONDARY_PROXY_v1.json"
LEDGER = ROOT / "docs/research/raw/CHEONYUCHO_FRAGMENT_LEDGER_v1.json"
OUT_REPORT = ROOT / "reports/constitution/btrack_pilot/ijeoma_secondary_proxy_merge_v1_latest.json"

HANJA_RE = re.compile(r"[\u4e00-\u9fff]+")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _longest_hanja_run(text: str) -> int:
    runs = HANJA_RE.findall(text or "")
    return max((len(r) for r in runs), default=0)


def _focus_for(topic: str, source_tier: str) -> str:
    if topic.startswith("dssbw_"):
        return "dssbw_workspace_canon"
    if topic.startswith("geukchigo"):
        return "geukchigo"
    if "cheonyucho" in topic:
        return "cheonyucho"
    if topic.startswith("lee") or topic.startswith("kim"):
        return "secondary_corpus"
    if "gate" in topic or "guard" in topic or "dispute" in topic:
        return "guard_meta"
    if source_tier.startswith("T0"):
        return "workspace_canon"
    return "secondary_corpus"


def _term_from(frag: dict[str, Any]) -> str:
    q = frag.get("quote_hanja") or frag.get("quote_ko") or ""
    for t in ("闡幽抄", "闡幽", "格致藁", "격치고", "太陽人", "物宅身", "意者"):
        if t in q:
            return t
    if "cheonyucho" in frag.get("topic", ""):
        return "闡幽抄"
    if "geukchigo" in frag.get("topic", ""):
        return "格致藁"
    return "secondary_proxy"


def _chunk_id(sp_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mkm:ijeoma-secondary-proxy:{sp_id}"))


def frag_to_chunk(frag: dict[str, Any]) -> dict[str, Any]:
    snippet = (frag.get("quote_hanja") or frag.get("quote_ko") or "").strip()
    path = frag.get("source_path")
    chunk: dict[str, Any] = {
        "chunk_id": _chunk_id(frag["id"]),
        "source_id": frag["id"],
        "pdf_path": path if path and str(path).endswith(".pdf") else "",
        "citation": frag.get("source_literature", ""),
        "focus": _focus_for(frag.get("topic", ""), frag.get("source_tier", "")),
        "term": _term_from(frag),
        "layer": frag.get("layer", "secondary_quote"),
        "snippet": snippet,
        "quote_ko": frag.get("quote_ko"),
        "context_hint": frag.get("context_hint"),
        "source_tier": frag.get("source_tier"),
        "source_path": path,
        "line_range": frag.get("line_range"),
        "verification_status": frag.get("verification_status"),
        "hanja_run_max": _longest_hanja_run(snippet),
        "text_backend": "ijeoma_secondary_proxy_v1",
        "physical_verified": False,
        "canon_claim": False,
        "proxy_merge": True,
    }
    if frag.get("grep_artifact"):
        chunk["grep_artifact"] = frag["grep_artifact"]
    if frag.get("mkm_pedagogy_pointer"):
        chunk["mkm_pedagogy_pointer"] = frag["mkm_pedagogy_pointer"]
    if not chunk["pdf_path"] and path:
        chunk["md_path"] = path
    return chunk


def merge(proxy: dict[str, Any], ledger: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    existing_ids = {c.get("source_id") for c in ledger.get("chunks", []) if c.get("source_id", "").startswith("SP-")}
    added: list[str] = []
    skipped: list[str] = []

    for frag in proxy.get("fragments", []):
        sp_id = frag["id"]
        if sp_id in existing_ids:
            skipped.append(sp_id)
            continue
        ledger.setdefault("chunks", []).append(frag_to_chunk(frag))
        added.append(sp_id)

    summary = ledger.setdefault("summary", {})
    summary["total_chunks"] = len(ledger["chunks"])
    summary["secondary_proxy_chunks"] = sum(
        1 for c in ledger["chunks"] if c.get("proxy_merge") is True
    )
    summary["primary_hanja_chunk_count"] = 0

    by_focus: dict[str, int] = {}
    for c in ledger["chunks"]:
        if c.get("proxy_merge"):
            f = c.get("focus", "other")
            by_focus[f] = by_focus.get(f, 0) + 1
    summary["secondary_proxy_by_focus"] = by_focus

    ledger["generated_at_utc"] = _utc()
    ledger.setdefault("secondary_proxy_merge", {})
    ledger["secondary_proxy_merge"] = {
        "merged_at_utc": _utc(),
        "proxy_schema": proxy.get("schema"),
        "proxy_path": _rel(PROXY),
        "added": added,
        "skipped": skipped,
    }

    report = {
        "schema": "ijeoma_secondary_proxy_merge_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "added_count": len(added),
        "skipped_count": len(skipped),
        "added": added,
        "skipped": skipped,
        "ledger_path": _rel(LEDGER),
        "proxy_path": _rel(PROXY),
        "canon_status": "not_acquired",
        "send_gate": "HOLD",
        "reproduce": "py scripts/merge_ijeoma_secondary_proxy_to_fragment_ledger_v1.py",
    }
    return ledger, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proxy", type=Path, default=PROXY)
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--report", type=Path, default=OUT_REPORT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.proxy.is_file():
        print(json.dumps({"ok": False, "error": f"missing proxy: {args.proxy}"}))
        return 1
    if not args.ledger.is_file():
        print(json.dumps({"ok": False, "error": f"missing ledger: {args.ledger}"}))
        return 1

    proxy = json.loads(args.proxy.read_text(encoding="utf-8-sig"))
    ledger = json.loads(args.ledger.read_text(encoding="utf-8-sig"))
    merged, report = merge(proxy, ledger)

    if not args.dry_run:
        args.ledger.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": args.dry_run,
                "added_count": report["added_count"],
                "skipped_count": report["skipped_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
