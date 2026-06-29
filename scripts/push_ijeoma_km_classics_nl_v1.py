#!/usr/bin/env python3
"""Upload KM classics vendor texts + index to IJEOMA B-track NL notebook (paid tier)."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UUID = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
VENDOR = ROOT / "vendor/korean-medicine-texts"
INDEX = ROOT / "reports/km_classics_index_hypo_v1_latest.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_km_classics_nl_upload_v1.json"
HEADER = (
    "[HYPO] B-track KM classic · clinician_lane_only · not clinical prescription · send_gate HOLD\n\n"
)
CHUNK = 6_000


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _upload(uuid: str, title: str, text: str, sleep_s: float) -> list[dict]:
    rows: list[dict] = []
    parts = [text] if len(text) <= CHUNK else [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]
    for i, part in enumerate(parts):
        t = title if i == 0 else f"{title}__p{i}"
        cmd = ["nlm", "source", "add", uuid, "--text", part, "--title", t[:120], "--wait"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0 and "Added source" in out
        rows.append({"title": t, "ok": ok, "chars": len(part), "tail": out[-160:]})
        print(json.dumps({"title": t, "ok": ok}, ensure_ascii=False), flush=True)
        if sleep_s > 0:
            time.sleep(sleep_s)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=0.85)
    parser.add_argument("--skip-donguibogam", action="store_true")
    parser.add_argument("--skip-gyeongak", action="store_true")
    parser.add_argument("--max-parts-per-work", type=int, default=0, help="0 = unlimited")
    args = parser.parse_args()

    if not INDEX.is_file():
        print(json.dumps({"error": "missing_index", "path": str(INDEX)}))
        return 2

    index_doc = json.loads(INDEX.read_text(encoding="utf-8"))
    rows: list[dict] = []

    rows.extend(
        _upload(
            UUID,
            "km_classics_index_hypo_v1",
            HEADER + INDEX.read_text(encoding="utf-8"),
            args.sleep,
        )
    )

    mirror = ROOT / "reports/km_classics_vendor_mirror_v1_latest.json"
    if mirror.is_file():
        rows.extend(
            _upload(UUID, "km_classics_vendor_mirror_report", HEADER + mirror.read_text(encoding="utf-8"), args.sleep)
        )

    geukchigo_note = (
        HEADER
        + "# 격치고(格致藁) · 천유초 — 입수 상태\n\n"
        + "- workspace inventory: `data/corpus/ijeoma/_inventory/IJEOMA_CORPUS_INVENTORY_2026-03-28.json` → **not_found_in_scanned_paths**\n"
        + "- 이제마 동의수세보원은 `canon_section_*` + chunk batches로 커버됨.\n"
        + "- 격치고 원전 확보 전까지 NL은 **인용 위조 금지**; 질의 10번은 외부 원전 필요로 표기.\n"
    )
    rows.extend(_upload(UUID, "IJEOMA_GEUKCHIGO_PLACEHOLDER_v1", geukchigo_note, args.sleep))

    order = ["huangdineijingsuwen", "huangdineijinglingshu", "donguibogam", "gyeongakjeonseo"]
    skip = set()
    if args.skip_donguibogam:
        skip.add("donguibogam")
    if args.skip_gyeongak:
        skip.add("gyeongakjeonseo")

    for entry in index_doc.get("entries", []):
        sid = entry.get("source_id")
        if sid in skip:
            continue
        if sid not in order:
            continue
        rel = entry.get("relative_path")
        if not rel:
            continue
        path = VENDOR / rel.replace("/", "\\")
        if not path.is_file():
            rows.append({"title": sid, "ok": False, "error": f"missing:{path}"})
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        prefix = f"# {entry.get('work')} ({entry.get('title_hanja')})\n# source_id={sid}\n# vendor_path={rel}\n\n"
        rows.extend(_upload(UUID, f"km_vendor_{sid}", HEADER + prefix + body, args.sleep))

    doc = {
        "schema": "comp_ijeoma_km_classics_nl_upload_v1",
        "generated_at_utc": _utc(),
        "notebook_uuid": UUID,
        "ok": sum(1 for r in rows if r.get("ok")),
        "fail": sum(1 for r in rows if not r.get("ok")),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "ok": doc["ok"], "fail": doc["fail"]}, ensure_ascii=False))
    return 0 if doc["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
