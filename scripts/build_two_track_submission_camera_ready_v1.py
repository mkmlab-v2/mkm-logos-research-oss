# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.75, L:0.9, K:0.85, M:0.75}
# Balance: 90
# Purpose: Expand submission draft into venue-style camera-ready abstract + outline JSON.
# Keywords: submission, camera-ready, KDD, AAAI, public-safe
#!/usr/bin/env python3
"""Build camera-ready expanded abstract + detailed outlines per venue from submission draft."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def _resolve(root: Path, path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = root / p
    return p


def _expanded_paragraphs(a: dict[str, Any], title: str, gates: dict[str, Any]) -> list[str]:
    problem = str(a.get("problem", ""))
    method = str(a.get("method", ""))
    result = str(a.get("result", ""))
    boundary = str(a.get("claim_boundary", ""))
    br = gates.get("bundle_ready")
    pub = gates.get("ready_for_publication_claim")
    return [
        (
            f"This work addresses a governance problem in systems that derive dense, meaning-rich signals "
            f"from cross-reference style knowledge networks. {problem} "
            f"We frame this as a promotion problem: narrative insight must be separated from operational claims."
        ),
        (
            f"Our contribution is an engineering architecture and evaluation stack rather than a closed-form "
            f"market oracle. {method} "
            f"The stack is designed to be auditable: falsification checks, multi-baseline comparisons, and "
            f"bootstrap/permutation significance sit alongside explicit disclosure boundaries."
        ),
        (
            f"Empirically, we report pipeline outputs consistent with the current evidence bundle and readiness gate. "
            f"{result} "
            f"Evidence-bundle status: bundle_ready={br}, ready_for_publication_claim={pub}. "
            f"We emphasize interpretability of the evaluation protocol over headline alpha claims."
        ),
        (
            f"Disclosure posture: {boundary} "
            f"The paper narrative therefore focuses on safety gates, rollback contracts, and reproducible artifacts."
        ),
        (
            f"Title for submission packaging: \"{title}\". "
            f"Limitations include domain-specific semantics and the need for extended drift windows; "
            f"we outline replication steps via referenced JSON artifacts rather than proprietary tuning tables."
        ),
    ]


def _outline_kdd() -> list[dict[str, Any]]:
    return [
        {
            "section": "1. Introduction",
            "pages_hint": "1.0–1.5",
            "subsections": [
                "Motivation: meaning-network signals vs trading promotion risk",
                "Contributions: two-track split, falsification-first evaluation, public-safe disclosure",
            ],
        },
        {
            "section": "2. Problem Setting & Threat Model",
            "pages_hint": "0.75–1.0",
            "subsections": [
                "Overfitting and false discovery when narrative insight meets execution",
                "Rollback and survivorship as first-class requirements",
            ],
        },
        {
            "section": "3. Two-Track Architecture",
            "pages_hint": "1.25–1.75",
            "subsections": [
                "K-track: knowledge / narrative layer (not a trading trigger)",
                "T-track: survivor filter, dynamic caps, operational gates",
            ],
        },
        {
            "section": "4. Experimental Protocol",
            "pages_hint": "1.0–1.5",
            "subsections": [
                "Raw OOS ingestion policy and audit linkage",
                "Baselines and ablations",
                "Bootstrap / permutation significance and baseline-specific tuning",
            ],
        },
        {
            "section": "5. Results & Evidence Bundle",
            "pages_hint": "1.0–1.5",
            "subsections": [
                "Benchmark comparison summary",
                "Significance and readiness gates",
                "Public-safe report highlights",
            ],
        },
        {
            "section": "6. Governance, Ethics, Limitations",
            "pages_hint": "0.5–1.0",
            "subsections": [
                "What we do not claim (causal alpha, guaranteed returns)",
                "Replication contract via artifact paths",
            ],
        },
    ]


def _outline_aaai() -> list[dict[str, Any]]:
    return [
        {
            "section": "1. Industry context",
            "pages_hint": "1",
            "subsections": [
                "Why LLM-era systems need promotion gates for narrative-heavy signals",
                "Stakeholders: research, compliance, product",
            ],
        },
        {
            "section": "2. System architecture",
            "pages_hint": "1.5–2",
            "subsections": [
                "Two-track separation (K vs T)",
                "Artifact chain from graph signals to statistical gates",
            ],
        },
        {
            "section": "3. Evaluation & falsification",
            "pages_hint": "1.5–2",
            "subsections": [
                "Multi-baseline benchmark",
                "Raw OOS readiness",
                "Falsification suite and rollback semantics",
            ],
        },
        {
            "section": "4. Deployment lessons",
            "pages_hint": "0.5–1",
            "subsections": [
                "Public-safe vs proprietary boundary",
                "Operational monitoring (drift, audit accumulation)",
            ],
        },
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build camera-ready submission JSON from draft.")
    ap.add_argument("--repo-root", default=str(ROOT))
    ap.add_argument(
        "--draft-json",
        default="docs/final/artifacts/two_track_submission_draft_latest.json",
    )
    ap.add_argument("--output-json", default="docs/final/artifacts/two_track_submission_camera_ready_latest.json")
    args = ap.parse_args()

    repo_root = Path(args.repo_root)
    if not repo_root.is_absolute():
        repo_root = ROOT / repo_root
    repo_root = repo_root.resolve()

    draft_path = _resolve(repo_root, args.draft_json)
    if not draft_path.is_file():
        raise SystemExit(f"missing draft json: {draft_path}")

    draft = _load(draft_path)
    abs_scaffold = draft.get("abstract_scaffold_en") if isinstance(draft.get("abstract_scaffold_en"), dict) else {}
    title = str(draft.get("recommended_title", "Two-track safety-gated inference"))
    gates = draft.get("submission_gate_snapshot") if isinstance(draft.get("submission_gate_snapshot"), dict) else {}

    paragraphs = _expanded_paragraphs(abs_scaffold, title, gates)
    word_count_hint = sum(len(p.split()) for p in paragraphs)

    keywords = [
        "safety-gated inference",
        "two-track evaluation",
        "falsification",
        "bootstrap significance",
        "public-safe disclosure",
        "survivor filter",
        "meaning graph",
    ]

    out_doc: dict[str, Any] = {
        "schema": "two_track_submission_camera_ready_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "source": {"draft_json": str(draft_path)},
        "recommended_title_en": title,
        "expanded_abstract_en": {
            "paragraphs": paragraphs,
            "approx_word_count": word_count_hint,
            "note": "Expand or trim to venue word limit; content stays public-safe by design.",
        },
        "venues": {
            "kdd_applied_data_science": {
                "venue_label": "KDD Applied Data Science / similar applied ML track",
                "typical_constraints": {
                    "abstract_words": "150–200 (short paper) or per CFP",
                    "paper_pages": "4–9 including refs (varies by year)",
                },
                "detailed_outline_en": _outline_kdd(),
                "formatting_notes_en": [
                    "Lead with problem + evaluation protocol, not proprietary formulas.",
                    "Use tables pointing to artifact schema names, not internal weight vectors.",
                ],
            },
            "aaai_industry_track": {
                "venue_label": "AAAI Industry / deployment-oriented track (CFP-dependent)",
                "typical_constraints": {
                    "abstract_words": "per CFP",
                    "paper_pages": "varies; often shorter industry format",
                },
                "detailed_outline_en": _outline_aaai(),
                "formatting_notes_en": [
                    "Stress governance, rollback, and stakeholder-facing disclosure.",
                    "Keep replication story at artifact + script path level.",
                ],
            },
        },
        "keywords_en": keywords,
        "public_safe_boundary": str(draft.get("public_safe_boundary", "")),
        "submission_gate_snapshot": gates,
    }

    out_path = _resolve(repo_root, args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
