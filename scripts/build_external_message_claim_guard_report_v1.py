from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ARTIFACTS_DIR / "external_message_claim_guard_latest.json"


@dataclass(frozen=True)
class Rule:
    id: str
    pattern: re.Pattern[str]
    severity: str = "warn"


RULES: tuple[Rule, ...] = (
    Rule("trading_decisions", re.compile(r"\btrading decisions?\b", re.IGNORECASE)),
    Rule("trading_actions", re.compile(r"\btrading actions?\b", re.IGNORECASE)),
    Rule("doctrinal_proof", re.compile(r"\bdoctrinal proof\b", re.IGNORECASE)),
    Rule("guaranteed_returns", re.compile(r"\bguaranteed returns?\b", re.IGNORECASE)),
    Rule("perfect_claim", re.compile(r"\bperfect\b", re.IGNORECASE)),
    Rule("zero_hallucination", re.compile(r"\bzero[- ]hallucination\b", re.IGNORECASE)),
)

EXCLUDE_FILE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"manse_postella_rule_fix_candidates_latest\.json$", re.IGNORECASE),
)

# If a hit appears inside one of these contexts, count as intentional guard text.
ALLOW_CONTEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bwhat we do not claim\b", re.IGNORECASE),
    re.compile(r"\bavoid doctrinal, guarantee-style\b", re.IGNORECASE),
    re.compile(r"\bno doctrinal or guarantee-style claim\b", re.IGNORECASE),
    re.compile(r"\bnot as doctrinal proof\b", re.IGNORECASE),
    re.compile(r"\bnot doctrinal proof\b", re.IGNORECASE),
    re.compile(r"\brather than doctrinal proof\b", re.IGNORECASE),
    re.compile(r"\bperfect calculator\b", re.IGNORECASE),
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def iter_latest_json_files(base_dir: Path) -> list[Path]:
    files: list[Path] = []
    for p in base_dir.rglob("*_latest.json"):
        if p.is_file() and p.name != OUT_JSON.name:
            files.append(p)
    return sorted(files)


def flatten_strings(node: Any, path: str = "$") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(node, str):
        out.append((path, node))
    elif isinstance(node, dict):
        for k, v in node.items():
            out.extend(flatten_strings(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(flatten_strings(v, f"{path}[{i}]"))
    return out


def is_allowed_context(text: str) -> bool:
    return any(p.search(text) for p in ALLOW_CONTEXT_PATTERNS)


def scan_file(path: Path) -> dict[str, Any]:
    rel_file = str(path.relative_to(ROOT)).replace("\\", "/")
    if any(p.search(rel_file) for p in EXCLUDE_FILE_PATTERNS):
        return {
            "file": rel_file,
            "excluded": True,
            "hits": [],
            "allowed_hits": [],
        }

    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_text(encoding="utf-8-sig")

    # Some JSON artifacts are written with UTF-8 BOM.
    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")

    try:
        doc = json.loads(raw)
    except Exception as exc:  # pragma: no cover - guard report should continue
        return {
            "file": rel_file,
            "parse_error": str(exc),
            "hits": [],
            "allowed_hits": [],
        }

    hits: list[dict[str, Any]] = []
    allowed_hits: list[dict[str, Any]] = []
    for jpath, text in flatten_strings(doc):
        for rule in RULES:
            if rule.pattern.search(text):
                rec = {
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "json_path": jpath,
                    "snippet": text[:220],
                }
                if is_allowed_context(text):
                    allowed_hits.append(rec)
                else:
                    hits.append(rec)

    return {
        "file": rel_file,
        "hits": hits,
        "allowed_hits": allowed_hits,
    }


def main() -> int:
    files = iter_latest_json_files(ARTIFACTS_DIR)
    scanned = [scan_file(p) for p in files]

    files_with_hits = [r for r in scanned if r["hits"]]
    files_with_allowed_hits = [r for r in scanned if r["allowed_hits"]]
    parse_errors = [r for r in scanned if r.get("parse_error")]
    excluded = [r for r in scanned if r.get("excluded")]

    report = {
        "schema": "external_message_claim_guard_v1",
        "generated_at_utc": now_utc(),
        "scope": "docs/final/artifacts/**/*_latest.json",
        "summary": {
            "files_scanned": len(scanned),
            "files_with_blocking_hits": len(files_with_hits),
            "files_with_allowed_hits": len(files_with_allowed_hits),
            "parse_errors": len(parse_errors),
            "excluded_files": len(excluded),
            "status": "pass" if not files_with_hits and not parse_errors else "review_required",
        },
        "rules": [{"id": r.id, "severity": r.severity, "pattern": r.pattern.pattern} for r in RULES],
        "allow_context_rules": [p.pattern for p in ALLOW_CONTEXT_PATTERNS],
        "files_with_blocking_hits": files_with_hits,
        "files_with_allowed_hits": files_with_allowed_hits,
        "excluded_files": excluded,
        "parse_errors": parse_errors,
    }

    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[claim-guard] wrote {OUT_JSON}")
    print(
        "[claim-guard] status="
        f"{report['summary']['status']} files={report['summary']['files_scanned']} "
        f"blocking={report['summary']['files_with_blocking_hits']} parse_errors={report['summary']['parse_errors']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

