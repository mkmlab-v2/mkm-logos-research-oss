"""Path → active plugin id (mirror TS contract)."""

from __future__ import annotations


def active_plugin_id_from_path(pathname: str) -> str | None:
    path = pathname.rstrip("/") or "/hub"
    if path == "/hub":
        return "discover"
    if path.startswith("/hub/customize"):
        return "governed_customization"
    if path.startswith("/hub/oracle"):
        return "oracle_observatory"
    if path.startswith("/hub/life"):
        return "mkm_life"
    if path.startswith("/hub/developer"):
        return "a_code_sandbox"
    if path.startswith("/hub/reports"):
        return "my_reports"
    if path.startswith("/hub/operator"):
        return "operator_wtt"
    if path.startswith("/clinician"):
        return "clinician"
    return None


def test_hub_paths():
    assert active_plugin_id_from_path("/hub") == "discover"
    assert active_plugin_id_from_path("/hub/customize") == "governed_customization"
    assert active_plugin_id_from_path("/hub/oracle") == "oracle_observatory"
    assert active_plugin_id_from_path("/clinician") == "clinician"
