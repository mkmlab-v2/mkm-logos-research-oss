#!/usr/bin/env python3
"""1-minute counsel brief for Track C B2B Two-Layer meeting pack."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "reports/track_c_b2b_counsel_copy_scan_v1_latest.json"
READINESS = ROOT / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/track_c_b2b_counsel_one_minute_brief_v1_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_md() -> str:
    scan = _read(SCAN)
    readiness = _read(READINESS)
    scan_ok = scan.get("scan_ok", False)
    internal_ok = readiness.get("ready_for_internal_meeting", False)
    external_ok = readiness.get("ready_for_external_send", False)
    blocking = scan.get("blocking_files") or []
    policy_line = (
        "**External send:** commander+counsel signoff on disk · disclaimer integrity OK · "
        "CTO mail is **manual only** (`track_c_b2b_external_cto_email_draft_v1_latest.json`)."
        if external_ok
        else "**1-person policy (2026-06-07):** counsel submission shelf until commander resumes revenue lane."
    )

    return f"""# Track C B2B — Counsel 1-minute brief (INTERNAL)

**generated_at_utc:** `{_utc_now()}`  
**status:** `DRAFT_AUTO` · **NOT legal approval** · `ready_for_external_send: {str(external_ok).lower()}`

---

## What this pack is

Enterprise **Two-Layer Agent** deck + 15 min rehearsal script + redacted Logos demo + **Functional BGM PoC `[HYPO]`** (WAV in ZIP). **OEM meaning/gate plugin** — not a new OS sandbox vendor.

{policy_line}

## Pre-scan (automated)

| Check | Result |
|-------|--------|
| Copy guardrail scan | **{"PASS" if scan_ok else "FAIL"}** |
| Internal meeting readiness | **{"PASS" if internal_ok else "FAIL"}** |
| Blocking files | {", ".join(blocking) if blocking else "none"} |

## What we explicitly do NOT claim (verify)

- Track A ~47.5% / universal matrix % as headline proof
- Lossless / omniscient AI / zero hallucination
- Auto live-trading or Track A promotion from this deck
- Competitor product trash-talk (use "execution-sandbox class" only)
- Wire envelope metrics as compression KPI (see meeting pack index warning)

## Counsel questions (5 min)

1. **Investment / trading:** Footer disclaimers sufficient for CTO/CISO meeting materials?
2. **Partnership [HYPO]:** OEM module language — any implied warranty or integration commitment to tighten?
3. **Logos / biblical layer:** `[NON_GATING]` posture clear enough vs advisory/trading confusion?
4. **IP:** "Invisible core, visible evidence" — any over-disclosure in redacted demo?
5. **External send:** What must change before `ready_for_external_send` may flip true?
6. **Audio hook `[HYPO]`:** Functional BGM bullets in sweep JSON — any Suno/competitor or clinical overreach in counsel ZIP WAV appendix?

## Attachments

- ZIP: `docs/final/artifacts/track_c_b2b_counsel_export_pack_v1.zip`
- Full scan JSON: `reports/track_c_b2b_counsel_copy_scan_v1_latest.json`

## After counsel reply

```bash
py scripts/record_track_c_b2b_legal_counsel_signoff_v1.py --counsel-reference <ticket-id> --apply-scope
```

Commander sign-off (separate, does not replace counsel):

```bash
py scripts/record_track_c_b2b_commander_signoff_v1.py --reference <your-id> --scope counsel_submission
```

**boundary_ack:** Agent cannot record counsel approval; human reference required on disk.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(build_md(), encoding="utf-8")
    print(f"WROTE: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
