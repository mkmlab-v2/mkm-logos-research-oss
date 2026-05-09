#!/usr/bin/env python3
"""Daily agent memory GC: CENTRAL path sanity + routing snapshot + prune hints."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path("C:/workspace")
CENTRAL_REL = "docs/final/CENTRAL_AGENT_MEMORY_V1.md"
CONSTITUTION_REL = "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
ROUTING_SCRIPT = WORKSPACE / "scripts" / "build_memory_pruning_routing_status_v1.py"
OUT_JSON = WORKSPACE / "docs" / "final" / "artifacts" / "agent_memory_garbage_collection_latest.json"
OUT_MD = WORKSPACE / "docs" / "final" / "artifacts" / "agent_memory_garbage_collection_latest.md"

# Briefing / local-only pointers — do not treat as repo hygiene failures.
_OPTIONAL_REF_NAMES = frozenset(
    {
        "athena_memory_bank.md",
        "athena_memory_bank_v2.md",
        "CURRENT_OPS_SNAPSHOT.md",
    }
)

# Paths inside backticks ending with common extensions.
_BACKTICK = re.compile(
    r"`([^\s`]+?(?:\.(?:md|py|ps1|json|mjs|tsx?|jsx?|html|yaml|yml|txt)|schema\.json))`"
)
# Loose docs/projects/scripts references without extension (segment ends at space , ) ] `).
_LOOSE = re.compile(
    r"\b((?:docs|scripts|projects)/[^\s`)\],]+?\.(?:md|py|ps1|json|mjs|tsx?|jsx?|yaml|yml))\b"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_routing_snapshot() -> dict[str, Any]:
    if not ROUTING_SCRIPT.is_file():
        return {"error": "routing_script_missing", "path": str(ROUTING_SCRIPT)}
    proc = subprocess.run(
        [sys.executable, str(ROUTING_SCRIPT)],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    out_path = WORKSPACE / "docs" / "final" / "artifacts" / "memory_pruning_routing_status_latest.json"
    if proc.returncode != 0:
        return {
            "error": "routing_run_failed",
            "returncode": proc.returncode,
            "stderr": (proc.stderr or "")[:2000],
        }
    if out_path.is_file():
        try:
            return json.loads(out_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            return {"error": "routing_json_invalid", "detail": str(e)}
    return {"error": "routing_output_missing"}


def _extract_paths_from_central(text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for m in _BACKTICK.finditer(text):
        p = m.group(1).strip()
        if p.startswith("http"):
            continue
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    for m in _LOOSE.finditer(text):
        p = m.group(1).strip().rstrip(".,;:")
        if p.startswith("http"):
            continue
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered


def _checkpoint_stats(text: str) -> dict[str, Any]:
    start = "<!-- ATHENA_CHECKPOINT_V1_START -->"
    end = "<!-- ATHENA_CHECKPOINT_V1_END -->"
    i0 = text.find(start)
    i1 = text.find(end)
    if i0 < 0 or i1 < 0 or i1 <= i0:
        return {"present": False, "bullet_line_count": 0}
    block = text[i0 + len(start) : i1]
    bullets = [ln for ln in block.splitlines() if ln.strip().startswith("- **")]
    return {"present": True, "bullet_line_count": len(bullets)}


def _expand_reference_tokens(raw: str) -> list[str]:
    raw_clean = raw.replace("\\", "/").strip().rstrip("/")
    if not raw_clean:
        return []
    if raw_clean.endswith(".json/.md"):
        base = raw_clean[: -len(".json/.md")]
        return [base + ".json", base + ".md"]
    return [raw_clean]


def _candidate_paths(raw: str) -> list[Path]:
    """Try repo-relative locations for backtick references (often basename-only)."""
    raw = raw.replace("\\", "/").strip().lstrip("/")
    cands: list[Path] = []
    if not raw or "://" in raw:
        return cands
    # External / non-repo pointers (do not flag as missing files)
    if re.match(r"^(?:/opt/|opt/|/etc/)", raw, re.I):
        return cands
    if raw.startswith(("memory/", "vault/", "G:/", "g:/")):
        return cands

    root = WORKSPACE
    primary = (root / raw).resolve()
    cands.append(primary)

    name_only = Path(raw).name
    if raw == name_only or "/" not in raw:
        cands.extend(
            [
                (root / "docs" / "final" / name_only).resolve(),
                (root / "scripts" / name_only).resolve(),
                (root / "projects" / "no1kmedi" / "scripts" / name_only).resolve(),
                (root / "projects" / "no1kmedi" / name_only).resolve(),
            ]
        )
    if raw.startswith("artifacts/"):
        cands.append((root / "docs" / "final" / raw).resolve())

    bn = Path(raw).name
    if bn.endswith(".json"):
        cands.append((root / "docs" / "final" / "artifacts" / bn).resolve())
        cands.append((root / "reports" / bn).resolve())
    if bn.endswith(".ps1"):
        cands.append((root / "scripts" / "deploy" / bn).resolve())
    if bn.endswith(".md"):
        cands.append(
            (
                root
                / "projects"
                / "bitcoin-trading"
                / "ops"
                / "windows-rehearsal"
                / "jemaai-cloud-mvp"
                / bn
            ).resolve()
        )
    if bn.endswith(".py"):
        cands.append((root / "scripts" / bn).resolve())
        cands.append((root / "projects" / "bitcoin-trading" / bn).resolve())
        cands.append((root / "projects" / "bitcoin-trading" / "scripts" / bn).resolve())
    if raw.startswith("config/"):
        cands.append((root / "projects" / "bitcoin-trading" / raw).resolve())
    return cands


def _resolve_and_check(rel_paths: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ok: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    repo_root = WORKSPACE.resolve()
    seen_ok_paths: set[str] = set()
    seen_missing_paths: set[str] = set()

    for raw in rel_paths:
        if "*" in raw:
            continue
        if "/.../" in raw:
            continue

        for raw_clean in _expand_reference_tokens(raw):
            raw_clean = raw_clean.replace("\\", "/").strip()
            if not raw_clean or "://" in raw_clean:
                continue
            if re.match(r"^(?:/opt/|opt/|/etc/)", raw_clean, re.I):
                continue
            if raw_clean.startswith(("memory/", "vault/", "G:/", "g:/")):
                continue

            found: Path | None = None
            for cand in _candidate_paths(raw_clean):
                try:
                    cand.relative_to(repo_root)
                except ValueError:
                    continue
                if cand.is_file():
                    found = cand
                    break

            if found is not None:
                try:
                    rel_ok = str(found.relative_to(repo_root)).replace("\\", "/")
                except ValueError:
                    rel_ok = str(found)
                if raw_clean not in seen_ok_paths:
                    seen_ok_paths.add(raw_clean)
                    ok.append({"path": raw_clean, "resolved_to": rel_ok, "exists": True})
            else:
                if raw_clean not in seen_missing_paths:
                    seen_missing_paths.add(raw_clean)
                    missing.append({"path": raw_clean, "exists": False})
    return ok, missing


def build() -> int:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    central_path = WORKSPACE / CENTRAL_REL
    constitution_path = WORKSPACE / CONSTITUTION_REL

    central_text = ""
    if central_path.is_file():
        central_text = central_path.read_text(encoding="utf-8-sig")

    refs = _extract_paths_from_central(central_text)
    ok_refs, orphan_refs = _resolve_and_check(refs)
    optional_missing = [x for x in orphan_refs if Path(x["path"]).name in _OPTIONAL_REF_NAMES]
    real_orphans = [x for x in orphan_refs if Path(x["path"]).name not in _OPTIONAL_REF_NAMES]
    chk = _checkpoint_stats(central_text)

    routing_embed = _run_routing_snapshot()

    constitution_ok = constitution_path.is_file()
    central_ok = central_path.is_file()

    gc_status = "PASS"
    reasons: list[str] = []
    if not central_ok:
        gc_status = "FAIL"
        reasons.append("central_missing")
    if not constitution_ok:
        gc_status = "FAIL"
        reasons.append("constitution_missing")
    if real_orphans:
        gc_status = "WARN" if gc_status == "PASS" else gc_status
        reasons.append(f"orphan_refs:{len(real_orphans)}")
    if chk.get("bullet_line_count", 0) > 25:
        gc_status = "WARN" if gc_status == "PASS" else gc_status
        reasons.append("checkpoint_section_large")

    payload: dict[str, Any] = {
        "schema": "agent_memory_garbage_collection_v1",
        "generated_at_utc": _utc_now(),
        "status": gc_status,
        "status_reasons": reasons or ["ok"],
        "anchors": {
            "central_agent_memory": {"path": CENTRAL_REL, "exists": central_ok},
            "constitution_facts": {"path": CONSTITUTION_REL, "exists": constitution_ok},
        },
        "central_scan": {
            "referenced_paths_extracted": len(refs),
            "referenced_paths_verified_ok": len(ok_refs),
            "optional_missing_refs": optional_missing[:20],
            "orphan_or_missing_refs": real_orphans[:80],
            "checkpoint_section": chk,
        },
        "memory_pruning_routing_embed": routing_embed if "schema" in routing_embed else {"embed_error": routing_embed},
        "recommended_actions": [],
    }

    if real_orphans:
        payload["recommended_actions"].append(
            "Review CENTRAL_AGENT_MEMORY_V1.md backtick paths; remove stale pointers or fix typos."
        )
    if chk.get("bullet_line_count", 0) > 25:
        payload["recommended_actions"].append(
            "Compress ATHENA_CHECKPOINT bullets (keep newest N); archive older lines to git history only."
        )
    if not constitution_ok:
        payload["recommended_actions"].append("Restore CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md (Fact-Lock anchor).")

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = [
        "# Agent Memory Garbage Collection",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{gc_status}`",
        f"- orphan_refs: `{len(real_orphans)}`",
        f"- checkpoint_bullets: `{chk.get('bullet_line_count', 0)}`",
        "",
        "## Recommended actions",
    ]
    recs = payload["recommended_actions"]
    if recs:
        md_lines.extend(f"- {a}" for a in recs)
    else:
        md_lines.append("- None")
    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"wrote: {OUT_JSON}")
    print(f"wrote: {OUT_MD}")
    return 0 if gc_status != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(build())
