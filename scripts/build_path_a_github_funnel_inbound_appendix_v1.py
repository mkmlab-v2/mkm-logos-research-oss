#!/usr/bin/env python3
"""GitHub funnel / inbound appendix from Path A spine commercial defense fact sheet.

send_gate HOLD · honest product KPI only · FAIL-COMP-004 guard.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACT = ROOT / "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json"
OUT_MD = ROOT / "reports/human_paste/path_a_github_funnel_inbound_appendix_v1_latest.md"
OUT_TXT = ROOT / "reports/human_paste/path_a_github_funnel_inbound_appendix_v1_latest.txt"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_fact() -> dict[str, Any]:
    if not FACT.is_file():
        raise SystemExit(f"missing fact sheet — run: py scripts/run_path_a_spine_commercial_defense_chain_v1.py")
    return json.loads(FACT.read_text(encoding="utf-8-sig"))


def build_body(fact: dict[str, Any]) -> tuple[str, str]:
    p = fact["product_lane"]
    saving = p.get("global_token_saving_percent")
    cohort = p.get("cohort") or {}
    forbidden = fact.get("forbidden_paste_phrases") or []
    repro = (fact.get("reproduce") or {}).get("chain", "")

    md = f"""# Path A spine — GitHub funnel / inbound appendix (internal)

- **generated_at_utc:** `{_utc()}`
- **send_gate:** `HOLD` — not a production SLA or paid SKU claim
- **SSOT:** `reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json`

## Honest product KPI (paste-safe)

| Field | Value |
|-------|-------|
| Spine binary billable saving | **{saving}%** |
| Byte-exact parity | **{p.get('byte_exact_subset_parity')}** ({p.get('case_count')} cases) |
| Cohort | `{cohort.get('domain_tag')}` longform B2B copy |
| Official recon | `{ (p.get('codec') or {}).get('official_recon') }` |

Sidecar / preview layers are **NON_GATING** — not billed as official reconstruction quality.

## Do not use in public copy

"""
    for phrase in forbidden:
        md += f"- {phrase}\n"

    md += f"""
## Reproduce (Fact-Lock)

```powershell
{repro}
```

## Research lanes (reference only — do not merge into headline)

- Internal latent bench (~47% class) = B-track research, not this appendix
- Conditional fusion v3 = research_only, `beat_frozen: false`
- 25-row masked support cohort (~0.18%) = synthetic invariant check, not customer ROI
"""

    txt = f"""Path A spine — inbound / GitHub funnel (internal · HOLD)

Honest KPI: {saving}% spine binary billable · byte-exact {p.get('byte_exact_subset_parity')} · {p.get('case_count')} cases · {cohort.get('domain_tag')}

Official recon: verbatim spine decode only. Sidecar = preview, not SLA.

Forbidden in copy: latent ~47%, v3 conditional SLA, masked cohort as customer ROI, repair_v2 as core quality.

Reproduce: {repro}
"""
    return md, txt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--out-txt", type=Path, default=OUT_TXT)
    args = ap.parse_args()

    fact = _load_fact()
    md, txt = build_body(fact)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md, encoding="utf-8")
    args.out_txt.write_text(txt, encoding="utf-8")

    p = fact["product_lane"]
    ok = float(p.get("byte_exact_subset_parity") or 0) >= 1.0
    print(
        json.dumps(
            {
                "ok": ok,
                "wrote_md": str(args.out_md),
                "wrote_txt": str(args.out_txt),
                "saving_percent": p.get("global_token_saving_percent"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
