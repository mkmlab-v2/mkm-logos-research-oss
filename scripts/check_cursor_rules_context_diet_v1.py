from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "cursor_rules_context_diet_v1"
DEFAULT_MAX_ALWAYS_APPLY = 10
DEFAULT_MAX_ALWAYS_APPLY_LINES = 320
DEFAULT_MAX_AGENTS_MD_LINES = 95
DEFAULT_MAX_CLAUDE_MD_LINES = 110
DEFAULT_MAX_CURSORRULES_LINES = 150
CURSORRULES_TEMPLATE_REL = "docs/final/artifacts/cursorrules_slim_ssot_v1.txt"

# Core stack — keep alwaysApply (context diet SSOT; change only with this script + review).
CORE_ALWAYS_APPLY = frozenset(
    {
        "central-agent-memory.mdc",
        "cursor-session-validation-baseline-v1.mdc",
        "mission-log-combat-ssot.mdc",
        "mkm-automation-gate.mdc",
        "mkm-browser-automation-v1.mdc",
        "mkm-solo-background-ops-auto.mdc",
        "mkm-commander-chat-tone-v1.mdc",
        "raw-repair-dual-reporting-v1.mdc",
        "tracka-raw-gate-guard-v1.mdc",
    }
)

# Lane / trigger rules — must stay agent-requestable (alwaysApply: false).
LANE_REQUESTABLE = frozenset(
    {
        "12ai-orchestration.mdc",
        "autonomous-web-search-v1.mdc",
        "compression-narrative-fact-lock-v1.mdc",
        "cursor-cloud-sandbox-boundary.mdc",
        "gut-brain-metaphor-agent-v1.mdc",
        "local-lock-security-guard-v1.mdc",
        "mkm-cognitive-architecture-v1.mdc",
        "mkm-core-coordinate-map-v1.mdc",
        "mkm-commander-cursor-perf-v1.mdc",
        "mkm-commander-delegation-router-v1.mdc",
        "mkm-delegation-research-assist-v1.mdc",
        "mkm-identity-engine-adapter-v1.mdc",
        "mkm-paper-digest-trigger-v1.mdc",
        "mkm-paper-disk-verdict-four-slot-v1.mdc",
        "mkm-paste-epistemic-triage-v1.mdc",
        "notebooklm-mcp-session-bridge.mdc",
        "parallel-passive-loop-v1.mdc",
        "pr-review-canvas-auto.mdc",
        "prophecy-core-fact-lock-v1.mdc",
        "regime-field-constitution.mdc",
        "sovereign-central-command.mdc",
    }
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Audit .cursor/rules alwaysApply stack for context diet (MKM Cursor)."
    )
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument(
        "--rules-dir",
        default=".cursor/rules",
        help="Rules directory relative to workspace root",
    )
    p.add_argument(
        "--output-json",
        default="reports/cursor_rules_context_diet_v1_latest.json",
    )
    p.add_argument(
        "--max-always-apply",
        type=int,
        default=DEFAULT_MAX_ALWAYS_APPLY,
    )
    p.add_argument(
        "--max-always-apply-lines",
        type=int,
        default=DEFAULT_MAX_ALWAYS_APPLY_LINES,
    )
    p.add_argument(
        "--max-agents-md-lines",
        type=int,
        default=DEFAULT_MAX_AGENTS_MD_LINES,
    )
    p.add_argument(
        "--max-claude-md-lines",
        type=int,
        default=DEFAULT_MAX_CLAUDE_MD_LINES,
    )
    p.add_argument(
        "--max-cursorrules-lines",
        type=int,
        default=DEFAULT_MAX_CURSORRULES_LINES,
    )
    p.add_argument(
        "--cursorrules-template",
        default=CURSORRULES_TEMPLATE_REL,
        help="Slim SSOT template that must match .cursorrules byte-for-byte",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on count/line budget or lane-rule alwaysApply violations",
    )
    return p.parse_args()


