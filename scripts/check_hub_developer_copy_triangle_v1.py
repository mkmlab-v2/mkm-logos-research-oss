#!/usr/bin/env python3
"""Hub developer copy triangle — benchmark · GitHub reproduce · enterprise apply.

  py scripts/check_hub_developer_copy_triangle_v1.py

Output: reports/hub_developer_copy_triangle_v1_latest.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/hub_developer_copy_triangle_v1_latest.json"

PLUGINS = ROOT / "projects/no1kmedi/src/lib/universeHubPluginsV2.ts"
DEV_PAGE = ROOT / "projects/no1kmedi/src/app/hub/developer/page.tsx"
PUBLIC_COPY = ROOT / "projects/no1kmedi/marketing-site/public-copy.json"

APPLY_PATH = "/enterprise/apply"
BENCHMARK_HOST = "a-codeai.com/benchmark"
REPRODUCE_REPO = "github.com/mkmlab-v2/a-codeai-compression-reproduce"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    checks: list[dict[str, Any]] = []
    fail = 0

    if PLUGINS.is_file():
        text = _read(PLUGINS)
        for name, needle in (
            ("plugins_benchmark", "aCodeOpenBenchBenchmark"),
            ("plugins_reproduce", REPRODUCE_REPO),
            ("plugins_apply", APPLY_PATH),
        ):
            ok = needle in text
            checks.append({"id": name, "ok": ok, "needle": needle})
            if not ok:
                fail += 1
    else:
        checks.append({"id": "plugins_file", "ok": False, "error": "missing"})
        fail += 1

    if DEV_PAGE.is_file():
        text = _read(DEV_PAGE)
        for name, needle in (
            ("dev_page_benchmark", "aCodeOpenBenchBenchmark"),
            ("dev_page_reproduce", "aCodeOpenBenchReproduce"),
            ("dev_page_apply", "compressionPilotApply"),
        ):
            ok = needle in text
            checks.append({"id": name, "ok": ok, "needle": needle})
            if not ok:
                fail += 1
    else:
        checks.append({"id": "dev_page", "ok": False, "error": "missing"})
        fail += 1

    if PUBLIC_COPY.is_file():
        data = json.loads(_read(PUBLIC_COPY))
        apply_href = (
            data.get("enterprise", {})
            .get("compression_roi", {})
            .get("apply_href")
        )
        ok = apply_href == APPLY_PATH
        checks.append({"id": "public_copy_apply_href", "ok": ok, "value": apply_href})
        if not ok:
            fail += 1
    else:
        checks.append({"id": "public_copy", "ok": False, "error": "missing"})
        fail += 1

    readme_candidates = [
        ROOT / "external_staging/a_codeai_public_reproduce/README.md",
        ROOT / "reports/a_codeai_public_reproduce_materialize_v1_latest.json",
    ]
    readme = next((p for p in readme_candidates if p.is_file()), None)
    if readme and readme.suffix == ".md":
        text = _read(readme)
        ok = "enterprise/apply" in text
        checks.append({"id": "reproduce_readme_apply_link", "ok": ok, "path": str(readme)})
        if not ok:
            fail += 1

    payload = {
        "schema": "hub_developer_copy_triangle_v1",
        "generated_at_utc": _utc(),
        "ok": fail == 0,
        "checks": checks,
        "triangle": {
            "benchmark": f"https://{BENCHMARK_HOST}/",
            "reproduce": f"https://{REPRODUCE_REPO}",
            "apply": f"https://app.jema-ai.com{APPLY_PATH}",
        },
        "reproduce": "py scripts/check_hub_developer_copy_triangle_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": payload["ok"], "fail_count": fail, "out": str(OUT)}, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
