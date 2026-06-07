#!/usr/bin/env python3
"""B-track rebuild: ETCBC DSS → 200-token metadata NDJSON pilot.

Restores 2026-03-27 frontline DSS leg without apocrypha fetch.
``--dry-run`` writes only under ``reports/tmp_dss_token_dry_run/``.

Usage (from repo root):
  py projects/dss-4d-ingest/run_dss_token_pilot.py --manifest dss_pilot_manifest_tf4.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_step(cmd: list[str], *, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_ndjson(path: Path) -> tuple[bool, str]:
    required = ("work", "token_index", "script", "lineage_tier", "source")
    forbidden = ("text", "token_text", "surface", "lemma")
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return False, "row not object"
        for key in required:
            if key not in obj:
                return False, f"missing {key}"
        for key in forbidden:
            if key in obj:
                return False, f"forbidden key {key}"
        count += 1
    if count < 1:
        return False, "empty ndjson"
    return True, f"verified {count} records"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default="dss_pilot_manifest_tf4.json")
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--force-manifest", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-ci-alias", action="store_true")
    args = ap.parse_args()

    manifest_path = ROOT / args.manifest
    if not manifest_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing manifest {manifest_path}"}), file=sys.stderr)
        return 2

    manifest = _load_json(manifest_path)
    max_tokens = args.max_tokens or int(manifest.get("max_tokens") or 200)
    dataset_version = str(manifest.get("dataset_version") or "dss-pilot-tf4")

    if args.dry_run:
        out_dir = REPO / "reports" / "tmp_dss_token_dry_run"
        out_primary = out_dir / "dss_tokens_pilot_manifest_tf4.ndjson"
        out_alias = out_dir / "dss_tokens_ci_smoke_manifest_tf4.ndjson"
    else:
        out_dir = ROOT / "outputs"
        out_primary = out_dir / Path(str(manifest.get("output_ndjson") or "outputs/dss_tokens_pilot_manifest_tf4.ndjson")).name
        out_alias = out_dir / Path(str(manifest.get("output_ci_alias") or "outputs/dss_tokens_ci_smoke_manifest_tf4.ndjson")).name

    scrolls_json = ROOT / str(manifest.get("scrolls_json") or "dss_pilot_scrolls.json")
    tf_map = ROOT / str(manifest.get("tf_feature_map") or "tf_feature_map.default.json")
    tf_loc = REPO / "data" / "etcbc-dss" / "tf" / "1.9"

    ingest_cmd = [
        sys.executable,
        str(ROOT / "ingest_etcbc_dss.py"),
        "--scrolls-json",
        str(scrolls_json),
        "--tf-feature-map",
        str(tf_map),
        "--max-tokens",
        str(max_tokens),
        "--dataset-version",
        dataset_version,
        "--out",
        str(out_primary),
    ]
    if args.force_manifest or args.dry_run:
        ingest_cmd.append("--force-manifest")
    if tf_loc.is_dir():
        ingest_cmd.extend(["--tf-loc", str(tf_loc)])

    code, out = _run_step(ingest_cmd, cwd=ROOT)
    print(out)
    if code != 0:
        return code

    ok, verify_msg = _verify_ndjson(out_primary)
    if not ok:
        print(json.dumps({"ok": False, "error": verify_msg}), file=sys.stderr)
        return 2
    print(f"OK: {verify_msg}")

    if not args.skip_ci_alias and not args.dry_run:
        out_alias.write_bytes(out_primary.read_bytes())
        print(f"aliased ci manifest → {out_alias}")

    summary = {
        "schema": "dss_token_pilot_summary_v1",
        "tag": manifest.get("tag"),
        "records": sum(1 for line in out_primary.read_text(encoding="utf-8").splitlines() if line.strip()),
        "sha256": _sha256_file(out_primary),
        "out_primary": str(out_primary),
        "out_alias": str(out_alias) if out_alias.is_file() else None,
        "dry_run": args.dry_run,
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
    }
    summary_path = out_dir / "dss_token_pilot_summary_latest.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
