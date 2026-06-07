#!/usr/bin/env python3
"""One-shot: rebuild Track C B2B meeting pack (one-pagers, slide, redacted demo, index)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(py: str, script: str, extra: list[str] | None = None) -> int:
    cmd = [py, str(_root() / script), *(extra or [])]
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=_root(), check=False).returncode


def _exists(root: Path, rel: str) -> bool:
    return (root / rel).is_file()


def _build_index(*, generated_at: str, steps: list[tuple[str, int]]) -> str:
    artifacts = [
        ("1 · Open (5 min)", "docs/final/artifacts/track_c_logos_b2b_exec_summary_slide_v1_latest.md"),
        ("2 · Proof (10 min)", "docs/final/artifacts/track_c_logos_redacted_demo_excerpt_v1_latest.md"),
        ("3 · Macro offer", "docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md"),
        ("4 · Logos module", "docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md"),
        ("5 · Combined", "docs/final/artifacts/track_c_combined_b2b_offer_onepager_v1_latest.md"),
        ("6 · H2 MVP", "docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md"),
        ("7 · Logos appendix", "docs/final/artifacts/track_c_b2b_logos_lens_appendix_v1_latest.md"),
        ("8 · Compression plugin IR", "docs/final/artifacts/track_c_b2b_compression_plugin_appendix_v1_latest.md"),
        ("9 · Audio hook PoC `[HYPO]`", "docs/final/artifacts/dynamic_bgm_melody_chain_demo_v1_latest.json"),
    ]
    rows = []
    for label, path in artifacts:
        ok = _exists(_root(), path)
        rows.append(f"| {label} | `{path}` | {'OK' if ok else 'MISSING'} |")
    step_lines = "\n".join(f"- `{name}` → exit {code}" for name, code in steps)
    return f"""# Track C B2B — Meeting Pack Index (auto)

- **generated_at_utc:** `{generated_at}`
- **status:** `DRAFT_AUTO` — legal sign-off before external send or PDF export
- **reading_order:** slide → redacted demo → combined offer (deep dive)

## Build steps (this run)

{step_lines}

## Artifacts

| Step | Path | Disk |
|------|------|------|
{chr(10).join(rows)}

### Audio hook (B-track · internal deck only · `[HYPO]`)

- **PoC chain:** `py scripts/run_dynamic_bgm_melody_chain_v1.py`
- **HP sweep:** `py scripts/run_dynamic_bgm_hp_sweep_v1.py` → `dynamic_bgm_hp_sweep_v1_latest.json`
- **Counsel pack:** included in `track_c_b2b_counsel_export_pack_v1.zip` when manifest rebuilt
- **Not** Suno competitor claim · legal send **HOLD**

## Public demo URLs (pointers only · no performance claims)

| Surface | URL | Notes |
|---------|-----|-------|
| Risk topology radar (Phase 2.1–2.2) | https://jemaai.cloud/public_showroom_topology_radar_v1.html | Canonical static · `api.jemaai.cloud` mirror via nginx snippet |
| Meaning topology graph (capped subgraph) | https://jemaai.cloud/public_showroom_meaning_topology_graph_v1.html | `bible_meaning_graph` slice · hub labels · `[HYPO]` |
| Minimal public board | https://api.jemaai.cloud/public_showroom_board_minimal.html | Hub CTA default · `public_event_v1` poll |
| Logos research slice (full) | https://jemaai.cloud/public_showroom_logos_research_v1.html | `[HYPO]` snapshot · not live trading |
| **Logos Observatory (Track C product)** | https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1 | Visual path · chronology rail · **NON_GATING** |
| Logos Trace API (health) | https://api.jemaai.cloud/v1/logos/health | Deterministic stub · no live LLM |
| Wire audit PoC (static JSON) | `docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json` | B-track · `[HYPO]` · v6 panel reads `showroom_logos_graph_wire_rag_poc_v1.json` |
| Public Event API | https://api.jemaai.cloud/api/public-events/latest | API SSOT only (not static HTML) |

**Wire metrics (internal B2B only · not MS FinOps claims):** use `wire.honest_metrics.payload_savings_ratio` (~71% wire vs naive verse-id JSON) and `governance_overhead_factor` (~2.4× envelope vs naive). Do **not** label 2.42× as “compression” or paste into MS RQ-019 wire decks.

**5-min showroom demo script:** `docs/final/artifacts/track_c_showroom_topology_sales_demo_script_v1_latest.md`

Screenshots: capture locally after `sync_showroom_to_vps.ps1` (**do not** use `-RefreshStaging` — resets graph slice). Do not embed win rates or path leaks in decks.

## Regenerate

```powershell
py scripts/build_track_c_b2b_meeting_pack_v1.py
```

## Disclaimers (paste on every deck)

> Not investment advice. No buy/sell instructions. Logos layer `[NON_GATING]`. Core formulas not disclosed (§9A).
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print plan only.")
    parser.add_argument(
        "--skip-commander",
        action="store_true",
        help="Skip Logos commander chain (faster).",
    )
    parser.add_argument(
        "--include-track-b-pipeline",
        action="store_true",
        help="Run run_logos_track_b_pipeline_chain_v1.py (slices 3–5 + ANN lite) before pack.",
    )
    args = parser.parse_args()

    root = _root()
    py = sys.executable
    scripts = [
        ("macro_mvp", "scripts/build_track_c_macro_risk_mvp_filled_v1.py", []),
        ("logos_corpus_manifest", "scripts/build_logos_corpus_manifest_v1.py", []),
        ("logos_corpus_graph_bundle", "scripts/build_logos_corpus_graph_bundle_v1.py", []),
        ("logos_showroom_slice", "scripts/build_showroom_logos_research_slice_v1.py", []),
        ("logos_b2b_appendix", "scripts/build_logos_b2b_appendix_v1.py", []),
        ("logos_onepager", "scripts/build_track_c_logos_b2b_offer_onepager_v1.py", []),
        ("combined", "scripts/build_track_c_combined_b2b_offer_onepager_v1.py", ["--skip-rebuild"]),
        ("sales_collateral", "scripts/build_track_c_logos_b2b_sales_collateral_v1.py", []),
        ("compression_appendix", "scripts/build_track_c_compression_b2b_appendix_v1.py", []),
    ]
    if args.include_track_b_pipeline:
        scripts.insert(
            0,
            (
                "logos_track_b_pipeline",
                "scripts/run_logos_track_b_pipeline_chain_v1.py",
                ["--include-ann-lite"],
            ),
        )
    if not args.skip_commander:
        scripts.insert(
            0,
            ("commander", "scripts/run_logos_track_b_commander_deep_report_v1.py", []),
        )

    if args.dry_run:
        for name, script, extra in scripts:
            print(name, script, extra)
        return 0

    steps: list[tuple[str, int]] = []
    worst = 0
    for name, script, extra in scripts:
        code = _run(py, script, extra)
        steps.append((name, code))
        if code != 0:
            worst = code

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    index_path = root / "docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md"
    index_path.write_text(_build_index(generated_at=generated_at, steps=steps), encoding="utf-8", newline="\n")
    print(f"WROTE: {index_path}")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
