#!/usr/bin/env python3
"""Pre-publish scan for Logos public docs copy JSON (hub + glossary; no auto-edit)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COPY = ROOT / "projects/no1kmedi/marketing-site/logos-research-docs-copy.json"
DEFAULT_WORKSPACE_COPY = ROOT / "projects/no1kmedi/marketing-site/logos-research-copy.json"
DEFAULT_OUT = ROOT / "reports/logos_research_public_docs_copy_scan_v1_latest.json"

SCAN_PROFILES: dict[str, dict[str, bool]] = {
    "docs": {
        "require_meta": True,
        "require_footer": True,
        "require_demo_url": True,
        "require_glossary_min": True,
    },
    "workspace": {
        "require_meta": False,
        "require_footer": False,
        "require_demo_url": False,
        "require_glossary_min": False,
    },
}

NEGATION_MARKERS = (
    "do not",
    "does not",
    "하지 않",
    "아닌",
    "아닙니다",
    "금지",
    "forbidden",
    "제외",
    "미포함",
    "쓰지 말",
    "not ",
    "no buy/sell",
    "not investment",
    "not for ads",
    "비공개",
    "포함하지 않",
)

FORBIDDEN_JSON_KEYS = frozenset({"forbidden_in_public_ads", "excluded", "not"})

RULES: list[dict[str, Any]] = [
    {
        "id": "prophecy_hit_rate_marketing",
        "pattern": re.compile(r"적중률\s*[○0-9]|hit\s*rate\s*[○0-9]|예언\s*적중\s*[○0-9]", re.I),
        "severity": "block",
    },
    {
        "id": "thermo_alias_fact",
        "pattern": re.compile(r"\$E_i|\$P_f|\$D_d|\$H_c|γ\s*동적|gamma\s*transition", re.I),
        "severity": "block",
    },
    {
        "id": "external_send_true",
        "pattern": re.compile(r"ready_for_external_send:\s*true(?!\s*\()", re.I),
        "severity": "block",
    },
    {
        "id": "guaranteed_returns",
        "pattern": re.compile(r"guaranteed\s+returns|수익\s*보장|always\s+profitable", re.I),
        "severity": "block",
    },
    {
        "id": "toe_complete",
        "pattern": re.compile(r"TOE\s*완성|만물예측\s*완성|75식\s*전부\s*상용", re.I),
        "severity": "block",
    },
    {
        "id": "live_trading_go",
        "pattern": re.compile(r"live\s+trading\s+GO|실매매\s*트리거(?!\s*·)", re.I),
        "severity": "block",
    },
    {
        "id": "competitor_absolute",
        "pattern": re.compile(r"ChatGPT.*(항상|always).*(틀|wrong|hallucin)", re.I),
        "severity": "block",
    },
]

LEAK_RULES: list[dict[str, Any]] = [
    {
        "id": "repo_script_path",
        "pattern": re.compile(r"py\s+scripts/|scripts/[a-z0-9_\-]+\.py", re.I),
        "severity": "block",
    },
    {
        "id": "internal_docs_path",
        "pattern": re.compile(r"docs/final/|CONSTITUTION_INFERENCE|\.jsonl\b", re.I),
        "severity": "block",
    },
    {
        "id": "workspace_path_leak",
        "pattern": re.compile(r"C:\\\\workspace|/workspace/projects/", re.I),
        "severity": "block",
    },
    {
        "id": "internal_pipeline_id",
        "pattern": re.compile(r"gematria_bridge_v1|kernel_alignment", re.I),
        "severity": "block",
    },
]

REQUIRED_GLOSSARY_TERM_MIN = 15

REQUIRED_META: tuple[tuple[str, Any], ...] = (
    ("send_gate_hold", lambda m: m.get("send_gate") == "HOLD"),
    ("external_send_false", lambda m: m.get("ready_for_external_send") is False),
    ("public_draft", lambda m: m.get("status") == "PUBLIC_DRAFT"),
    ("non_gating_tag", lambda m: "NON_GATING" in (m.get("tags") or [])),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _line_negated(text: str) -> bool:
    lower = text.lower()
    return any(m.lower() in lower for m in NEGATION_MARKERS)


def _walk_strings(obj: Any, path: str = "$") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(obj, str):
        out.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}"
            out.extend(_walk_strings(v, child))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(_walk_strings(v, f"{path}[{i}]"))
    return out


def _segment_key(segment: str) -> str:
    return re.sub(r"\[\d+\]$", "", segment)


def _in_forbidden_context(json_path: str) -> bool:
    parts = json_path.split(".")
    return any(_segment_key(p) in FORBIDDEN_JSON_KEYS for p in parts)


def _scan_copy(path: Path, *, profile: str = "docs") -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "ok": False, "missing": True, "hits": [], "profile": profile}

    opts = SCAN_PROFILES.get(profile, SCAN_PROFILES["docs"])
    raw = path.read_text(encoding="utf-8", errors="replace")
    doc = json.loads(raw)
    meta = doc.get("_meta") or {}
    hits: list[dict[str, Any]] = []

    if opts["require_meta"]:
        for name, check in REQUIRED_META:
            if not check(meta):
                hits.append(
                    {
                        "rule_id": "required_meta",
                        "severity": "block",
                        "message": f"missing or invalid _meta.{name}",
                    }
                )

    if opts["require_footer"]:
        footer_en = (doc.get("footer_disclaimer") or {}).get("en", "")
        if not re.search(r"Not investment advice", footer_en, re.I):
            hits.append(
                {
                    "rule_id": "footer_disclaimer",
                    "severity": "block",
                    "message": "footer_disclaimer.en missing Not investment advice",
                }
            )

    if opts["require_demo_url"]:
        demo = doc.get("demo_url", "")
        if "api.jemaai.cloud/public_showroom_meaning_topology_qa_v2" not in demo:
            hits.append(
                {
                    "rule_id": "demo_url",
                    "severity": "block",
                    "message": "demo_url must point at public showroom topology QA v2",
                }
            )

    if profile == "workspace":
        pilot = doc.get("pilot_status") or {}
        if pilot.get("send_gate") != "HOLD" or pilot.get("ready_for_external_send") is not False:
            hits.append(
                {
                    "rule_id": "workspace_pilot_status",
                    "severity": "block",
                    "message": "pilot_status must send_gate HOLD and ready_for_external_send false",
                }
            )

    for json_path, text in _walk_strings(doc):
        if json_path.endswith("_meta.note"):
            continue
        forbidden_ctx = _in_forbidden_context(json_path)
        for rule in RULES + LEAK_RULES:
            if not rule["pattern"].search(text):
                continue
            if forbidden_ctx and rule in RULES:
                continue
            if _line_negated(text) and rule in RULES:
                continue
            hits.append(
                {
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "json_path": json_path,
                    "excerpt": text.strip()[:200],
                }
            )

    term_count = len((doc.get("glossary") or {}).get("terms") or [])
    if opts["require_glossary_min"] and term_count < REQUIRED_GLOSSARY_TERM_MIN:
        hits.append(
            {
                "rule_id": "glossary_term_min",
                "severity": "block",
                "message": f"term_count {term_count} < {REQUIRED_GLOSSARY_TERM_MIN}",
            }
        )

    blocking = [h for h in hits if h.get("severity") == "block"]
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    return {
        "path": rel,
        "profile": profile,
        "ok": not blocking,
        "missing": False,
        "term_count": term_count,
        "hits": hits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copy-json", default="", help="Single JSON only (legacy); default scans docs+workspace")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    parser.add_argument("--skip-workspace", action="store_true")
    args = parser.parse_args()

    if args.copy_json:
        targets = [(Path(args.copy_json), "docs")]
    else:
        targets = [(DEFAULT_COPY, "docs")]
        if not args.skip_workspace:
            targets.append((DEFAULT_WORKSPACE_COPY, "workspace"))

    results = [_scan_copy(path, profile=profile) for path, profile in targets]
    scan_ok = all(r.get("ok") and not r.get("missing") for r in results)

    report = {
        "schema": "logos_research_public_docs_copy_scan_v1",
        "generated_at_utc": _utc_now(),
        "scan_ok": scan_ok,
        "ready_for_external_send": False,
        "send_gate": "HOLD",
        "boundary_ack": "Automated public-docs scan only; not counsel sign-off.",
        "files": results,
        "file": results[0] if len(results) == 1 else results,
        "reproduce": "py scripts/check_logos_research_public_docs_copy_v1.py",
    }

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": scan_ok, "out": str(out_path.relative_to(ROOT)).replace("\\", "/")}))
    return 0 if scan_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
