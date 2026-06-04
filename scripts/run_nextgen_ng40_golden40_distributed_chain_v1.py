#!/usr/bin/env python3
"""[HYPO] Golden-40 2-shard chain: main shard-0 + aux job drop + merge."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "experiments/nextgen_clean_slate_cpu_v1/results"
AUX_SHARE = Path("Z:/nextgen_cpu_aux")
SHARD0 = RESULTS / "ng40_golden40_shard0_v1_latest.json"
SHARD1 = RESULTS / "ng40_golden40_shard1_v1_latest.json"
SHARD1_AUX = AUX_SHARE / "ng40_golden40_shard1_v1_latest.json"
MERGED = RESULTS / "ng40_golden40_merged_v1_latest.json"
MANIFEST = RESULTS / "ng40_golden40_distributed_manifest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str]) -> int:
    cmd = [sys.executable, str(ROOT / script), *extra]
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--local-both-shards",
        action="store_true",
        help="Run shard-1 on main too (merge path smoke; not true aux compute)",
    )
    ap.add_argument("--skip-shard0", action="store_true")
    ap.add_argument("--share-root", type=Path, default=AUX_SHARE)
    ap.add_argument(
        "--staging-merge-local-shard1",
        action="store_true",
        help="If aux shard1 missing, merge with local results/ng40_golden40_shard1 (labeled staging)",
    )
    ap.add_argument(
        "--publish-local-shard1-to-share",
        action="store_true",
        help="Copy local shard1 JSON+report to share (path test only; not aux compute)",
    )
    args = ap.parse_args()

    common = [
        "--match-active-caps",
        "--shard-count",
        "2",
    ]
    rc = 0
    if not args.skip_shard0:
        rc = _run(
            "scripts/run_nextgen_ng40_golden40_shard_eval_v1.py",
            ["--shard-index", "0", "--out-json", str(SHARD0), *common],
        )
        if rc:
            return rc

    job = {
        "schema": "ng40_golden40_aux_shard_job_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "aux_cmd": (
            "cd /d C:\\workspace && py scripts/run_nextgen_ng40_golden40_shard_eval_v1.py "
            "--shard-index 1 --shard-count 2 --match-active-caps "
            f"--out-json {args.share_root / 'ng40_golden40_shard1_v1_latest.json'}"
        ),
        "aux_cmd_share_only": (
            f"Z:\\nextgen_cpu_aux\\RUN_NG40_SHARD_ON_AUX.cmd "
            f"(requires C:\\workspace on aux)"
        ),
        "expected_out": str(args.share_root / "ng40_golden40_shard1_v1_latest.json"),
    }
    if args.share_root.parent.exists():
        args.share_root.mkdir(parents=True, exist_ok=True)
        (args.share_root / "ng40_shard_job_v1_latest.json").write_text(
            json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    published_from_main = False
    if args.publish_local_shard1_to_share and SHARD1.is_file() and args.share_root.parent.exists():
        args.share_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SHARD1, args.share_root / "ng40_golden40_shard1_v1_latest.json")
        rep = SHARD1.with_suffix(".report.json")
        if rep.is_file():
            shutil.copy2(rep, args.share_root / "ng40_golden40_shard1_v1_latest.report.json")
        (args.share_root / "ng40_shard1_publish_from_main_v1.json").write_text(
            json.dumps(
                {
                    "schema": "ng40_shard1_publish_from_main_v1",
                    "published_at_utc": _utc(),
                    "source": str(SHARD1),
                    "not_aux_compute": True,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        published_from_main = True

    shard1_path: Path = SHARD1
    shard1_source = "unknown"
    if args.local_both_shards:
        shard1_source = "local_both_shards"
        rc = _run(
            "scripts/run_nextgen_ng40_golden40_shard_eval_v1.py",
            ["--shard-index", "1", "--out-json", str(SHARD1), *common],
        )
        if rc:
            return rc
    elif SHARD1_AUX.is_file():
        shard1_path = SHARD1_AUX
        shard1_source = (
            "aux_share_publish_from_main"
            if published_from_main
            else "aux_share"
        )
    elif args.staging_merge_local_shard1 and SHARD1.is_file():
        shard1_path = SHARD1
        shard1_source = "staging_local_shard1_not_aux"
    else:
        MANIFEST.write_text(
            json.dumps(
                {
                    **job,
                    "status": "awaiting_aux_shard1",
                    "main_shard0": str(SHARD0.relative_to(ROOT)).replace("\\", "/"),
                    "readiness_pointer": (
                        "experiments/nextgen_clean_slate_cpu_v1/results/"
                        "ng40_golden40_distributed_readiness_v1_latest.json"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": "awaiting_aux_shard1",
                    "wrote_manifest": str(MANIFEST),
                    "hint": "Aux: RUN_NG40_SHARD_ON_AUX.cmd on Z:\\nextgen_cpu_aux, then re-run",
                    "or_staging": "--staging-merge-local-shard1 if local shard1 smoke exists",
                },
                ensure_ascii=False,
            )
        )
        return 0

    rc = _run(
        "scripts/merge_nextgen_ng40_golden40_shards_v1.py",
        [str(SHARD0), str(shard1_path), "--out-json", str(MERGED)],
    )
    if rc:
        return rc

    merged = json.loads(MERGED.read_text(encoding="utf-8-sig"))
    MANIFEST.write_text(
        json.dumps(
            {
                "schema": "ng40_golden40_distributed_manifest_v1",
                "generated_at_utc": _utc(),
                "shard0": str(SHARD0),
                "shard1": str(shard1_path),
                "merged": str(MERGED),
                "local_both_shards": args.local_both_shards,
                "shard1_source": shard1_source,
                "true_aux_compute": shard1_source == "aux_share",
                "publish_local_shard1_to_share": published_from_main,
                "beat_check": merged.get("beat_check"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"merged": str(MERGED), "beat_frozen": merged.get("beat_check", {}).get("beat_frozen")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
