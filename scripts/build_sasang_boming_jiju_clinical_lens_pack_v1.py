#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build `sasang_boming_jiju_clinical_lens_pack_v1_latest.json` (4체질 보명지주 임상 렌즈)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.sasang_boming_jiju_clinical_lens_v1 import build_full_pack  # noqa: E402

OUT = ROOT / "docs" / "final" / "artifacts" / "sasang_boming_jiju_clinical_lens_pack_v1_latest.json"


def main() -> int:
    payload = build_full_pack()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"written={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
