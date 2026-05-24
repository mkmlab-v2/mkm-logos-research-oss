#!/usr/bin/env python3
"""Build 1-slide exec summary + redacted Logos demo excerpt for B2B calls (DRAFT)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _redact_paths(text: str) -> str:
    text = re.sub(r"[A-Za-z]:\\[^\s`\"']+", "[REDACTED_PATH]", text)
    text = re.sub(
        r"(?:docs|reports|projects|scripts|memory|data)/[^\s`\"']+",
        "[REDACTED_ARTIFACT_SLOT]",
        text,
    )
    return text


def _redact_customer_demo(text: str) -> str:
    """Strip internal paths and identifiable corpus anchors for live-call excerpt."""
    text = _redact_paths(text)
    text = re.sub(r"\b(?:sample|verse|node)[-_][\w.-]+", "[REDACTED_NODE]", text, flags=re.I)
    text = re.sub(r"aramaic::[\w.]+", "[CORPUS_NODE]", text)
    text = re.sub(r"sha256:[a-f0-9]{32,}", lambda m: _redact_hash(m.group(0)), text, flags=re.I)
    return text


def _redact_hash(value: str, keep: int = 12) -> str:
    s = str(value).strip()
    if s.startswith("sha256:"):
        body = s[7:]
        return f"sha256:{body[:keep]}…"
    if len(s) > keep + 3:
        return f"{s[:keep]}…"
    return s


def _exec_summary_slide(*, generated_at: str, bundle: dict[str, Any] | None) -> str:
    smoke_note = ""
    if bundle:
        unc = bundle.get("uncertainty") if isinstance(bundle.get("uncertainty"), dict) else {}
        smoke_note = (
            f"Latest bundle snapshot: `non_gating=True`, "
            f"`uncertainty_band={unc.get('uncertainty_band', 'n/a')}` — illustrative only."
        )
    return f"""# MKM — Macro-Risk Intelligence Brief (1 slide · DRAFT)

**For:** C-level / risk committee · first 5 minutes · **not for external send until legal sign-off**

| | |
|---|---|
| **What we sell** | Enterprise **macro early-warning** (§3.8) + **Logos Observatory** (graph-native scripture intelligence · visual reasoning trace) — decision-support surfaces only |
| **Product demo (Logos)** | https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1 — `[HYPO]` · NON_GATING · not trade signals |
| **What we do NOT sell** | Prophecy, religious instruction, trade signals, return guarantees, “AI predicts markets” |
| **How it works** | **Field** (macro/regime context) → **Lenses** (사상 / 명리 / Logos `[NON_GATING]`) → **Conflict map** → **Operator posture** (HOLD/REDUCE/WATCH) — not buy/sell |
| **Proof model** | Reproducible JSON artifacts + audit logs; core formulas stay server-side (§9A) |
| **Bundle** | Macro subscription + Logos premium module — **not** a standalone holy-text signal product |

**One line (EN):** *Governance-driven macro risk scenarios with artifact-backed evidence — decision support only.*

**한 줄 (KO):** *거시 리스크 시나리오·운영자 포즈를 아티팩트 근거로 제공하는 의사결정 보조 — 투자자문·매매 지시 아님.*

{smoke_note}

