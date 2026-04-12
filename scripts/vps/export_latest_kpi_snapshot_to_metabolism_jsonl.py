#!/usr/bin/env python3
"""VPS/전방 초소: 최신 KPI 스냅샷 JSONL → LOG_METABOLISM JSONL (convert_kpi 재사용).

모노레포 루트에서 실행한다. 원시 서버 로그가 아니라 collect_kpi_snapshot 산출물만 입력한다.
후방(로컬)으로 rsync할 파일 기본값: docs/final/artifacts/derived/log_metabolism_from_kpi_vps_export_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[2]


def _latest_kpi_jsonl(kpi_dir: Path) -> Path | None:
    if not kpi_dir.is_dir():
        return None
    files = sorted(
        kpi_dir.glob("kpi_snapshot_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="모노레포 루트 (기본: 이 스크립트 기준 상위 두 단계)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="LOG_METABOLISM JSONL 출력 (기본: docs/final/artifacts/derived/log_metabolism_from_kpi_vps_export_v1.jsonl)",
    )
    ap.add_argument(
        "--report",
        type=Path,
        default=None,
        help="선택: JSON 리포트 경로 (기본: docs/final/artifacts/derived/vps_kpi_metabolism_export_report_v1.json)",
    )
    args = ap.parse_args()

    root = _repo_root(args.repo_root)
    kpi_dir = root / "projects" / "bitcoin-trading" / "memory" / "kpi"
    latest = _latest_kpi_jsonl(kpi_dir)
    if latest is None:
        print(f"FAIL: no kpi_snapshot_*.jsonl under {kpi_dir}", file=sys.stderr)
        return 2

    out = args.out
    if out is None:
        out = root / "docs" / "final" / "artifacts" / "derived" / "log_metabolism_from_kpi_vps_export_v1.jsonl"
    else:
        out = Path(out)
        if not out.is_absolute():
            out = (root / out).resolve()

    convert = root / "scripts" / "convert_kpi_snapshot_to_metabolism_jsonl.py"
    if not convert.is_file():
        print(f"FAIL: missing {convert}", file=sys.stderr)
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    cp = subprocess.run(
        [sys.executable, str(convert), "--in", str(latest), "--out", str(out)],
        cwd=str(root),
    )
    if cp.returncode != 0:
        return int(cp.returncode)

    report_path = args.report
    if report_path is None:
        report_path = root / "docs" / "final" / "artifacts" / "derived" / "vps_kpi_metabolism_export_report_v1.json"
    else:
        report_path = Path(report_path)
        if not report_path.is_absolute():
            report_path = (root / report_path).resolve()

    n_lines = 0
    if out.is_file():
        n_lines = sum(1 for line in out.read_text(encoding="utf-8").splitlines() if line.strip())

    st = latest.stat()
    mtime_epoch = st.st_mtime
    mtime_iso = datetime.fromtimestamp(mtime_epoch, tz=timezone.utc).isoformat()

    rep = {
        "schema": "vps_kpi_metabolism_export_report_v1",
        "source_kpi_jsonl": str(latest).replace("\\", "/"),
        "source_mtime_epoch": mtime_epoch,
        "source_mtime_iso_utc": mtime_iso,
        "source_size_bytes": st.st_size,
        "output_metabolism_jsonl": str(out).replace("\\", "/"),
        "output_rows": n_lines,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK: {latest.name} -> {out} rows={n_lines} report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
