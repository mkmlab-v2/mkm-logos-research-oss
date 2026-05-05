#!/usr/bin/env python3
"""MyeongriCompleteFusion(또는 commander ``full_fusion_payload``) JSON → ``myeongni_lens_advanced_input_v1``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from myeongni_lens_v1.fusion_bridge import (  # noqa: E402
    build_advanced_input_from_fusion,
    unwrap_fusion_payload,
)

from scripts.myeongri_complete_fusion import MyeongriCompleteFusion  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--fusion-json",
        type=Path,
        help="융합 dict JSON (MyeongriCompleteFusion 출력 또는 래핑 문서).",
    )
    src.add_argument(
        "--compute-birth",
        action="store_true",
        help="만세력으로 융합 즉시 계산 (아래 생년월일시 필요).",
    )
    ap.add_argument("--birth-year", type=int, default=None)
    ap.add_argument("--birth-month", type=int, default=None)
    ap.add_argument("--birth-day", type=int, default=None)
    ap.add_argument("--birth-hour", type=int, default=None)
    ap.add_argument("--is-solar", action="store_true", help="양력 입력")
    ap.add_argument("--is-male", action="store_true", help="남성(대운 방향용)")
    ap.add_argument(
        "--reference-ts-utc",
        type=str,
        default=None,
        help="advanced_input.reference_ts_utc (선택)",
    )
    ap.add_argument("--output", type=Path, default=None, help="기본: stdout만")
    ap.add_argument("--compact", action="store_true")
    args = ap.parse_args()

    fus: dict[str, Any] | None = None
    if args.compute_birth:
        for name, v in (
            ("birth_year", args.birth_year),
            ("birth_month", args.birth_month),
            ("birth_day", args.birth_day),
            ("birth_hour", args.birth_hour),
        ):
            if v is None:
                print(f"emit advanced from fusion: missing --{name.replace('_', '-')}", file=sys.stderr)
                return 2
        fus = MyeongriCompleteFusion().calculate_complete_fusion(
            args.birth_year,
            args.birth_month,
            args.birth_day,
            args.birth_hour,
            is_solar=args.is_solar,
            is_male=args.is_male,
        )
    else:
        assert args.fusion_json is not None
        if not args.fusion_json.is_file():
            print(f"not found: {args.fusion_json}", file=sys.stderr)
            return 2
        raw = _load_json(args.fusion_json)
        fus = unwrap_fusion_payload(raw)
        if fus is None:
            print(
                "could not extract fusion (expect top-level saju or full_fusion_payload).",
                file=sys.stderr,
            )
            return 2

    advanced = build_advanced_input_from_fusion(
        fus,
        reference_ts_utc=args.reference_ts_utc,
    )
    text = json.dumps(advanced, ensure_ascii=False, indent=None if args.compact else 2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
