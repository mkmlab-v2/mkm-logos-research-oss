# MKM Secure Agent Runtime V0.8

Bounded local-first runtime candidate for MKM's Desktop Commander-class tool layer.

## Layers

- V0: approved-root file/command primitives, Thin Coordinates, receipts
- V0.1: MCP stdio + exact one-time out-of-band HUMAN_GATE
- V0.2: deterministic privacy prefilter
- V0.3: Windows current-user DPAPI secret store
- V0.4: DPAPI-encrypted rollback snapshots
- V0.5: Windows tray approval UI + loopback-only Ollama manager
- V0.6: isolated Windows UIA Desktop Action Layer
- V0.7: process/class based App Adapter Layer
- V0.8: semantic Developer Workspace Adapter for VS Code/Cursor

## V0.8 Developer Adapter

The V0.8 developer layer is intentionally semantic. It does not accept arbitrary terminal text.

Supported semantic actions:

- `dev_workspace_status`
  - read-only Git status
  - approved workspace only
  - path-like output locally privacy-scanned
- `dev_git_diff`
  - read-only bounded Git diff
  - SECRET/PERSONAL/PHI-like output is blocked locally before MCP release
- `dev_detect_tests`
  - observes deterministic pytest markers only
  - emits only the fixed candidate profile `pytest.quiet.v0`
- `request_dev_test`
  - requests HUMAN_GATE for the exact fixed command:
    `python -m pytest -q`
  - no execution before approval
- `execute_dev_test`
  - re-validates app/workspace/profile
  - exact approval digest includes window_ref, workspace_path, adapter_id, profile_id, argv and timeout
  - test stdout/stderr is locally privacy-scanned before release

Explicitly unavailable:

- arbitrary terminal strings
- arbitrary shell
- git commit/push/pull/fetch/checkout/reset
- package installation
- deploy/SEND
- secret injection

## V0.8 app boundary

Developer tools accept only windows identified by:

- `editor.vscode.v0`
- `editor.cursor.v0`

A supplied workspace must also be inside an approved filesystem root.

Important evidence boundary:

`window_ref + workspace_path` is only a request-scoped pair.

The runtime does **not** currently prove that the observed Cursor/VS Code window has that exact workspace open. The returned state is therefore:

`REQUEST_SCOPED_PAIR_ASSOCIATION_NOT_ESTABLISHED`

No stronger association should be inferred.

## Existing V0.6/V0.7 UI boundary

- UIA runs in an isolated worker subprocess
- window titles hidden by default
- Edit/Text/Document content hidden by default
- low-risk click / clean Edit text -> HUMAN_GATE
- password/sensitive/high-risk controls -> DENY
- browsers -> OBSERVE_ONLY
- unmatched app -> OBSERVE_ONLY
- legacy generic UI mutation is denied when App Adapter Layer is active
- no arbitrary coordinates
- no raw keyboard/hotkey injection

## Current validation

- full targeted Windows suite: **80 PASS**
- V0.8 targeted developer suite: **10 PASS**
- V0.7 targeted adapter suite: 10 PASS
- MCP protocol observed: 2026-07-28
- MCP tool count observed after V0.8: **29**

V0.8 synthetic developer fixture verified:

- Git status read-only
- clean diff released
- secret-like diff blocked
- fixed pytest profile detection
- test request caused no execution before approval
- local approval -> fixed pytest execution
- approval timeout mismatch -> rejected
- unknown test profile -> rejected
- workspace outside approved root -> rejected
- no pytest marker -> NOT_ESTABLISHED

## Real Windows read-only observation

A live `cursor.exe` window was identified as:

`editor.cursor.v0`

Against the separate approved validation clone:

- Git entry count observed: 0
- window title remained hidden
- SEND remained HOLD
- tool count observed: 29
- window/workspace association: **NOT_ESTABLISHED**

No mutation was performed against the live Cursor window.

## Retained fresh failures

Previous V0.6 failures remain sealed:

1. in-process UIA COM fatal 0x8001010d -> isolated worker subprocess
2. CP949 parent decode failure on UTF-8 Korean UI JSON -> explicit UTF-8 transport
3. initial synthetic click without observable effect -> InvokePattern preferred; fresh targeted rerun passed

V0.7 also retained a Notepad launcher-PID smoke that ended NOT_FOUND; later visible Notepad identification was read-only and not claimed to be the same launcher instance.

## Evidence ceiling

`BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_8_CANDIDATE`

Still NOT_ESTABLISHED / NOT_AUTHORIZED:

- actual Cursor/VS Code window-to-workspace association
- cross-application developer reliability
- browser mutation
- password/secret UI injection
- EMR production write
- remote relay/device pairing
- PHI production use
- git push/deploy/SEND
- independent security review
- production deployment
