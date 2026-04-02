# Print-only: how to silence duplicate GOOGLE_API_KEY warnings when using GEMINI_API_KEY only.
# Does not read or print any API key values.

Write-Host @"
Gemini env hygiene (no secrets printed)
--------------------------------------
If you use GEMINI_API_KEY only, remove the legacy user-level GOOGLE_API_KEY to reduce client warnings:

  # PowerShell (current session)
  Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue

  # Windows User environment (persistent) — run in elevated or User scope as appropriate:
  [System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', $null, 'User')

Do not commit keys. See AGENTS.md and scripts/gemini_multimodal_batch.py header.
"@
