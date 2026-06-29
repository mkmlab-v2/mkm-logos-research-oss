"""mkmlife design kernel v1 — myeongni accent extension wire."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE = ROOT / "projects/mkm/mkm-life"
KERNEL_PUBLIC = MKMLIFE / "public/data/sasang_design_primitive_kernel_v1.json"
ORB_CSS_MAP = ROOT / "docs/final/artifacts/mkm_orb_design_kernel_css_map_v1_latest.json"
FAMILY_ENVELOPE = MKMLIFE / "public/data/family_anchor_sphere_envelope_v1.json"
LIB = MKMLIFE / "lib/mkmlifeDesignKernelV1.ts"
ORB_CSS_LIB = MKMLIFE / "lib/mkmlifeOrbKernelCssV1.ts"
CORE = MKMLIFE / "lib/mkmlifeDesignKernelCoreV1.ts"
API = MKMLIFE / "app/api/v1/design-kernel/accent/route.ts"
PROVIDER = MKMLIFE / "components/shell/MkmlifeDesignKernelProvider.tsx"
LAYOUT = MKMLIFE / "app/layout.tsx"
GLOBALS = MKMLIFE / "app/globals.css"
CHECK = ROOT / "scripts/check_mkmlife_design_kernel_v1.py"

FORBIDDEN_RESPONSE_SUBSTRINGS = ["%", "운세", "일운", "명리", "태양인", "오행"]


def test_mkmlife_kernel_public_and_depth() -> None:
    assert KERNEL_PUBLIC.is_file()
    doc = json.loads(KERNEL_PUBLIC.read_text(encoding="utf-8"))
    row = doc["product_depth"]["mkmlife.com"]
    assert "myeongni" in row["extensions"]
    assert "pathology" in row["primitives"]


def test_mkmlife_kernel_lib_api_provider_wired() -> None:
    lib = LIB.read_text(encoding="utf-8")
    assert "resolveMkmlifeDesignKernel" in lib
    assert "orb_accent_hex" in lib
    assert "inferDominantOhaeng" in lib
    assert "envelopeToContextBlob" in lib
    assert ORB_CSS_LIB.is_file()
    assert "orbKernelCssFromResolved" in ORB_CSS_LIB.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")
    assert "resolveMkmlifeDesignKernel" in api
    assert "orb_accent_hex" in api
    assert "pulse_period_ms" in api
    provider = PROVIDER.read_text(encoding="utf-8")
    assert "/api/v1/design-kernel/accent" in provider
    assert "mkmlife-design-kernel-v1" in provider
    assert "--orb-accent" in provider
    assert "--orb-pulse-period-ms" in provider
    assert "MkmlifeDesignKernelProvider" in LAYOUT.read_text(encoding="utf-8")
    css = GLOBALS.read_text(encoding="utf-8")
    assert "--orb-pulse-period-ms" in css
    assert "var(--orb-ray-pulse-period-ms" in css


def test_orb_kernel_css_map_artifact() -> None:
    assert ORB_CSS_MAP.is_file()
    doc = json.loads(ORB_CSS_MAP.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_orb_design_kernel_css_map_v1"
    fields = {m["kernel_field"] for m in doc["mappings"]}
    assert "pulse_period_ms" in fields
    assert "intensity_budget" in fields
    assert doc["fail_safe"]["orb_accent_hex"] == "#2dd4bf"


def test_family_envelope_has_myeongni_context_for_fire_accent() -> None:
    env = json.loads(FAMILY_ENVELOPE.read_text(encoding="utf-8"))
    blob = json.dumps(env, ensure_ascii=False)
    assert "丙午" in blob or "병오" in blob
    myeongni = env.get("lenses", {}).get("myeongni", {})
    assert myeongni.get("body_ko")


def test_check_mkmlife_design_kernel_script_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
