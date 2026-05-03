#!/usr/bin/env python3
"""만세력 봇 → 완전 융합 JSON → 명리 독립 렌즈 v1 원클릭 체인 (B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_BOT_OUT = ART / "manseryeok_bot_chain_latest.json"
DEFAULT_FUSION_OUT = ART / "myeongri_complete_fusion_from_bot_chain_latest.json"
# 체인 기본값은 v1 전용 파일로 두어 `myeongni_independent_lens_latest.json`(v0 체크인 호환)과 충돌하지 않게 함.
DEFAULT_LENS_OUT = ART / "myeongni_independent_lens_from_chain_latest.json"

_DEMO_PROFILE: dict[str, Any] = {
    "name": "chain_demo_smoke",
    "sex": "female",
    "analysis_depth": "basic",
    "place": "ladakh",
    "local": {"year": 2021, "month": 1, "day": 5, "hour": 19, "minute": 0},
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--profile-json", type=Path, help="run_manseryeok_bot_v1 입력 프로필")
    src.add_argument("--fusion-json", type=Path, help="봇 생략: 기존 MyeongriCompleteFusion dict JSON")
    src.add_argument(
        "--demo-smoke",
        action="store_true",
        help="내장 데모 프로필로 스모크만 (저장소 회귀과 동일 ladakh 케이스)",
    )
    ap.add_argument("--bot-out", type=Path, default=DEFAULT_BOT_OUT)
    ap.add_argument("--fusion-out", type=Path, default=DEFAULT_FUSION_OUT)
    ap.add_argument("--lens-out", type=Path, default=DEFAULT_LENS_OUT)
    ap.add_argument("--compact", action="store_true", help="봇·융합 JSON 들여쓰기 생략")
    args = ap.parse_args()

    py = sys.executable
    bot = ROOT / "scripts" / "run_manseryeok_bot_v1.py"
    lens = ROOT / "scripts" / "run_lens_myeongni.py"

    fusion_path: Path
    if args.fusion_json is not None:
        fusion_path = args.fusion_json
        if not fusion_path.is_file():
            print(f"chain: fusion file not found: {fusion_path}", file=sys.stderr)
            return 2
    else:
        if args.demo_smoke:
            profile_path = Path(tempfile.mkdtemp(prefix="myeongni_chain_")) / "profile.json"
            profile_path.write_text(
                json.dumps(_DEMO_PROFILE, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        else:
            profile_path = args.profile_json
            assert profile_path is not None
            if not profile_path.is_file():
                print(f"chain: profile not found: {profile_path}", file=sys.stderr)
                return 2

        fusion_path = args.fusion_out
        bot_cmd = [
            py,
            str(bot),
            "--profile-json",
            str(profile_path),
            "--out",
            str(args.bot_out),
            "--write-complete-fusion-json",
            str(fusion_path),
        ]
        if args.compact:
            bot_cmd.append("--compact")
        r = subprocess.run(bot_cmd, cwd=str(ROOT), capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr or r.stdout, file=sys.stderr)
            return r.returncode

    lens_cmd = [
        py,
        str(lens),
        "--emit-schema",
        "v1",
        "--advanced-from-fusion-json",
        str(fusion_path),
        "--allow-fallback",
        "--output",
        str(args.lens_out),
    ]
    r2 = subprocess.run(lens_cmd, cwd=str(ROOT), capture_output=True, text=True)
    if r2.returncode != 0:
        print(r2.stderr or r2.stdout, file=sys.stderr)
        return r2.returncode

    print(f"CHAIN_OK bot_out={args.bot_out if not args.fusion_json else '(skipped)'}")
    print(f"CHAIN_OK fusion={fusion_path.resolve()}")
    print(f"CHAIN_OK lens={args.lens_out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
