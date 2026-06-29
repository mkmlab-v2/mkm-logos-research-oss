#!/usr/bin/env python3
"""Bootstrap pilot tenant slug: corpus JSONL + intake manifest (pre-chain)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROLE_PREFIX_RE = re.compile(r"\[(?:user|assistant)\]\s*", re.IGNORECASE)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl"
TEMPLATE = ROOT / "docs/final/artifacts/compression_b2b_prospect_poc_corpus_intake_v1.template.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _flatten_wtt_turns_to_text(obj: dict[str, Any]) -> str | None:
    """Align with export_wtt_sessions_to_compression_corpus_v1: turns[] -> single text."""
    turns = obj.get("turns")
    if not isinstance(turns, list) or not turns:
        return None
    parts: list[str] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role", "user"))
        parts.append(f"[{role}] {turn.get('text', '')}")
    joined = " ".join(parts).strip()
    return joined or None


def _strip_role_prefixes_from_text(text: str) -> str:
    return ROLE_PREFIX_RE.sub("", text).strip()


def _ensure_compression_text_field(obj: dict[str, Any], *, strip_role_prefixes: bool = False) -> None:
    """PoC reads text/raw_text/content/body — WTT session rows only have turns[]."""
    for key in ("text", "raw_text", "content", "body"):
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            if strip_role_prefixes:
                obj[key] = _strip_role_prefixes_from_text(val)
            return
    flat = _flatten_wtt_turns_to_text(obj)
    if flat:
        if strip_role_prefixes:
            flat = _strip_role_prefixes_from_text(flat)
        obj["text"] = flat
        if obj.get("session_id") and not obj.get("wtt_session_id"):
            obj["wtt_session_id"] = obj["session_id"]


def _build_corpus(
    tenant_id: str,
    source: Path,
    max_cases: int,
    *,
    contributor: bool = False,
    strip_role_prefixes: bool = False,
) -> Path:
    out = ROOT / f"data/compression/stateless_poc_prospect_{tenant_id}_v1.jsonl"
    lines: list[str] = []
    for i, line in enumerate(source.read_text(encoding="utf-8").splitlines()):
        if not line.strip() or i >= max_cases:
            break
        obj: dict[str, Any] = json.loads(line)
        _ensure_compression_text_field(obj, strip_role_prefixes=strip_role_prefixes)
        obj["id"] = f"prospect-{tenant_id}-{i:03d}"
        obj["tenant_id"] = tenant_id
        obj["source"] = f"pilot_intake_from_{source.stem}"
        obj["pilot_intake"] = True
        obj["send_gate"] = "HOLD"
        obj["ready_for_external_send"] = False
        if contributor:
            obj["contributor_provided"] = True
            obj["customer_provided"] = False
            labels = list(obj.get("labels") or [])
            for tag in ("contributor_provided", "research_only", "btrack_learning_v1"):
                if tag not in labels:
                    labels.append(tag)
            obj["labels"] = labels
        if strip_role_prefixes:
            labels = list(obj.get("labels") or [])
            for tag in ("btrack_cs_bodyonly_v1", "research_only"):
                if tag not in labels:
                    labels.append(tag)
            obj["labels"] = labels
        lines.append(json.dumps(obj, ensure_ascii=False))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _build_intake(
    tenant_id: str,
    corpus: Path,
    case_count: int,
    *,
    source: Path | None = None,
    customer_masked: bool = False,
    contributor_provided: bool = False,
    btrack_poc_options: dict[str, Any] | None = None,
) -> Path:
    tpl = json.loads(TEMPLATE.read_text(encoding="utf-8-sig"))
    out = ROOT / f"reports/compression_b2b_prospect_poc_corpus_{tenant_id}_v1.json"
    doc = dict(tpl)
    doc.pop("status", None)
    doc["status"] = "active_pilot_intake"
    doc["tenant_id"] = tenant_id
    doc["activated_at_utc"] = _utc()
    doc["corpus_path"] = corpus.relative_to(ROOT).as_posix()
    doc["corpus_case_count"] = case_count
    is_public_open = (
        not customer_masked
        and (
            (source is not None and ("public_open" in source.stem or source.name.startswith("stateless_poc_public_open")))
            or tenant_id.startswith("public-open-web")
        )
    )
    if contributor_provided:
        doc["corpus_provenance"] = "github_contributor_masked_jsonl_v1"
        if source is not None:
            doc["contributor_source_jsonl"] = source.relative_to(ROOT).as_posix()
        doc["labels"] = [
            "DRAFT",
            "research_only",
            "contributor_provided",
            "btrack_learning",
            "publish_allowed=false",
        ]
        doc["status"] = "active_contributor_intake"
        doc["boundary_ack"] = (
            "GitHub/open-bench contributor masked JSONL — B-track learning only; "
            "NOT customer_provided; SEND_GATE HOLD; Track A apply requires commander sign-off."
        )
    elif customer_masked:
        doc["corpus_provenance"] = "customer_masked_jsonl_v1"
        if source is not None:
            doc["customer_source_jsonl"] = source.relative_to(ROOT).as_posix()
        doc["labels"] = [
            "DRAFT",
            "research_only",
            "customer_pilot_intake",
            "publish_allowed=false",
        ]
        doc["status"] = "active_customer_pilot_intake"
        doc["boundary_ack"] = (
            "Customer-masked JSONL pilot — 1:1 ROI proxy only until counsel sign-off; "
            "SEND_GATE HOLD; not ad headline or public case study without human gates."
        )
    elif is_public_open:
        doc["corpus_provenance"] = "public_open_api_rss_v1_not_customer"
        doc["labels"] = [
            "DRAFT",
            "research_only",
            "public_open_web",
            "not_customer_corpus",
            "publish_allowed=false",
        ]
        doc["status"] = "active_public_open_intake"
        doc["boundary_ack"] = (
            "Public API/RSS corpus — operational proxy only; "
            "NOT customer masked JSONL; SEND_GATE HOLD; forbidden as customer case study."
        )
    else:
        doc["corpus_provenance"] = "golden40_public_safe_derived_internal_pilot_pending_customer_swap"
        doc["labels"] = [
            "DRAFT",
            "research_only",
            "internal_first_pilot",
            "publish_allowed=false",
        ]
        doc["boundary_ack"] = (
            "Internal first pilot intake — golden40-derived until customer-masked JSONL swap; "
            "SEND_GATE HOLD; not external case study"
        )
    doc["metering"]["tenant_id"] = tenant_id
    doc["metering"]["log_path"] = (
        f"reports/constitution/btrack_pilot/track_a_metering_log_{tenant_id}_v1.jsonl"
    )
    doc["blueprint"] = {
        "one_click_ps1": "scripts/Run-CompressionPilotIntakeBlueprint_v1.ps1",
        "canonical_slug": tenant_id,
    }
    doc["recommended_commands"] = {
        "one_click": (
            f"powershell -NoProfile -ExecutionPolicy Bypass -File "
            f"scripts/Run-CompressionPilotIntakeBlueprint_v1.ps1 -TenantId {tenant_id} -MaxCases {case_count}"
        ),
        "dollar_roi": (
            f"py scripts/build_compression_pilot_dollar_roi_v1.py --tenant-id {tenant_id} "
            f"--poc-json reports/customer_compression_stateless_poc_{tenant_id}_v1_latest.json "
            f"--metering-appendix-json docs/final/artifacts/compression_b2b_pilot_metering_appendix_{tenant_id}_latest.json"
        ),
    }
    doc["send_gate"] = "HOLD"
    doc["ready_for_external_send"] = False
    if btrack_poc_options:
        doc["btrack_poc_options"] = btrack_poc_options
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", default="prospect-first-pilot-v1")
    ap.add_argument("--source-jsonl", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument(
        "--customer-masked",
        action="store_true",
        help="Source is customer-provided masked JSONL (not golden40/public-open).",
    )
    ap.add_argument(
        "--contributor-provided",
        action="store_true",
        help="Source is GitHub/open-bench contributor JSONL (not customer).",
    )
    ap.add_argument(
        "--strip-role-prefixes",
        action="store_true",
        help="[HYPO] Strip [user]/[assistant] from flattened WTT text (CS short-chat B-track).",
    )
    ap.add_argument("--short-context-token-threshold", type=int, default=None)
    ap.add_argument("--short-context-max-saving-rate", type=float, default=None)
    args = ap.parse_args()

    src = args.source_jsonl.resolve()
    if not src.is_file():
        print(f"error: missing source corpus: {src}", file=sys.stderr)
        return 2

    btrack_poc_options: dict[str, Any] | None = None
    if (
        args.strip_role_prefixes
        or args.short_context_token_threshold is not None
        or args.short_context_max_saving_rate is not None
    ):
        btrack_poc_options = {
            "hypothesis_tag": "[HYPO]",
            "research_only": True,
            "strip_role_prefixes": bool(args.strip_role_prefixes),
            "short_context_token_threshold": args.short_context_token_threshold,
            "short_context_max_saving_rate": args.short_context_max_saving_rate,
        }

    corpus = _build_corpus(
        args.tenant_id,
        src,
        args.max_cases,
        contributor=args.contributor_provided,
        strip_role_prefixes=args.strip_role_prefixes,
    )
    case_count = sum(1 for ln in corpus.read_text(encoding="utf-8").splitlines() if ln.strip())
    intake = _build_intake(
        args.tenant_id,
        corpus,
        case_count,
        source=src,
        customer_masked=args.customer_masked and not args.contributor_provided,
        contributor_provided=args.contributor_provided,
        btrack_poc_options=btrack_poc_options,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "tenant_id": args.tenant_id,
                "corpus": corpus.relative_to(ROOT).as_posix(),
                "intake": intake.relative_to(ROOT).as_posix(),
                "case_count": case_count,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
