#!/usr/bin/env python3
"""[HYPO] Prism Index pinset swap — max 3 pointer entries per turn (B-track)."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_REGISTRY = ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"
DEFAULT_CONTRACT = ROOT / "experiments/no_guard_limit_test/prism_pinset_swap_contract_v1.json"
DEFAULT_OUT = ROOT / "experiments/no_guard_limit_test/results/prism_pinset_swap_latest.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]+")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text) if len(t) >= 2}


def _score_entry(
    entry: dict[str, Any],
    *,
    profile: dict[str, Any],
    context_tokens: set[str],
    lane_hint: str = "",
    selection_mode: str = "context_scored",
) -> float:
    axis = str(entry.get("prism_axis") or "")
    allowed = set(profile.get("allowed_axes") or [])
    if axis not in allowed:
        return -1.0

    path = str(entry.get("path") or "").lower()
    summary = str(entry.get("summary_ko") or "").lower()
    eid = str(entry.get("id") or "").lower()
    blob = f"{path} {summary} {eid}"

    score = 0.0
    if axis == "S":
        score += 2.0
    elif axis == "K":
        score += 1.5

    path_boost = profile.get("path_boost_if_contains") or {}
    if isinstance(path_boost, dict):
        for needle, boost in path_boost.items():
            if needle.lower() in path:
                score += float(boost)

    path_penalty = profile.get("path_penalty_if_contains") or {}
    if isinstance(path_penalty, dict):
        for needle, pen in path_penalty.items():
            if needle.lower() in path:
                score -= float(pen)

    preferred = profile.get("preferred_entry_ids") or []
    suppress_pref = bool(profile.get("suppress_preferred_in_context_scored"))
    if (
        isinstance(preferred, list)
        and str(entry.get("id") or "") in preferred
        and not (selection_mode == "context_scored" and suppress_pref)
    ):
        score += 5.0

    id_prefix_boost = profile.get("id_boost_if_prefix") or {}
    if isinstance(id_prefix_boost, dict):
        eid_str = str(entry.get("id") or "")
        for prefix, boost in id_prefix_boost.items():
            if eid_str.startswith(str(prefix)):
                score += float(boost)

    lane_boost = profile.get("lane_boost") or {}
    if lane_hint and isinstance(lane_boost, dict):
        lane_rules = lane_boost.get(lane_hint)
        if isinstance(lane_rules, dict):
            needles = lane_rules.get("path_contains") or []
            boost = float(lane_rules.get("boost") or 0)
            if isinstance(needles, list) and boost:
                for needle in needles:
                    if str(needle).lower() in path:
                        score += boost
                        break

    for tok in context_tokens:
        if tok in blob:
            score += 1.0

    access = str(entry.get("agent_access") or "")
    if access == "read_only_strict":
        score += 0.5
    if access == "b_track_only":
        score += 0.25

    return score


def select_pinset(
    *,
    registry_path: Path,
    contract_path: Path,
    task_profile: str,
    context_text: str = "",
    file_hint: str = "",
    max_entries: int | None = None,
    selection_mode: str = "context_scored",
) -> dict[str, Any]:
    registry = _load_json(registry_path)
    contract = _load_json(contract_path)
    profiles = contract.get("task_profiles") or {}
    profile = profiles.get(task_profile)
    if not isinstance(profile, dict):
        raise ValueError(f"unknown task_profile: {task_profile}")

    cap = int(max_entries if max_entries is not None else contract.get("max_entries_per_turn", 3))
    cap = max(1, min(cap, 10))

    ctx = f"{context_text} {file_hint}".strip()
    context_tokens = _tokenize(ctx)
    for kw in profile.get("context_keywords") or []:
        if isinstance(kw, str):
            context_tokens.add(kw.lower())

    entries = registry.get("entries") or []
    by_id = {str(ent.get("id")): ent for ent in entries if isinstance(ent, dict) and ent.get("id")}

    if selection_mode == "fixed_preferred":
        preferred = profile.get("preferred_entry_ids") or []
        picked: list[dict[str, Any]] = []
        if isinstance(preferred, list):
            for pid in preferred:
                ent = by_id.get(str(pid))
                if ent and str(ent.get("prism_axis") or "") in set(profile.get("allowed_axes") or []):
                    picked.append(ent)
                if len(picked) >= cap:
                    break
        if not picked:
            selection_mode = "context_scored"
        else:
            scored = [(0.0, ent) for ent in picked]
    else:
        scored = []
        for ent in entries:
            if not isinstance(ent, dict):
                continue
            s = _score_entry(
                ent,
                profile=profile,
                context_tokens=context_tokens,
                lane_hint=file_hint,
                selection_mode=selection_mode,
            )
            if s >= 0:
                scored.append((s, ent))
        scored.sort(key=lambda x: (-x[0], str(x[1].get("id") or "")))
        picked = [ent for _, ent in scored[:cap]]

    return {
        "schema": "prism_pinset_swap_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "task_profile": task_profile,
        "selection_mode": selection_mode,
        "max_entries": cap,
        "context_token_sample": sorted(context_tokens)[:24],
        "entries": [
            {
                "id": ent.get("id"),
                "path": ent.get("path"),
                "prism_axis": ent.get("prism_axis"),
                "summary_ko": ent.get("summary_ko"),
                "agent_access": ent.get("agent_access"),
            }
            for ent in picked
        ],
        "boundary_ack": "Pointer-only; no full file bodies.",
    }


def format_pinset_block(pinset: dict[str, Any]) -> str:
    lines = ["[PRISM_PINSET v1 · research_only · max 3]"]
    for ent in pinset.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        eid = ent.get("id") or "?"
        path = ent.get("path") or "?"
        summary = ent.get("summary_ko") or ""
        lines.append(f"- {eid} | {path} | {summary}")
    return "\n".join(lines) + "\n\n"


def estimate_pinset_tokens(block: str) -> int:
    return len(TOKEN_RE.findall(block))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Prism Index pinset swap (B-track).")
    ap.add_argument("--task-profile", default="py_coding")
    ap.add_argument("--context-text", default="")
    ap.add_argument("--file-hint", default="")
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--print-block", action="store_true")
    ap.add_argument(
        "--selection-mode",
        default="context_scored",
        choices=("context_scored", "fixed_preferred"),
    )
    args = ap.parse_args()

    registry = Path(args.registry)
    contract = Path(args.contract)
    if not registry.is_absolute():
        registry = ROOT / registry
    if not contract.is_absolute():
        contract = ROOT / contract

    pinset = select_pinset(
        registry_path=registry,
        contract_path=contract,
        task_profile=args.task_profile,
        context_text=args.context_text,
        file_hint=args.file_hint,
        selection_mode=args.selection_mode,
    )
    block = format_pinset_block(pinset)
    pinset["formatted_block"] = block
    pinset["estimated_pinset_tokens"] = estimate_pinset_tokens(block)

    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pinset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    if args.print_block:
        print(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
