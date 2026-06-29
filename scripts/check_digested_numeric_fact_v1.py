#!/usr/bin/env python3
"""Active fact-lite for digested numeric facts (DeepResearchEval-inspired, B-track).

Promotes verification Unknown→Right when value appears in arXiv abstract/title.
Conservative: does not auto-mark Wrong in default mode.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_digested_numeric_fact_check_latest.json"

from scripts.check_research_lit_review_fact_support_v1 import (  # noqa: E402
    fetch_arxiv_records_batch,
    _normalize_arxiv_id,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def value_in_text(value: float, text: str, unit: str) -> bool:
    text_n = text.replace(",", " ")
    candidates: list[str] = []
    if value == int(value):
        candidates.append(str(int(value)))
    candidates.append(f"{value}")
    candidates.append(f"{value:.4f}".rstrip("0").rstrip("."))
    candidates.append(f"{value:.2f}".rstrip("0").rstrip("."))
    if unit == "percent":
        for c in list(candidates):
            candidates.append(f"{c}%")
    seen: set[str] = set()
    for cand in candidates:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        if re.search(re.escape(cand), text_n):
            return True
    return False


def run_active_fact_lite(
    doc: dict[str, Any],
    *,
    offline: bool = False,
    only_unknown: bool = True,
    mark_miss_as_wrong: bool | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    facts = list(doc.get("facts") or [])
    entries: list[dict[str, Any]] = []
    arxiv_ids: list[str] = []
    eligible: list[dict[str, Any]] = []

    for fact in facts:
        status = str((fact.get("verification") or {}).get("status") or "Unknown")
        if only_unknown and status != "Unknown":
            continue
        aid = (fact.get("provenance") or {}).get("arxiv_id")
        if isinstance(aid, str) and aid.strip():
            norm = _normalize_arxiv_id(aid)
            eligible.append(fact)
            if norm not in arxiv_ids:
                arxiv_ids.append(norm)

    records: dict[str, dict[str, Any]] = {}
    if mark_miss_as_wrong is None:
        mark_miss_as_wrong = not offline
    if not offline and arxiv_ids:
        records = fetch_arxiv_records_batch(arxiv_ids)

    promoted = 0
    wrong_n = 0
    for fact in facts:
        fact_id = str(fact.get("fact_id") or "")
        verification = dict(fact.get("verification") or {})
        status = str(verification.get("status") or "Unknown")
        prov = fact.get("provenance") or {}
        aid = prov.get("arxiv_id")

        entry: dict[str, Any] = {
            "fact_id": fact_id,
            "prior_status": status,
            "new_status": status,
            "arxiv_id": aid,
        }

        if only_unknown and status != "Unknown":
            entry["skipped"] = True
            entry["reason"] = "not_unknown"
            entries.append(entry)
            continue

        if not isinstance(aid, str) or not aid.strip():
            entry["skipped"] = True
            entry["reason"] = "no_arxiv_id"
            entries.append(entry)
            continue

        if offline:
            entry["skipped"] = True
            entry["reason"] = "offline_mode"
            entries.append(entry)
            continue

        norm = _normalize_arxiv_id(aid)
        rec = records.get(norm) or {}
        if rec.get("error"):
            verification["status"] = "Unknown"
            verification["method"] = "active_fact_lite"
            verification["reason"] = str(rec.get("error"))
            fact["verification"] = verification
            entry["new_status"] = "Unknown"
            entry["detail"] = rec.get("error")
            entries.append(entry)
            continue

        title = str(rec.get("title") or "")
        abstract = str(rec.get("abstract") or "")
        blob = f"{title} {abstract}"
        value = float(fact["value"])
        unit = str(fact.get("unit") or "other")
        if value_in_text(value, blob, unit):
            verification["status"] = "Right"
            verification["method"] = "active_fact_lite"
            verification["reason"] = "value_in_arxiv_title_or_abstract"
            fact["verification"] = verification
            entry["new_status"] = "Right"
            promoted += 1
        else:
            verification["method"] = "active_fact_lite"
            if mark_miss_as_wrong:
                verification["status"] = "Wrong"
                verification["reason"] = "value_not_in_arxiv_title_or_abstract"
                entry["new_status"] = "Wrong"
                wrong_n += 1
            else:
                verification["reason"] = "value_not_in_arxiv_title_or_abstract"
                entry["new_status"] = "Unknown"
            fact["verification"] = verification
            entry["detail"] = "not promoted"

        entries.append(entry)

    out_doc = dict(doc)
    out_doc["facts"] = facts
    prov = dict(out_doc.get("provenance") or {})
    prov["active_fact_lite_at_utc"] = _utc_now()
    flags = list(prov.get("uncertainty_flags") or [])
    if promoted:
        flags.append(f"active_fact_lite_promoted_{promoted}")
    prov["uncertainty_flags"] = flags
    out_doc["provenance"] = prov

    right_n = sum(1 for f in facts if (f.get("verification") or {}).get("status") == "Right")
    unknown_n = sum(1 for f in facts if (f.get("verification") or {}).get("status") == "Unknown")
    wrong_count = sum(1 for f in facts if (f.get("verification") or {}).get("status") == "Wrong")
    report = {
        "schema": "mkm_digested_numeric_fact_check_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "mode": "offline" if offline else "online",
        "mark_miss_as_wrong": mark_miss_as_wrong,
        "eligible_with_arxiv": len(eligible),
        "promoted_to_right": promoted,
        "marked_wrong": wrong_n,
        "right_count_after": right_n,
        "unknown_count_after": unknown_n,
        "wrong_count_after": wrong_count,
        "entries": entries,
        "research_only": True,
        "send_gate": "HOLD",
    }
    return out_doc, report


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Active fact-lite on digested numeric facts")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None, help="updated digested JSON (default: overwrite input)")
    parser.add_argument("--report", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--no-mark-miss-as-wrong", action="store_true")
    parser.add_argument("--include-already-right", action="store_true")
    parser.add_argument(
        "--production",
        action="store_true",
        help="production mode: forbid --no-mark-miss-as-wrong (also MKM_DIGESTION_PRODUCTION env)",
    )
    args = parser.parse_args()

    if args.no_mark_miss_as_wrong and (args.production or _env_truthy("MKM_DIGESTION_PRODUCTION")):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "forbidden --no-mark-miss-as-wrong in production digestion mode",
                },
                ensure_ascii=False,
            )
        )
        return 3

    in_path = args.input.resolve()
    if not in_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {in_path}"}, ensure_ascii=False))
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    updated, report = run_active_fact_lite(
        doc,
        offline=args.offline,
        only_unknown=not args.include_already_right,
        mark_miss_as_wrong=False if args.no_mark_miss_as_wrong else None,
    )

    out_path = args.out.resolve() if args.out else in_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_path": _posix_path(out_path),
                "report_path": _posix_path(report_path),
                "promoted_to_right": report["promoted_to_right"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
