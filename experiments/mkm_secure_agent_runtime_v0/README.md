# MKM Secure Agent Runtime V0.6

Bounded local-first runtime candidate for MKM's Desktop Commander-class tool layer.

## Implemented

### V0 core
- approved-root path policy
- list/read/write file primitives
- HUMAN_GATE on writes and command execution
- argv-only subprocess execution; never `shell=True`
- executable allowlist + blocked risky Git subcommands
- SHA-256 Thin Coordinates
- append-only JSONL action receipts without raw file/prompt contents
- semantic state remains `NOT_ADJUDICATED`; SEND remains `HOLD`

### V0.1 MCP
- MCP Python SDK v2 stdio server
- tool discovery / structured schemas
- out-of-band local approval broker
- approval state outside model-accessible roots
- one-time exact-action approval consumption
- local approval CLI

### V0.2 privacy gate
- deterministic local secret/direct-identifier prefilter
- automatic scan before local file body is released through MCP
- SECRET -> DENY
- direct identifier + medical context -> PHI / HOLD
- PERSONAL -> HOLD
- metadata-only privacy scan tool
- person-name detection remains NOT_ESTABLISHED

### V0.3 secret broker
- Windows current-user DPAPI secret-at-rest store
- local-only secret management CLI
- MCP exposes secret-handle metadata only
- no MCP tool returns decrypted secret material

### V0.4 rollback
- approved text writes capture Windows DPAPI-encrypted pre-write snapshots
- existing files restore original bytes
- newly created files can be removed by rollback
- rollback is local CLI only
- write_text bounded to 1 MiB

### V0.5 Windows tray / approval UI
- pystray notification-area shell
- new REQUESTED approval opens a local popup
- Approve once / Deny buttons operate on local ApprovalBroker
- popup displays target + argument digest, not raw write contents
- Ollama auto-connect is loopback-only and cleans up failed MKM-started processes

### V0.6 Desktop Action Layer
- Windows UI Automation via pywinauto UIA backend
- all UIA work isolated in a separate worker subprocess
- UIA crash cannot directly kill the MCP runtime
- worker transport forced to UTF-8
- opaque, expiring local UI refs
- visible top-level window observation
- window titles hidden by default
- Edit/Text/Document contents hidden by default
- control labels exposed only for bounded action-oriented controls
- click mutation requires HUMAN_GATE
- non-sensitive Edit text mutation requires HUMAN_GATE
- password controls DENY
- PERSONAL/PHI/SECRET text input DENY
- high-risk action labels such as Delete/Send/Pay/Transfer/Deploy/Purchase DENY
- no arbitrary screen coordinates
- no raw keyboard shortcut injection
- denied UI requests return structured DENIED, not tool exceptions

## Exposed MCP tools

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

Desktop V0.6:
- `ui_list_windows`
- `ui_inspect_window`
- `request_ui_click`
- `execute_ui_click`
- `request_ui_set_text`
- `execute_ui_set_text`

## Explicitly not implemented / authorized

- arbitrary mouse coordinates
- arbitrary keyboard sequences / hotkeys
- password-field input
- secret injection into browser/subprocess
- destructive / SEND / payment / transfer UI controls
- remote relay/device pairing
- git push/deploy/SEND
- PHI production workflow
- reliable person-name recognition
- independent security review
- production installer/startup registration

## Current validation

- full targeted Windows suite: 60 PASS
- MCP stdio protocol observed: 2026-07-28
- MCP tool count observed after V0.6: 18
- approval/privacy/secret/rollback/Ollama/tray tests: PASS within bounded fixtures
- synthetic WinForms UIA targeted suite: 8 PASS
- final Desktop MCP wire smoke:
  - safe click request -> HUMAN_GATE
  - local approval -> click effect observed
  - high-risk Delete control -> structured DENIED
  - SEND remained HOLD
  - window title hidden
  - Edit content hidden
- pywinauto version observed: 0.6.9
- psutil version observed: 7.2.2

### Fresh failures retained

1. In-process pywinauto UIA enumeration produced Windows fatal COM exception `0x8001010d`.
   - Design changed to isolated UI worker subprocess.
   - This failure is not relabeled as PASS.

2. First worker implementation used Windows default CP949 parent decoding while worker emitted UTF-8.
   Korean UI text caused the parent reader thread to fail.
   - Worker transport is now explicitly UTF-8.
   - This failure is retained as evidence.

3. Initial synthetic click reported execution but fixture sentinel did not appear.
   - Click implementation changed to prefer UIA InvokePattern / logical click.
   - Synthetic fixture path was simplified.
   - Fresh targeted rerun passed 8/8.

## Evidence ceiling

`BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_6_CANDIDATE`

This is a development candidate, not production-security or unrestricted desktop-control authorization.
