"""Path mindmap model smoke — TS SSOT + optional live bundle probe."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1K = ROOT / "projects" / "no1kmedi"
TS_SMOKE = NO1K / "scripts" / "smoke-logos-research-path-mindmap-v1.ts"
PROBE = ROOT / "scripts" / "_probe_logos_mindmap_live_v1.py"


def test_path_mindmap_ts_smoke_exit_0() -> None:
    proc = subprocess.run(
        ["npm", "run", "smoke:logos-path-mindmap"],
        cwd=str(NO1K),
        capture_output=True,
        text=True,
        check=False,
        shell=True,
    )
    assert proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
    doc = json.loads((proc.stdout or "").strip().splitlines()[-1])
    assert doc.get("ok") is True
    assert int(doc.get("nodes") or 0) >= 7


def test_path_mindmap_live_probe_optional() -> None:
    """Live probe — skip when offline; run in CI against logos.jema-ai.com via env."""
    if not PROBE.is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(PROBE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0 and "URLError" in (proc.stderr or ""):
        return
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_path_mindmap_playwright_smoke_optional() -> None:
    """Playwright E2E — skip when playwright not installed unless strict env."""
    script = NO1K / "scripts" / "smoke-logos-research-studio-mindmap-playwright-v1.mjs"
    env = {**dict(**__import__("os").environ), "LOGOS_STUDIO_SMOKE_BASE": "https://logos.jema-ai.com"}
    proc = subprocess.run(
        ["node", str(script)],
        cwd=str(NO1K),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
        env=env,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 and "playwright_not_installed" in out:
        if __import__("os").environ.get("MKM_SMOKE_STRICT_PLAYWRIGHT") == "1":
            assert False, out
        return
    assert proc.returncode == 0, out
