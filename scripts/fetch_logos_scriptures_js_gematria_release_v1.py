#!/usr/bin/env python3
"""Fetch scriptures-js ecosystem lexicon + license bundle [HYPO].

Downloads STEP Bible lexicon JSON (CC-BY-4.0 data) and upstream LICENSE files.
Code stack: metaxiamultimedia/scriptures-js (MIT) + scriptures-js-core (MIT).
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / "storage/external_kg/scriptures_js_v1"
DEFAULT_REPORT = ROOT / "reports/logos_scriptures_js_gematria_fetch_v1_latest.json"

SCRIPTURES_JS_REPO = "metaxiamultimedia/scriptures-js"
SCRIPTURES_CORE_REPO = "metaxiamultimedia/scriptures-js-core"
LEXICON_REPO = "metaxiamultimedia/scriptures-js-source-stepbible-lexicon"
BRANCH = "main"

LEXICON_ASSETS = (
    "data/stepbible-tbesh.json",
    "data/stepbible-tbesg.json",
    "data/stepbible-tflsj.json",
)
LICENSE_ASSETS = (
    (SCRIPTURES_JS_REPO, "LICENSE", "scriptures-js_LICENSE"),
    (SCRIPTURES_CORE_REPO, "LICENSE", "scriptures-js-core_LICENSE"),
    (LEXICON_REPO, "LICENSE", "stepbible-lexicon_LICENSE"),
    (LEXICON_REPO, "README.md", "stepbible-lexicon_README.md"),
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _download(url: str, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-logos-scriptures-js-fetch-v1"})
    with urllib.request.urlopen(req, timeout=600) as resp, dest.open("wb") as out:
        out.write(resp.read())
    return {"url": url, "path": _rel(dest), "bytes": dest.stat().st_size, "ok": dest.is_file()}


def fetch_scriptures_js(
    dest: Path,
    *,
    skip_download: bool = False,
    skip_tflsj: bool = False,
) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    lexicon_dir = dest / "lexicon"
    license_dir = dest / "licenses"
    lexicon_dir.mkdir(parents=True, exist_ok=True)
    license_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []

    assets = list(LEXICON_ASSETS)
    if skip_tflsj:
        assets = [a for a in assets if "tflsj" not in a]

    if not skip_download:
        for rel_path in assets:
            url = f"https://raw.githubusercontent.com/{LEXICON_REPO}/{BRANCH}/{rel_path}"
            out = lexicon_dir / rel_path.split("/")[-1]
            try:
                row = _download(url, out)
                row["asset"] = rel_path
                row["ok"] = out.is_file() and out.stat().st_size > 0
                steps.append(row)
            except OSError as exc:
                steps.append({"asset": rel_path, "ok": False, "error": str(exc)})

        for repo, rel_path, local_name in LICENSE_ASSETS:
            url = f"https://raw.githubusercontent.com/{repo}/{BRANCH}/{rel_path}"
            out = license_dir / local_name
            try:
                row = _download(url, out)
                row["asset"] = f"{repo}/{rel_path}"
                row["ok"] = out.is_file() and out.stat().st_size > 0
                steps.append(row)
            except OSError as exc:
                steps.append({"asset": f"{repo}/{rel_path}", "ok": False, "error": str(exc)})

    systems_doc = {
        "schema": "logos_scriptures_js_gematria_systems_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "upstream_core": f"https://github.com/{SCRIPTURES_CORE_REPO}",
        "hebrew_methods": ["mispar_hechrachi", "mispar_katan", "mispar_siduri"],
        "greek_methods": ["isopsephy_standard", "isopsephy_ordinal", "isopsephy_reduced"],
        "operational_4d_ssot": "gematria_bridge_v1 S-L-K-M",
        "license_notes": {
            "code": "MIT (scriptures-js + scriptures-js-core)",
            "lexicon_data": "CC-BY-4.0 (STEPBible via stepbible-lexicon package)",
        },
    }
    systems_path = dest / "gematria_systems_v1.json"
    systems_path.write_text(json.dumps(systems_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    files: dict[str, dict] = {}
    for name in ("stepbible-tbesh.json", "stepbible-tbesg.json", "stepbible-tflsj.json"):
        p = lexicon_dir / name
        files[name] = {"path": _rel(p), "exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else 0}

    required = ("stepbible-tbesh.json", "stepbible-tbesg.json")
    if not skip_tflsj:
        required = (*required, "stepbible-tflsj.json")
    license_ok = (license_dir / "stepbible-lexicon_LICENSE").is_file()
    ok = license_ok and all(files[n]["exists"] for n in required)

    return {
        "schema": "logos_scriptures_js_gematria_fetch_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "repos": {
            "scriptures_js": SCRIPTURES_JS_REPO,
            "scriptures_core": SCRIPTURES_CORE_REPO,
            "stepbible_lexicon": LEXICON_REPO,
        },
        "branch": BRANCH,
        "license_hint": "MIT code + CC-BY-4.0 STEPBible lexicon data — verify upstream LICENSE",
        "dest_dir": _rel(dest),
        "lexicon_dir": _rel(lexicon_dir),
        "skip_tflsj": skip_tflsj,
        "steps": steps,
        "files": files,
        "gematria_systems": _rel(systems_path),
        "ok": ok,
        "reproduce": f"py scripts/fetch_logos_scriptures_js_gematria_release_v1.py --dest {dest.as_posix()}",
        "next": (
            "py scripts/ingest_logos_scriptures_js_gematria_lexicon_v1.py "
            f"--scriptures-js-dir {_rel(dest)} --ack-license-verify-upstream"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--skip-tflsj", action="store_true", help="Omit large TFLSJ lexicon download")
    args = ap.parse_args()

    doc = fetch_scriptures_js(args.dest, skip_download=args.skip_download, skip_tflsj=args.skip_tflsj)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(args.report), "dest": str(args.dest)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
