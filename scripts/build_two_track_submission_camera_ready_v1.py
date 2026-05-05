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


def _expanded_paragraphs(
    a: dict[str, Any], title: str, gates: dict[str, Any], falsification_snapshot: dict[str, Any], falsification_boundary_snapshot: dict[str, Any]
) -> list[str]:
    problem = str(a.get("problem", ""))
    method = str(a.get("method", ""))
    result = str(a.get("result", ""))
    boundary = str(a.get("claim_boundary", ""))
    br = gates.get("bundle_ready")
    pub = gates.get("ready_for_publication_claim")
    f_pass = int(falsification_snapshot.get("pass_count", 0) or 0)
    f_total = int(falsification_snapshot.get("total_checks", 0) or 0)
    f_status = str(falsification_snapshot.get("suite_status", "unknown"))
    bp = (
        falsification_snapshot.get("sensitivity_breakpoint")
        if isinstance(falsification_snapshot.get("sensitivity_breakpoint"), dict)
        else {}
    )
    bp_survivor = bp.get("min_survivor_count")
    bp_ci = bp.get("min_ci_low_defense_contrib")
    safe_survivor = falsification_boundary_snapshot.get("max_safe_min_survivor_count")
    break_survivor = falsification_boundary_snapshot.get("min_break_min_survivor_count")
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
            f"Falsification status: {f_pass}/{f_total} ({f_status}); "
            f"first sensitivity breakpoint at min_survivor_count={bp_survivor}, min_ci_low_defense_contrib={bp_ci}. "
            f"We emphasize interpretability of the evaluation protocol over headline alpha claims."
        ),
        (
            f"Disclosure posture: {boundary} "
            f"The paper narrative therefore focuses on safety gates, rollback contracts, and reproducible artifacts."
        ),
        (
            f"Fail-boundary disclosure: maximum safe survivor-floor observed in sensitivity grid is {safe_survivor}, "
            f"and first break condition appears at survivor-floor {break_survivor}. "
            f"We use this boundary as an explicit reviewer-facing risk condition."
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


def _compressed_abstracts(
    title: str,
    gates: dict[str, Any],
    falsification_snapshot: dict[str, Any],
    falsification_boundary_snapshot: dict[str, Any],
) -> dict[str, str]:
    br = gates.get("bundle_ready")
    pub = gates.get("ready_for_publication_claim")
    f_pass = int(falsification_snapshot.get("pass_count", 0) or 0)
    f_total = int(falsification_snapshot.get("total_checks", 0) or 0)
    bp = (
        falsification_snapshot.get("sensitivity_breakpoint")
        if isinstance(falsification_snapshot.get("sensitivity_breakpoint"), dict)
        else {}
    )
    bp_survivor = bp.get("min_survivor_count")
    bp_ci = bp.get("min_ci_low_defense_contrib")
    safe_survivor = falsification_boundary_snapshot.get("max_safe_min_survivor_count")
    break_survivor = falsification_boundary_snapshot.get("min_break_min_survivor_count")

    kdd_180 = (
        f"{title} proposes a safety-gated evaluation architecture for meaning-rich cross-reference signals that are "
        f"expressive but vulnerable to overfitting when promoted directly to trading actions. We separate K-track "
        f"(knowledge/IP narrative generation) from T-track (survivor filtering, rollback contracts, and operational gates), "
        f"and validate claims with multi-baseline comparison, raw OOS readiness checks, and bootstrap/permutation significance. "
        f"Current gate status is bundle_ready={br}, ready_for_publication_claim={pub}, with falsification pass {f_pass}/{f_total}. "
        f"Robustness sensitivity reports first non-pass at min_survivor_count={bp_survivor} and "
        f"min_ci_low_defense_contrib={bp_ci}. A fail-boundary layer defines max-safe survivor floor={safe_survivor} and first-break "
        f"threshold={break_survivor}, which is wired to an explicit no-go gate. Public disclosure remains redacted at formula/weight "
        f"level, while reproducibility is preserved through artifact-chain checkpoints."
    )
    aaai_150 = (
        f"We present a deployment-oriented governance stack for narrative-heavy inference systems. The design separates "
        f"K-track insight generation from T-track execution gating, then enforces falsification, baseline comparison, and "
        f"raw OOS readiness before any promotion claim. Current status: bundle_ready={br}, "
        f"ready_for_publication_claim={pub}, falsification={f_pass}/{f_total}. Sensitivity analysis shows the first "
        f"non-pass at survivor threshold {bp_survivor} (ci-low threshold {bp_ci}); fail-boundary control sets "
        f"max-safe survivor floor={safe_survivor} and first-break={break_survivor}, wired to rollback/no-go semantics. "
        f"Significance is computed with bootstrap mean CI and sign-flip permutation testing. The paper reports safety, "
        f"auditability, and reproducibility via artifact paths while keeping proprietary formulas redacted."
    )
    return {"kdd_180w": kdd_180, "aaai_150w": aaai_150}


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
    falsification_snapshot = (
        draft.get("falsification_snapshot") if isinstance(draft.get("falsification_snapshot"), dict) else {}
    )
    falsification_boundary_snapshot = (
        draft.get("falsification_boundary_snapshot")
        if isinstance(draft.get("falsification_boundary_snapshot"), dict)
        else {}
    )

    paragraphs = _expanded_paragraphs(
        abs_scaffold, title, gates, falsification_snapshot, falsification_boundary_snapshot
    )
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
        "compressed_abstracts_en": _compressed_abstracts(
            title, gates, falsification_snapshot, falsification_boundary_snapshot
        ),
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
                    "Include falsification sensitivity breakpoint as a robustness boundary condition.",
                    "Add fail-boundary row (max-safe threshold / first-break threshold) in rebuttal appendix.",
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
                    "State falsification pass count and sensitivity breakpoint in deployment risk narrative.",
                    "Include fail-boundary condition as explicit no-go threshold for operations.",
                ],
            },
        },
        "keywords_en": keywords,
        "public_safe_boundary": str(draft.get("public_safe_boundary", "")),
        "submission_gate_snapshot": gates,
        "falsification_snapshot": falsification_snapshot,
        "falsification_boundary_snapshot": falsification_boundary_snapshot,
    }

    out_path = _resolve(repo_root, args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
