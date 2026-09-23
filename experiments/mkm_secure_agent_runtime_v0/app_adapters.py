"""Declarative App Adapter Layer for MKM Secure Agent Runtime V0.7.

Adapters identify applications from non-content metadata (process/class), never
from window titles. They narrow capabilities; they never widen the underlying
Desktop Action Layer policy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable

from desktop_ui import DesktopActionLayer, DesktopUIError
from ui_refs import UIRefStore, UIRefError


class AppAdapterError(RuntimeError):
    pass


OBSERVE = "OBSERVE"
CLICK_LOW_RISK = "CLICK_LOW_RISK"
SET_TEXT_CLEAN = "SET_TEXT_CLEAN"
_ALLOWED_CAPABILITIES = {OBSERVE, CLICK_LOW_RISK, SET_TEXT_CLEAN}


@dataclass(frozen=True)
class AdapterSpec:
    adapter_id: str
    display_name: str
    process_names: tuple[str, ...]
    class_name_patterns: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = (OBSERVE,)
    risk_class: str = "BOUNDED"
    enabled: bool = True
    notes: str = ""

    def validate(self) -> None:
        if not self.adapter_id or any(ch.isspace() for ch in self.adapter_id):
            raise AppAdapterError("invalid adapter_id")
        if not self.process_names:
            raise AppAdapterError("adapter requires process_names")
        if not set(self.capabilities) <= _ALLOWED_CAPABILITIES:
            raise AppAdapterError("adapter has unknown capability")
        for pattern in self.class_name_patterns:
            re.compile(pattern)


@dataclass(frozen=True)
class AdapterMatch:
    adapter_id: str
    display_name: str
    capabilities: tuple[str, ...]
    risk_class: str
    matched: bool
    reason: str
    notes: str


def builtin_adapter_specs() -> list[AdapterSpec]:
    """Conservative built-ins. Browsers remain observe-only in V0.7."""
    return [
        AdapterSpec(
            adapter_id="windows.notepad.v0",
            display_name="Windows Notepad",
            process_names=("notepad.exe",),
            capabilities=(OBSERVE, CLICK_LOW_RISK, SET_TEXT_CLEAN),
            risk_class="BOUNDED_LOCAL_EDITOR",
            notes="No secret/password injection; high-risk labels remain denied.",
        ),
        AdapterSpec(
            adapter_id="editor.vscode.v0",
            display_name="Visual Studio Code",
            process_names=("code.exe",),
            capabilities=(OBSERVE, CLICK_LOW_RISK, SET_TEXT_CLEAN),
            risk_class="BOUNDED_DEVELOPER_TOOL",
            notes="No terminal typing, git push, deploy, SEND, or secrets.",
        ),
        AdapterSpec(
            adapter_id="editor.cursor.v0",
            display_name="Cursor",
            process_names=("cursor.exe",),
            capabilities=(OBSERVE, CLICK_LOW_RISK, SET_TEXT_CLEAN),
            risk_class="BOUNDED_DEVELOPER_TOOL",
            notes="No terminal typing, git push, deploy, SEND, or secrets.",
        ),
        AdapterSpec(
            adapter_id="browser.chromium.observe.v0",
            display_name="Chromium Browser Observe-Only",
            process_names=("chrome.exe", "msedge.exe", "brave.exe"),
            capabilities=(OBSERVE,),
            risk_class="OBSERVE_ONLY_BROWSER",
            notes="Mutation disabled in V0.7.",
        ),
        AdapterSpec(
            adapter_id="browser.firefox.observe.v0",
            display_name="Firefox Observe-Only",
            process_names=("firefox.exe",),
            capabilities=(OBSERVE,),
            risk_class="OBSERVE_ONLY_BROWSER",
            notes="Mutation disabled in V0.7.",
        ),
        AdapterSpec(
            adapter_id="windows.explorer.observe.v0",
            display_name="Windows Explorer Observe-Only",
            process_names=("explorer.exe",),
            capabilities=(OBSERVE,),
            risk_class="OBSERVE_ONLY_FILE_MANAGER",
            notes="File-manager mutation disabled in V0.7.",
        ),
    ]


class AppAdapterRegistry:
    def __init__(self, specs: Iterable[AdapterSpec] | None = None):
        self.specs = list(specs if specs is not None else builtin_adapter_specs())
        ids = set()
        for spec in self.specs:
            spec.validate()
            if spec.adapter_id in ids:
                raise AppAdapterError(f"duplicate adapter_id: {spec.adapter_id}")
            ids.add(spec.adapter_id)

    @staticmethod
    def _matches(spec: AdapterSpec, summary: dict[str, Any]) -> bool:
        if not spec.enabled:
            return False
        process_name = str(summary.get("process_name") or "").lower()
        if process_name not in {x.lower() for x in spec.process_names}:
            return False
        if not spec.class_name_patterns:
            return True
        class_name = str(summary.get("class_name") or "")
        return any(re.search(pattern, class_name) for pattern in spec.class_name_patterns)

    def identify_summary(self, summary: dict[str, Any]) -> AdapterMatch:
        matches = [spec for spec in self.specs if self._matches(spec, summary)]
        if not matches:
            return AdapterMatch(
                adapter_id="unmatched.observe-only",
                display_name="Unmatched Application",
                capabilities=(OBSERVE,),
                risk_class="OBSERVE_ONLY_UNMATCHED",
                matched=False,
                reason="NO_ENABLED_ADAPTER_MATCH",
                notes="Mutation is disabled until an explicit adapter exists.",
            )
        if len(matches) != 1:
            raise AppAdapterError(
                "adapter match is ambiguous: " + ",".join(x.adapter_id for x in matches)
            )
        spec = matches[0]
        return AdapterMatch(
            adapter_id=spec.adapter_id,
            display_name=spec.display_name,
            capabilities=spec.capabilities,
            risk_class=spec.risk_class,
            matched=True,
            reason="EXACT_PROCESS_CLASS_MATCH",
            notes=spec.notes,
        )


class AppAdapterLayer:
    def __init__(
        self,
        desktop: DesktopActionLayer,
        ui_refs: UIRefStore,
        registry: AppAdapterRegistry | None = None,
    ):
        self.desktop = desktop
        self.ui_refs = ui_refs
        self.registry = registry or AppAdapterRegistry()

    def identify_window(self, window_ref: str) -> dict[str, Any]:
        payload = self.ui_refs.resolve(window_ref, expected_kind="window")
        summary = payload["summary"]
        match = self.registry.identify_summary(summary)
        return {
            "window_ref": window_ref,
            "adapter": asdict(match),
            "process_name": summary.get("process_name"),
            "class_name": summary.get("class_name"),
            "window_title": summary.get("title"),
        }

    def inspect_window(self, window_ref: str, *, max_controls: int = 100) -> dict[str, Any]:
        identity = self.identify_window(window_ref)
        observed = self.desktop.inspect_window(window_ref, max_controls=max_controls)
        caps = set(identity["adapter"]["capabilities"])
        controls = []
        for item in observed["controls"]:
            controls.append({
                **item,
                "adapter_capabilities": sorted(caps),
                "mutation_available": bool(
                    CLICK_LOW_RISK in caps or SET_TEXT_CLEAN in caps
                ),
            })
        return {
            "window_ref": window_ref,
            "adapter": identity["adapter"],
            "control_count": observed["control_count"],
            "controls": controls,
            "truncated": observed["truncated"],
        }

    def _binding(self, window_ref: str, control_ref: str) -> tuple[dict[str, Any], dict[str, Any], AdapterMatch]:
        window = self.ui_refs.resolve(window_ref, expected_kind="window")
        control = self.ui_refs.resolve(control_ref, expected_kind="control")
        ws = window["selector"]
        cs = control["selector"]
        if int(ws["top_handle"]) != int(cs["top_handle"]):
            raise AppAdapterError("control does not belong to window_ref")
        if int(ws["process_id"]) != int(cs["process_id"]):
            raise AppAdapterError("control process does not match window_ref")
        match = self.registry.identify_summary(window["summary"])
        return window, control, match

    def require_capability(
        self,
        window_ref: str,
        control_ref: str,
        capability: str,
    ) -> AdapterMatch:
        if capability not in _ALLOWED_CAPABILITIES:
            raise AppAdapterError("unknown capability")
        _window, _control, match = self._binding(window_ref, control_ref)
        if capability not in set(match.capabilities):
            raise AppAdapterError(
                f"adapter capability denied: {match.adapter_id} lacks {capability}"
            )
        return match

    def app_policy(
        self,
        window_ref: str,
        control_ref: str,
        *,
        action: str,
        text: str | None = None,
    ) -> dict[str, Any]:
        capability = CLICK_LOW_RISK if action == "click" else SET_TEXT_CLEAN
        try:
            match = self.require_capability(window_ref, control_ref, capability)
        except AppAdapterError as exc:
            return {
                "decision": "DENY",
                "reason": str(exc),
                "adapter_id": self.identify_window(window_ref)["adapter"]["adapter_id"],
            }
        base = self.desktop.action_policy(control_ref, action=action, text=text)
        return {
            **base,
            "adapter_id": match.adapter_id,
            "adapter_capability": capability,
        }
