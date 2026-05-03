"""security_agent_manager: import + optional DPAPI round-trip (Windows only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_get_security_agent_singleton() -> None:
    from scripts.security_agent_manager import SecurityAgent, get_security_agent

    a = get_security_agent()
    b = get_security_agent()
    assert isinstance(a, SecurityAgent)
    assert a is b


@pytest.mark.skipif(os.name != "nt", reason="DPAPI store is Windows-only")
def test_dpapi_get_missing_key_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MKM_SKIP_DPAPI_SECRET_STORE", "")
    from scripts import security_agent_manager as m

    assert m._get_plain_from_dpapi_store("__unlikely_missing_key_mkm_test__") is None


@pytest.mark.skipif(os.name != "nt", reason="DPAPI store is Windows-only")
def test_dpapi_skip_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MKM_SKIP_DPAPI_SECRET_STORE", "1")
    from scripts import security_agent_manager as m

    assert m._get_plain_from_dpapi_store("ANY") is None
