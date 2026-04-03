# B-Track pilot launcher for OpenClaude (npm: @gitlawb/openclaude).
# Scope (Fact-Lock): local research only — no trading daemon, no G: vault push, no VPS deploy.
# SSOT: root .cursorrules (TITAN + Cursor IDE·Agent·MCP), AGENTS.md (B-track vs ops), Hermes: projects/bitcoin-trading/ops/.hermes.md
# This script does NOT dot-source C:\workspace\.env; use session keys or OPENCLAUDE_PILOT_* only.
#
# Prerequisites: npm i -g @gitlawb/openclaude ; optional: Ollama on localhost for -Ollama
#
# Examples:
#   From repo root (C:\workspace): .\scripts\Start-OpenClaudeBTrackPilot.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Start-OpenClaudeBTrackPilot.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Start-OpenClaudeBTrackPilot.ps1 -Ollama
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Start-OpenClaudeBTrackPilot.ps1 -Ollama -Smoke
#   # One-shot chain: multilens pytest + backend smoke — scripts\Invoke-BTrackOpenClaudeFusionGate.ps1 (-Backend Ollama|Cloud)
#   # Custom smoke text: add -SmokePrompt 'Summarize AGENTS.md in one line' (keep short to save tokens)
#   # B-track smoke: OpenAI-compatible API (DashScope / OpenRouter / Vercel AI Gateway, etc.) — no .env dot-source
#   $env:OPENCLAUDE_PILOT_API_KEY = '<provider-key>'
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Start-OpenClaudeBTrackPilot.ps1 -CloudOpenAI -CloudBaseUrl 'https://openrouter.ai/api/v1' -CloudModel 'qwen/qwen3-6-plus'

param(
    [switch]$Ollama,
    [string]$OllamaModel = "qwen2.5-coder:7b",
    [string]$OllamaBaseUrl = "http://localhost:11434/v1",
    [switch]$Smoke,
    [switch]$CloudOpenAI,
    [string]$CloudBaseUrl = "",
    [string]$CloudModel = "",
    [string]$SmokePrompt = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArguments
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $workspace

Write-Host ""
Write-Host "[OpenClaude B-Track pilot] workspace=$workspace" -ForegroundColor Cyan
Write-Host "  Allowed tool root: --add-dir this workspace only (pass more dirs only if you intend)." -ForegroundColor DarkGray
Write-Host "  Not loaded: $workspace\.env (set keys in this shell or User env for pilot-only credentials)." -ForegroundColor DarkGray
Write-Host ""

if ($Ollama -and $CloudOpenAI) {
    Write-Error "Use only one of -Ollama or -CloudOpenAI."
}

if ($Smoke -and (-not $Ollama) -and (-not $CloudOpenAI)) {
    Write-Error "-Smoke requires -Ollama or -CloudOpenAI (sets backend before non-interactive check)."
}

if ($Ollama) {
    $env:CLAUDE_CODE_USE_OPENAI = "1"
    $env:OPENAI_BASE_URL = $OllamaBaseUrl
    $env:OPENAI_MODEL = $OllamaModel
    Write-Host "[OpenClaude B-Track pilot] Ollama-compatible: OPENAI_BASE_URL=$OllamaBaseUrl OPENAI_MODEL=$OllamaModel" -ForegroundColor Green
}

if ($CloudOpenAI) {
    $resolvedBase = if (-not [string]::IsNullOrWhiteSpace($CloudBaseUrl)) { $CloudBaseUrl } else { $env:OPENCLAUDE_PILOT_OPENAI_BASE_URL }
    $resolvedModel = if (-not [string]::IsNullOrWhiteSpace($CloudModel)) { $CloudModel } else { $env:OPENCLAUDE_PILOT_OPENAI_MODEL }
    if ([string]::IsNullOrWhiteSpace($resolvedBase)) {
        Write-Error @"
CloudOpenAI: missing base URL. Set one of:
  - `$env:OPENCLAUDE_PILOT_OPENAI_BASE_URL = 'https://openrouter.ai/api/v1'
  - or pass -CloudBaseUrl 'https://openrouter.ai/api/v1' (DashScope uses its own compatible-mode URL; see provider docs).
"@
    }
    if ([string]::IsNullOrWhiteSpace($resolvedModel)) {
        Write-Error @"
CloudOpenAI: missing model id. Set one of:
  - `$env:OPENCLAUDE_PILOT_OPENAI_MODEL = '<provider-model-slug>'
  - or pass -CloudModel '<provider-model-slug>' (exact string from OpenRouter/DashScope dashboard).
"@
    }
    $env:CLAUDE_CODE_USE_OPENAI = "1"
    $env:OPENAI_BASE_URL = $resolvedBase.TrimEnd("/")
    $env:OPENAI_MODEL = $resolvedModel
    Write-Host "[OpenClaude B-Track pilot] Cloud OpenAI-compatible: OPENAI_BASE_URL=$($env:OPENAI_BASE_URL) OPENAI_MODEL=$($env:OPENAI_MODEL)" -ForegroundColor Green
    Write-Host "  Fact-Lock: B-track research only; no production trading keys; sandbox data only for API calls." -ForegroundColor DarkGray
}

# Cloud: real provider key. Ollama: always ASCII placeholder — OPENCLAUDE_PILOT_API_KEY may contain
# non-Latin-1 chars or be set globally; passing it to Node/OpenClaude causes ByteString API errors.
if ($CloudOpenAI) {
    $pilotKey = $env:OPENCLAUDE_PILOT_API_KEY
    if ([string]::IsNullOrWhiteSpace($pilotKey)) {
        Write-Error "CloudOpenAI: set OPENCLAUDE_PILOT_API_KEY in this session (ASCII key from provider)."
    }
    $env:OPENAI_API_KEY = $pilotKey
    Write-Host "[OpenClaude B-Track pilot] Using OPENAI_API_KEY from OPENCLAUDE_PILOT_API_KEY (cloud only)." -ForegroundColor Green
}
if ($Ollama) {
    $env:OPENAI_API_KEY = "ollama"
    Write-Host "[OpenClaude B-Track pilot] Ollama: OPENAI_API_KEY=ollama (placeholder; ignores OPENCLAUDE_PILOT_API_KEY)." -ForegroundColor DarkGray
}

$oc = Get-Command openclaude -ErrorAction SilentlyContinue
if (-not $oc) {
    Write-Error "openclaude not on PATH. Install: npm install -g @gitlawb/openclaude"
}

if ($Smoke) {
    $smokeText = if (-not [string]::IsNullOrWhiteSpace($SmokePrompt)) { $SmokePrompt.Trim() } else { "Reply with exactly one word: OK" }
    Write-Host "[OpenClaude B-Track pilot] Smoke: non-interactive one-shot (openclaude --print)..." -ForegroundColor Cyan
    $smokeArgs = @("--add-dir", $workspace, "-p", $smokeText, "--print")
    & openclaude @smokeArgs
    exit $LASTEXITCODE
}

$invokeArgs = @("--add-dir", $workspace) + $RemainingArguments
Write-Host "[OpenClaude B-Track pilot] starting: openclaude $($invokeArgs -join ' ')" -ForegroundColor Cyan
& openclaude @invokeArgs
exit $LASTEXITCODE
