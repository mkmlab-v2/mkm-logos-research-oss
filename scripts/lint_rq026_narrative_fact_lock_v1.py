#!/usr/bin/env python3
"""RQ-026 narrative fact-lock lint for experiments/ namespace ([HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/temperament_eval_axes_contract_v1.json"
)
DEFAULT_ROOT = ROOT / "experiments/sasang_temperament_agents_v1"
DEFAULT_OUT = ROOT / "docs/final/artifacts/rq026_narrative_lint_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scan_paths(root: Path) -> list[Path]:
    exclude = {"temperament_eval_axes_contract_v1.json"}
    out: list[Path] = []
    for pat in ("**/*.md", "specs/temperament_agent_state_v1.example.json", "specs/pathology_transition_matrix_v1*.json"):
        out.extend(
            p
            for p in root.glob(pat)
            if p.is_file() and p.name not in exclude
        )
    return sorted(set(out))


def lint(*, contract: dict[str, Any], paths: list[Path]) -> dict[str, Any]:
    phrases = list(contract.get("forbidden_narrative_phrases_ko") or [])
    hits: list[dict[str, str]] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for phrase in phrases:
            if phrase in text:
                hits.append(
                    {
                        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                        "phrase": phrase,
                    }
                )
    ok = len(hits) == 0
    return {
        "schema": "rq026_narrative_lint_v1",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-026",
        "hypothesis_tier": "B",
        "research_only": True,
        "narrative_lint_ok": ok,
        "files_scanned": len(paths),
        "forbidden_phrase_hits": hits,
        "contract_pointer": str(DEFAULT_CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "verdict_ko": "narrative lint OK" if ok else f"forbidden phrase {len(hits)}건",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    if not args.contract.is_file():
        raise SystemExit(f"missing contract: {args.contract}")
    if not args.root.is_dir():
        raise SystemExit(f"missing root: {args.root}")

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    doc = lint(contract=contract, paths=_scan_paths(args.root))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    if args.strict and not doc.get("narrative_lint_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