- **generated_at_utc:** `{generated_at}` · **status:** `DRAFT_AUTO` · Full offer: `track_c_combined_b2b_offer_onepager_v1_latest.md`
"""


def _redacted_demo(
    *,
    generated_at: str,
    bundle: dict[str, Any] | None,
    commander: dict[str, Any] | None,
) -> str:
    lines: list[str] = []
    lines.append("# Logos Deep Narrative — Redacted Demo Excerpt (DRAFT)")
    lines.append("")
    lines.append(
        f"- **generated_at_utc:** `{generated_at}` · **purpose:** live call / NDA room — "
        "**paths, repo roots, and full hashes redacted**"
    )
    lines.append("- **status:** `DRAFT_AUTO` — legal review before customer distribution")
    lines.append("")

    lines.append("## A. Insight bundle (sanitized snapshot)")
    if not bundle:
        lines.append("_Bundle artifact not found — run `build_logos_insight_bundle_v1.py`._")
    else:
        pol = bundle.get("policy") if isinstance(bundle.get("policy"), dict) else {}
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| schema | `{bundle.get('schema', 'n/a')}` |")
        lines.append(f"| generated_at_utc | `{bundle.get('generated_at_utc', 'n/a')}` |")
        lines.append(f"| research_only | `{pol.get('research_only')}` |")
        lines.append(f"| non_gating | `{pol.get('non_gating')}` |")
        lines.append(f"| hypothesis_tier | `{bundle.get('hypothesis_tier', 'n/a')}` |")
        lines.append(f"| degraded | `{bundle.get('degraded')}` |")
        gating = bundle.get("gating") if isinstance(bundle.get("gating"), dict) else {}
        lines.append(f"| gating.pastoral_and_trading | `{gating.get('pastoral_and_trading')}` |")
        unc = bundle.get("uncertainty") if isinstance(bundle.get("uncertainty"), dict) else {}
        lines.append(
            f"| uncertainty | band=`{unc.get('uncertainty_band')}`, "
            f"unknown_fraction=`{unc.get('unknown_fraction_0_1')}` |"
        )
        q = bundle.get("query") if isinstance(bundle.get("query"), dict) else {}
        if q.get("query_fingerprint"):
            lines.append(f"| query_fingerprint | `{_redact_hash(q['query_fingerprint'])}` |")

        agg = bundle.get("aggregation") if isinstance(bundle.get("aggregation"), dict) else {}
        morph = agg.get("morphology_summary") if isinstance(agg.get("morphology_summary"), dict) else {}
        if morph:
            lines.append(
                f"| morphology (aggregate) | coverage≈`{morph.get('coverage_ratio_0_1')}`, "
                f"matched_atoms=`{morph.get('matched_hebrew_atoms')}` |"
            )
        sem = agg.get("semantic_edge_quality_digest")
        if isinstance(sem, dict):
            lines.append(
                f"| semantic edges (aggregate) | count=`{sem.get('edge_count')}`, "
                f"overlap_mean≈`{sem.get('semantic_overlap_mean')}` |"
            )
        top = []
        ic = agg.get("insight_candidates_digest")
        if isinstance(ic, dict) and isinstance(ic.get("top"), list):
            top = ic["top"][:5]
        if top:
            lines.append("")
            lines.append("**Top insight candidates (anonymized nodes):**")
            lines.append("")
            lines.append("| rank | regime_tag | hub_score | path_score |")
            lines.append("|------|------------|-----------|------------|")
            for row in top:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"| {row.get('rank')} | `{row.get('regime_tag')}` | "
                    f"{row.get('hub_score')} | {row.get('path_score')} |"
                )
        audit = bundle.get("audit") if isinstance(bundle.get("audit"), dict) else {}
        if audit.get("inputs_hash"):
            lines.append("")
            lines.append(f"- inputs_hash: `{_redact_hash(audit['inputs_hash'])}`")
        lines.append("")
        lines.append(
            "> **Demo note:** Corpus node IDs and upstream file lists are omitted. "
            "Full reproducibility is available under contract + NDA."
        )

    lines.append("")
    lines.append("## B. Commander deep report — 5-axis skeleton (sanitized)")
    if not commander:
        lines.append("_Commander JSON not found — run `run_logos_track_b_commander_deep_report_v1.py`._")
    else:
        ts = commander.get("generated_at_utc") or commander.get("ts_utc") or "n/a"
        lines.append(f"- schema: `{commander.get('schema')}` · snapshot_utc: `{ts}`")
        lines.append(f"- labels: `{', '.join(commander.get('labels', []))}`")
        gate = commander.get("human_commander_gate_v1")
        if isinstance(gate, dict) and gate.get("banner_ko"):
            lines.append(f"- banner: {gate['banner_ko']}")
        env = commander.get("envelope")
        if isinstance(env, dict) and env.get("disclaimer_ko"):
            lines.append(f"- disclaimer: {env['disclaimer_ko']}")
        axes = commander.get("report_axes_v1")
        if isinstance(axes, dict):
            lines.append("")
            lines.append("| Axis | Excerpt (HYPO / observational) |")
            lines.append("|------|--------------------------------|")
            for key, val in axes.items():
                if not isinstance(val, dict):
                    continue
                title = val.get("title_ko", key)
                stub = str(val.get("deterministic_stub_ko", "")).strip()
                stub = _redact_customer_demo(stub)
                if len(stub) > 160:
                    stub = stub[:157] + "…"
                lines.append(f"| {title} | {stub} |")
        lines.append("")
        lines.append(
            "**Redacted:** `inputs_digest` paths, manifest pointers, verse_id lists, "
            "and fusion/market lens file locations."
        )

    lines.append("")
    lines.append("## C. Fixed disclaimer (paste under any slide)")
    lines.append("")
    lines.append(
        "> MKM provides governance-driven risk warning and scenario posture support. "
        "Not investment advice; no buy/sell instructions; no return guarantees. "
        "Logos/classical-corpus layer is `[NON_GATING]` explanatory depth only."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = _root()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bundle = _load_json(root / "docs/final/artifacts/logos_insight_bundle_v1_latest.json")
    commander = _load_json(root / "docs/final/artifacts/logos_track_b_commander_deep_report_latest.json")

    slide = _exec_summary_slide(generated_at=generated_at, bundle=bundle)
    demo = _redacted_demo(generated_at=generated_at, bundle=bundle, commander=commander)

    slide_path = root / "docs/final/artifacts/track_c_logos_b2b_exec_summary_slide_v1_latest.md"
    demo_path = root / "docs/final/artifacts/track_c_logos_redacted_demo_excerpt_v1_latest.md"

    if args.dry_run:
        print(slide_path, demo_path)
        return 0

    slide_path.parent.mkdir(parents=True, exist_ok=True)
    slide_path.write_text(slide, encoding="utf-8", newline="\n")
    demo_path.write_text(demo, encoding="utf-8", newline="\n")
    print(f"WROTE: {slide_path}")
    print(f"WROTE: {demo_path}")
    return 0 if bundle else 1


if __name__ == "__main__":
    raise SystemExit(main())
