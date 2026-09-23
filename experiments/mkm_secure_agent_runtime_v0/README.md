# MKM Secure Agent Runtime V0.7

Bounded local-first runtime candidate for MKM's Desktop Commander-class tool layer.

## Implemented

### V0 core
- approved-root path policy
- bounded file/command primitives
- HUMAN_GATE on mutations
- argv-only subprocess execution
- Thin Coordinates + JSONL receipts
- SEND remains HOLD

### V0.1 MCP
- MCP Python SDK v2 stdio server
- exact one-time out-of-band approval broker
- model cannot self-assert human approval

### V0.2 privacy gate
- deterministic local secret/direct-identifier prefilter
- SECRET -> DENY
- PERSONAL / PHI -> HOLD
- person-name detection NOT_ESTABLISHED

### V0.3 secret broker
- Windows current-user DPAPI secret store
- MCP exposes metadata only, never decrypted secret material

### V0.4 rollback
- DPAPI-encrypted pre-write snapshots
- rollback remains local CLI only

### V0.5 local tray UI / Ollama
- Approve once / Deny local tray surface
- loopback-only Ollama lifecycle manager

### V0.6 Desktop Action Layer
- Windows UI Automation using pywinauto UIA
- all UIA work isolated in a separate worker subprocess
- opaque expiring UI refs
- window titles hidden by default
- content-bearing Edit/Text/Document strings hidden by default
- low-risk click / clean Edit text -> HUMAN_GATE
- password fields, sensitive text, high-risk labels -> DENY
- no arbitrary coordinates or raw keyboard sequences

### V0.7 App Adapter Layer
- application identity uses process/class metadata, never window title content
- adapters narrow capabilities; they never widen Desktop Action Layer policy
- unmatched application -> OBSERVE_ONLY
- ambiguous adapter match -> fail closed
- browser adapters -> OBSERVE_ONLY
- Windows Explorer adapter -> OBSERVE_ONLY
- Notepad / VS Code / Cursor adapters -> bounded click/edit candidates
- control ref must belong to the same window ref / process
- approval digest binds window_ref + control_ref + adapter_id + UI fingerprint + action
- when V0.7 is active, legacy V0.6 generic UI mutation requests are DENIED with APP_ADAPTER_REQUIRED
- mutation must use adapter-scoped app_* tools
- high-risk Desktop policy remains authoritative after adapter match

## Builtin V0.7 adapters

- `windows.notepad.v0`
  - process: `notepad.exe`
  - capabilities: OBSERVE, CLICK_LOW_RISK, SET_TEXT_CLEAN
- `editor.vscode.v0`
  - process: `code.exe`
  - capabilities: OBSERVE, CLICK_LOW_RISK, SET_TEXT_CLEAN
- `editor.cursor.v0`
  - process: `cursor.exe`
  - capabilities: OBSERVE, CLICK_LOW_RISK, SET_TEXT_CLEAN
- `browser.chromium.observe.v0`
  - chrome / msedge / brave
  - OBSERVE only
- `browser.firefox.observe.v0`
  - firefox
  - OBSERVE only
- `windows.explorer.observe.v0`
  - explorer
  - OBSERVE only

These builtins are conservative candidates, not claims of general app compatibility.

## MCP tool surface

Core / local AI:
- `runtime_status`
- `list_directory`
- `secret_handle_info`
- `read_text_file`
- `privacy_scan_file`
- `thin_coordinate`
- `request_write_text`
- `execute_write_text`
- `request_command`
- `execute_command`
- `ollama_health`
- `ollama_generate`

Raw UI observation / legacy mutation surface:
- `ui_list_windows`
- `ui_inspect_window`
- `request_ui_click`
- `execute_ui_click`
- `request_ui_set_text`
- `execute_ui_set_text`

When App Adapter Layer is active, the four legacy mutation tools are denied.

Adapter-scoped V0.7 surface:
- `app_identify_window`
- `app_inspect_window`
- `request_app_click`
- `execute_app_click`
- `request_app_set_text`
- `execute_app_set_text`

## Current validation

- full targeted Windows suite: **70 PASS**
- V0.7 adapter suite: **10 PASS**
- MCP protocol observed: 2026-07-28
- V0.6 final MCP tool count: 18
- V0.7 adds 6 app-scoped tools
- synthetic WinForms adapter:
  - identify -> fixture adapter
  - generic V0.6 mutation -> APP_ADAPTER_REQUIRED
  - safe click -> HUMAN_GATE -> actual click effect
  - Delete All -> DENY / HIGH_RISK_CONTROL_LABEL
  - clean Edit text -> HUMAN_GATE -> actual text effect
  - personal text -> DENY
- builtin registry tests:
  - Chromium browser -> OBSERVE_ONLY
  - unmatched app -> OBSERVE_ONLY
  - ambiguous match -> fail closed

### Real Windows read-only observation

A visible `notepad.exe` window was observed and identified as:

`windows.notepad.v0`

with title still hidden and SEND still HOLD.

An earlier smoke that relied on the PID returned by `Start-Process notepad.exe` ended as `NOT_FOUND`; that launcher PID did not correspond to the visible Notepad window PID. This is retained as a separate failed smoke. It is NOT_ESTABLISHED that the later visible Notepad process was the exact launcher instance, so no mutation was attempted.

## Fresh failures retained from V0.6

1. in-process UIA COM fatal 0x8001010d -> UIA moved into isolated worker subprocess
2. Windows CP949 decode failure on UTF-8 Korean UI JSON -> worker transport forced to UTF-8
3. first synthetic click lacked observable effect -> InvokePattern preferred; fresh targeted rerun passed

## Explicitly not implemented / authorized

- browser mutation in V0.7
- arbitrary mouse coordinates
- arbitrary keyboard/hotkey injection
- password / secret UI injection
- SEND / payment / transfer / destructive UI controls
- EMR production write
- remote relay/device pairing
- PHI production workflow
- independent security review
- production installer / deployment

## Evidence ceiling

`BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_7_CANDIDATE`

This is a bounded development candidate, not a production-security or unrestricted desktop-control authorization.
