#!/usr/bin/env python3
"""External-facing copy Fact-Lock pass — forbidden hype scan + optional contract header.

Before grants, IR decks, support docs, or public landing copy:
  py scripts/check_external_facing_fact_lock_v1.py --target path/to/draft.md
  py scripts/check_external_facing_fact_lock_v1.py --target draft.md --write-contract reports/my_contract.json

Exit 0 = no forbidden hits in scanned files. Does not replace legal review or PUBLIC_FACING human read.

Middleware Claim-A / L0 onepager targets also run headline_reuse_guard (orphan
legacy 'Send pointers' without counter-signal → fail). Reproduce:
  py scripts/check_mkm_middleware_headline_reuse_guard_v1.py
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT_DEFAULT = ROOT / "reports/external_facing_fact_lock_v1_latest.json"
POLICY = ROOT / "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md"
TRACK_C = ROOT / "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md"

# Policy SSOT paths — may contain forbidden phrases as negative examples.
SKIP_EXACT = {
    POLICY.resolve(),
    TRACK_C.resolve(),
    (ROOT / "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md").resolve(),
    (ROOT / "docs/final/CENTRAL_AGENT_MEMORY_V1.md").resolve(),
    (ROOT / "reports/nvidia_grand_challenge_evidence_summary_v1.md").resolve(),
}

DEFAULT_TARGETS = [
    ROOT / "reports/nvidia_grand_challenge_application_en_v1.md",
    ROOT / "reports/nvidia_grand_challenge_attachment_pack_v1.md",
    ROOT / "docs/final/artifacts/compression_enterprise_executive_summary_v1.md",
    ROOT / "docs/final/artifacts/logos_oss_premarket_smoke_guide_v1.md",
]

FORBIDDEN: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"시장.{0,12}(유일|전무|독보)"), "market_unique_ko"),
    (re.compile(r"(?<![\w-])global(?:ly)?\s+(?:unique|only)\s+package", re.I), "market_unique_en"),
    (re.compile(r"(?<![\w-])zero[\s-]*hallucination|0%\s*hallucination", re.I), "zero_hallucination_claim"),
    (re.compile(r"환각\s*0\s*%"), "zero_hallucination_claim_ko"),
    (re.compile(r"완성\s*(된\s*)?(글로벌\s*)?OS|full\s+global\s+os\s+complete|JEMA\s+OS\s+complete", re.I), "full_os_complete"),
    (re.compile(r"60\s*초\s*(이내|만에)|within\s+60\s*seconds", re.I), "sixty_second_proof"),
    (re.compile(r"GPT[\s-]*(killer|replacement)|killer\s+AI", re.I), "gpt_killer"),
    (re.compile(r"배포\s*(자체)?\s*잠금|deploy(?:ment)?\s+hard\s+lock", re.I), "deploy_hard_lock_overclaim"),
    (re.compile(r"파괴적|game[\s-]*chang(er|ing)", re.I), "hype_destroyer"),
    (re.compile(r"글로벌\s*0\.1\s*%|top\s*0\.1\s*%\s*globally", re.I), "unverified_percentile"),
    (re.compile(r"repair_v2?\s+only.*(promot|승격)", re.I), "repair_only_promotion"),
    (re.compile(r"모델\s*(이\s*)?해결|model\s+solved", re.I), "model_solved_headline"),
]

NEGATION_LINE = re.compile(
    r"do\s+not\s+claim|don't\s+claim|not\s+claim|Non-claims|Forbidden|금지|"
    r"negative example|면책|guardrail|does not|do not imply|not imply|"
    r"^-\s+.*(?:zero|hallucination|유일)",
    re.I,
)


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _normalize_for_negation(line: str) -> str:
    return re.sub(r"\*+", "", line)


def _line_is_negation_context(line: str) -> bool:
    for candidate in (line, _normalize_for_negation(line)):
        if NEGATION_LINE.search(candidate):
            return True
    if re.search(r"what we do not claim|do not claim|non-claims", line, re.I):
        return True
    return False


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _should_skip(path: Path) -> bool:
    try:
        if path.resolve() in SKIP_EXACT:
            return True
    except OSError:
        pass
    rel = path.as_posix().lower()
    if "/tests/" in rel or rel.startswith("tests/"):
        return True
    if "/fixtures/" in rel or "/forbidden_examples/" in rel:
        return True
    return False


def _needs_headline_reuse_guard(path: Path) -> bool:
    """Claim-A / L0 middleware external drafts — Claude residual: checklist must be exit-gated."""
    name = path.name.lower()
    if not name.endswith((".md", ".txt")):
        return False
    needles = (
        "mkm_middleware_l0_send_ready",
        "mkm_middleware_claim_a_",
        "mkm_middleware_human_blind",
        "mkm_middleware_w2_human_blind",
    )
    return any(n in name for n in needles)


def _headline_reuse_violations(path: Path) -> list[dict[str, Any]]:
    from scripts.check_mkm_middleware_headline_reuse_guard_v1 import check_text  # noqa: WPS433

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [
            {
                "file": _display_path(path),
                "code": "headline_reuse_read_error",
                "detail": str(e),
            }
        ]
    row = check_text(text, path=str(path))
    if row.get("ok"):
        return []
    return [
        {
            "file": _display_path(path),
            "code": "headline_reuse_orphan",
            "orphan_headline": bool(row.get("orphan_headline")),
            "has_headline_core": bool(row.get("has_headline_core")),
            "has_counter_signal_marker": bool(row.get("has_counter_signal_marker")),
            "detail": (
                "legacy Send-pointers headline without counter-signal "
                "(run check_mkm_middleware_headline_reuse_guard_v1.py)"
            ),
        }
    ]


def _scan_file(path: Path) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        hits.append({"file": str(path), "code": "read_error", "detail": str(e)})
        return hits
    for line_no, line in enumerate(text.splitlines(), start=1):
        if _line_is_negation_context(line):
            continue
        for pattern, code in FORBIDDEN:
            if pattern.search(line):
                hits.append(
                    {
                        "file": _display_path(path),
                        "line": line_no,
                        "code": code,
                        "excerpt": line.strip()[:160],
                    }
                )
    return hits


def build_contract_header(
    *,
    scope: str,
    evidence: list[dict[str, str]],
    not_claimed: list[str],
    targets: list[str],
) -> dict[str, Any]:
    return {
        "schema": "mkm_external_facing_contract_header_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "scope_closed": scope,
        "evidence": evidence,
        "not_claimed": not_claimed,
        "targets": targets,
        "policy_ref": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
        "reproduce_scan": "py scripts/check_external_facing_fact_lock_v1.py --target <draft>",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--target",
        action="append",
        default=[],
        help="Draft file to scan (repeatable). Default: known public-facing report set.",
    )
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--write-contract",
        type=Path,
        default=None,
        help="Write contract header JSON (requires --scope).",
    )
    ap.add_argument("--scope", default="", help="One-line closed scope for contract header.")
    ap.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="artifact_path|reproduce_command pairs separated by |",
    )
    args = ap.parse_args()

    targets: list[Path] = []
    for raw in args.target:
        p = Path(raw)
        if not p.is_absolute():
            p = ROOT / p
        if p.is_file():
            targets.append(p)
    if not targets:
        targets = [p for p in DEFAULT_TARGETS if p.is_file()]

    violations: list[dict[str, Any]] = []
    scanned: list[str] = []
    headline_guard_targets: list[str] = []
    for path in targets:
        if _should_skip(path):
            continue
        scanned.append(_display_path(path))
        violations.extend(_scan_file(path))
        if _needs_headline_reuse_guard(path):
            headline_guard_targets.append(_display_path(path))
            violations.extend(_headline_reuse_violations(path))

    ok = len(violations) == 0 and bool(scanned)

    evidence_rows: list[dict[str, str]] = []
    for item in args.evidence:
        if "|" in item:
            artifact, cmd = item.split("|", 1)
            evidence_rows.append({"artifact": artifact.strip(), "reproduce": cmd.strip()})

    contract = None
    if args.write_contract:
        if not args.scope.strip():
            print("ERROR: --write-contract requires --scope", flush=True)
            return 1
        contract = build_contract_header(
            scope=args.scope.strip(),
            evidence=evidence_rows,
            not_claimed=[
                "send_open",
                "track_a_promotion",
                "market_unique",
                "full_os_complete",
                "zero_hallucination",
                "repair_v2_only_promotion",
            ],
            targets=scanned,
        )
        args.write_contract.parent.mkdir(parents=True, exist_ok=True)
        args.write_contract.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "external_facing_fact_lock_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "files_scanned": len(scanned),
        "scanned": scanned,
        "violation_count": len(violations),
        "violations": violations[:100],
        "forbidden_pattern_count": len(FORBIDDEN),
        "headline_reuse_guard": {
            "applied": bool(headline_guard_targets),
            "targets": headline_guard_targets,
            "script": "scripts/check_mkm_middleware_headline_reuse_guard_v1.py",
            "note_ko": (
                "Claim-A/L0 MD targets: orphan legacy headline → fail "
                "(checklist JSON is script output, not manual-only doc)."
            ),
        },
        "policy_ref": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
        "contract_header": str(args.write_contract).replace("\\", "/") if contract else None,
        "reproduce": "py scripts/check_external_facing_fact_lock_v1.py --target <draft.md>",
        "note_ko": "채팅 흥분 문장 금지 — 디스크·exit0·dual report만 대외 SSOT. 법무/지휘관 최종 read 별도.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "violations": len(violations), "scanned": len(scanned), "out": str(args.out)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
