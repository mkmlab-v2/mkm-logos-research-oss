#!/usr/bin/env python3
"""Combine Track C macro alert + Logos deep narrative B2B one-pagers into one file."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_or_placeholder(path: Path, title: str) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return f"_(Missing: `{path.relative_to(_root()).as_posix()}` — run builder for {title}.)_\n"


def _build_combined(
    *, generated_at: str, macro_md: str, logos_md: str, compression_md: str
) -> str:
    return f"""# Track C — Combined B2B Offer (Macro + Logos + Compression Plugin IR)

- **generated_at_utc:** `{generated_at}`
- **status:** `DRAFT_AUTO` — **legal review required before external send**
- **parts:** Macro §3.8 · Logos deep narrative · Compression plugin scalability (zone shards)

---

# Part A — Macro Early Warning (§3.8)

{macro_md}

---

# Part B — Logos Deep Risk Narrative (premium module)

{logos_md}

---

# Part C — Compression Plugin Scalability (Track A OEM hook)

{compression_md}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-rebuild",
        action="store_true",
        help="Do not run child builders; only merge existing latest files.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = _root()
    py = sys.executable
    if not args.skip_rebuild:
        for script in (
            "scripts/build_track_c_macro_risk_mvp_filled_v1.py",
            "scripts/build_track_c_logos_b2b_offer_onepager_v1.py",
            "scripts/build_track_c_compression_b2b_appendix_v1.py",
        ):
            rc = subprocess.run([py, str(root / script)], cwd=root, check=False)
            if rc.returncode != 0:
                print(f"WARN: {script} exited {rc.returncode}")

    macro_path = root / "docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md"
    logos_path = root / "docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md"
    compression_path = (
        root / "docs/final/artifacts/track_c_b2b_compression_plugin_appendix_v1_latest.md"
    )
    out_path = root / "docs/final/artifacts/track_c_combined_b2b_offer_onepager_v1_latest.md"

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    combined = _build_combined(
        generated_at=generated_at,
        macro_md=_read_or_placeholder(macro_path, "macro"),
        logos_md=_read_or_placeholder(logos_path, "logos"),
        compression_md=_read_or_placeholder(compression_path, "compression appendix"),
    )

    if args.dry_run:
        print(f"Would write: {out_path} ({len(combined)} chars)")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(combined, encoding="utf-8", newline="\n")
    print(f"WROTE: {out_path}")
    missing = [p for p in (macro_path, logos_path, compression_path) if not p.is_file()]
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