def _is_always_apply(text: str) -> bool:
    m = re.search(r"^alwaysApply:\s*(true|false)\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not m:
        return False
    return m.group(1).lower() == "true"


def _line_count(text: str) -> int:
    return len(text.splitlines())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_rules(rules_dir: Path) -> dict:
    entries: list[dict] = []
    for path in sorted(rules_dir.glob("*.mdc")):
        text = path.read_text(encoding="utf-8")
        entries.append(
            {
                "name": path.name,
                "lines": _line_count(text),
                "always_apply": _is_always_apply(text),
            }
        )

    always = [e for e in entries if e["always_apply"]]
    always_names = {e["name"] for e in always}
    always_lines = sum(e["lines"] for e in always)

    violations: list[str] = []
    if len(always) > 0:
        unexpected_aa = sorted(always_names - CORE_ALWAYS_APPLY)
        if unexpected_aa:
            violations.append(f"unexpected_always_apply:{','.join(unexpected_aa)}")
        missing_core = sorted(CORE_ALWAYS_APPLY - always_names)
        if missing_core:
            violations.append(f"missing_core_always_apply:{','.join(missing_core)}")
        lane_promoted = sorted(always_names & LANE_REQUESTABLE)
        if lane_promoted:
            violations.append(f"lane_rules_must_not_always_apply:{','.join(lane_promoted)}")

    return {
        "rules": entries,
        "always_apply_count": len(always),
        "always_apply_lines": always_lines,
        "always_apply_names": sorted(e["name"] for e in always),
        "core_always_apply_expected": sorted(CORE_ALWAYS_APPLY),
        "lane_requestable_expected": sorted(LANE_REQUESTABLE),
        "violations": violations,
    }


def audit_inject_docs(
    root: Path,
    max_agents: int,
    max_claude: int,
    max_cursorrules: int,
    cursorrules_template_rel: str,
) -> dict:
    agents_path = root / "AGENTS.md"
    claude_path = root / "CLAUDE.md"
    cursorrules_path = root / ".cursorrules"
    template_path = root / cursorrules_template_rel
    agents_lines = _line_count(agents_path.read_text(encoding="utf-8")) if agents_path.is_file() else 0
    claude_lines = _line_count(claude_path.read_text(encoding="utf-8")) if claude_path.is_file() else 0
    cursorrules_lines = (
        _line_count(cursorrules_path.read_text(encoding="utf-8")) if cursorrules_path.is_file() else 0
    )

    violations: list[str] = []
    if not agents_path.is_file():
        violations.append("agents_md_missing")
    elif agents_lines > max_agents:
        violations.append(f"agents_md_lines={agents_lines}>{max_agents}")
    if claude_path.is_file() and claude_lines > max_claude:
        violations.append(f"claude_md_lines={claude_lines}>{max_claude}")
    if not cursorrules_path.is_file():
        violations.append("cursorrules_missing")
    elif cursorrules_lines > max_cursorrules:
        violations.append(f"cursorrules_lines={cursorrules_lines}>{max_cursorrules}")
    template_in_sync: bool | None = None
    if template_path.is_file() and cursorrules_path.is_file():
        template_in_sync = _sha256(template_path) == _sha256(cursorrules_path)
        if not template_in_sync:
            violations.append("cursorrules_template_drift")
    elif not template_path.is_file():
        violations.append("cursorrules_template_missing")

    return {
        "agents_md_lines": agents_lines,
        "claude_md_lines": claude_lines,
        "cursorrules_lines": cursorrules_lines,
        "cursorrules_template_in_sync": template_in_sync,
        "violations": violations,
    }


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    rules_dir = root / args.rules_dir
    out = root / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)

    if not rules_dir.is_dir():
        payload = {
            "schema": SCHEMA,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ERROR",
            "reason": "rules_dir_missing",
            "rules_dir": str(rules_dir).replace("\\", "/"),
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"cursor_rules_context_diet=ERROR output={out.as_posix()}")
        return 2

    audit = audit_rules(rules_dir)
    inject = audit_inject_docs(
        root,
        args.max_agents_md_lines,
        args.max_claude_md_lines,
        args.max_cursorrules_lines,
        args.cursorrules_template,
    )
    budget_violations: list[str] = []
    if audit["always_apply_count"] > args.max_always_apply:
        budget_violations.append(
            f"always_apply_count={audit['always_apply_count']}>{args.max_always_apply}"
        )
    if audit["always_apply_lines"] > args.max_always_apply_lines:
        budget_violations.append(
            f"always_apply_lines={audit['always_apply_lines']}>{args.max_always_apply_lines}"
        )

    all_violations = audit["violations"] + budget_violations + inject["violations"]
    ok = len(all_violations) == 0
    status = "PASS" if ok else "WARN"

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "ok": ok,
        "violations": all_violations,
        "always_apply_count": audit["always_apply_count"],
        "always_apply_lines": audit["always_apply_lines"],
        "always_apply_names": audit["always_apply_names"],
        "core_always_apply_expected": audit["core_always_apply_expected"],
        "lane_requestable_expected": audit["lane_requestable_expected"],
        "inject_docs": {
            "agents_md_lines": inject["agents_md_lines"],
            "claude_md_lines": inject["claude_md_lines"],
            "cursorrules_lines": inject["cursorrules_lines"],
            "cursorrules_template_in_sync": inject["cursorrules_template_in_sync"],
        },
        "budget": {
            "max_always_apply": args.max_always_apply,
            "max_always_apply_lines": args.max_always_apply_lines,
            "max_agents_md_lines": args.max_agents_md_lines,
            "max_claude_md_lines": args.max_claude_md_lines,
            "max_cursorrules_lines": args.max_cursorrules_lines,
        },
        "rules": audit["rules"],
        "reproducible_command": "py scripts/check_cursor_rules_context_diet_v1.py --strict",
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "cursor_rules_context_diet="
        f"{status} always_apply={audit['always_apply_count']} "
        f"lines={audit['always_apply_lines']} "
        f"agents_md={inject['agents_md_lines']} "
        f"cursorrules={inject['cursorrules_lines']} output={out.as_posix()}"
    )
    if all_violations:
        for v in all_violations:
            print(f"  violation: {v}")

    if args.strict and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
