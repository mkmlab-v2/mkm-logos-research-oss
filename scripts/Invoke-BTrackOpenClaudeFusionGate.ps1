# B-track fusion gate: multilens pytest (optional), then OpenClaude backend smoke (Ollama or Cloud OpenAI-compatible).
# Does not load .env. Cloud: set OPENCLAUDE_PILOT_API_KEY in the shell (or User env) before -Backend Cloud.
# Isolation: does not touch daemons or trading keys; B-track log is optional append-only text.
#
# OpenClaude sends tool-style API calls. Ollama models that do not advertise tool support (e.g. gemma4:e2b) may
# return HTTP 400 on smoke — use default qwen2.5-coder:7b or another tool-capable tag for OpenClaude smoke.
#
# Examples:
#   .\scripts\Invoke-BTrackOpenClaudeFusionGate.ps1
#   .\scripts\Invoke-BTrackOpenClaudeFusionGate.ps1 -OllamaModel 'llama3.1:8b'
#   .\scripts\Invoke-BTrackOpenClaudeFusionGate.ps1 -Backend Cloud -CloudBaseUrl 'https://openrouter.ai/api/v1' -CloudModel 'qwen/qwen3-6-plus'
#   .\scripts\Invoke-BTrackOpenClaudeFusionGate.ps1 -SkipPytest -WriteFusionLog

param(
    [switch]$SkipPytest,
    [ValidateSet('Ollama', 'Cloud')]
    [string]$Backend = 'Ollama',
    [switch]$UseGemma3Local,
    [string]$OllamaModel = 'qwen2.5-coder:7b',
    [string]$CloudBaseUrl = '',
    [string]$CloudModel = '',
    [string]$SmokePrompt = '',
    [switch]$WriteFusionLog
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if ($UseGemma3Local) {
    # Legacy switch name: local Gemma line; now gemma4:e2b (gemma3:4b retired from Ollama on this machine).
    $OllamaModel = 'gemma4:e2b'
    Write-Warning "UseGemma3Local -> gemma4:e2b: OpenClaude may return 400 if the model does not support tools. Prefer -OllamaModel qwen2.5-coder:7b for smoke."
}

$launcher = Join-Path $root "scripts\Start-OpenClaudeBTrackPilot.ps1"
$logDir = Join-Path $root "projects\bitcoin-trading\memory\v2\btrack"
$logFile = Join-Path $logDir "fusion_gate_last.txt"

function Write-FusionLogLine {
    param([string]$Line)
    if (-not $WriteFusionLog) { return }
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $logFile -Value "[$ts] $Line" -Encoding utf8
}

Write-Host ""
if (-not $SkipPytest) {
    Write-Host "[Fusion] (1/2) pytest tests/test_multilens_sensitive_integrity_gate.py" -ForegroundColor Cyan
    & py -m pytest tests/test_multilens_sensitive_integrity_gate.py -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Fusion] pytest failed; skipping OpenClaude smoke." -ForegroundColor Red
        Write-FusionLogLine "pytest FAIL exit=$LASTEXITCODE backend=$Backend model=$OllamaModel"
        exit $LASTEXITCODE
    }
    Write-FusionLogLine "pytest OK backend=$Backend"
} else {
    Write-Host "[Fusion] Skipping pytest (-SkipPytest)." -ForegroundColor Yellow
    Write-FusionLogLine "pytest SKIPPED backend=$Backend"
}

Write-Host ""
$step = if ($SkipPytest) { "(1/1)" } else { "(2/2)" }
Write-Host "[Fusion] $step Start-OpenClaudeBTrackPilot.ps1 smoke (Backend=$Backend)" -ForegroundColor Cyan

$psiArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $launcher
)

if ($Backend -eq 'Ollama') {
    $psiArgs += @('-Ollama', '-OllamaModel', $OllamaModel)
} else {
    $resolvedBase = if (-not [string]::IsNullOrWhiteSpace($CloudBaseUrl)) { $CloudBaseUrl } else { $env:OPENCLAUDE_PILOT_OPENAI_BASE_URL }
    $resolvedModel = if (-not [string]::IsNullOrWhiteSpace($CloudModel)) { $CloudModel } else { $env:OPENCLAUDE_PILOT_OPENAI_MODEL }
    if ([string]::IsNullOrWhiteSpace($resolvedBase)) {
        Write-Error "Backend Cloud: set -CloudBaseUrl or OPENCLAUDE_PILOT_OPENAI_BASE_URL."
    }
    if ([string]::IsNullOrWhiteSpace($resolvedModel)) {
        Write-Error "Backend Cloud: set -CloudModel or OPENCLAUDE_PILOT_OPENAI_MODEL."
    }
    $psiArgs += @(
        '-CloudOpenAI',
        '-CloudBaseUrl', $resolvedBase,
        '-CloudModel', $resolvedModel
    )
}

$psiArgs += '-Smoke'
if (-not [string]::IsNullOrWhiteSpace($SmokePrompt)) {
    $psiArgs += @('-SmokePrompt', $SmokePrompt)
}

& powershell @psiArgs
$exitCode = $LASTEXITCODE
Write-FusionLogLine "openclaude smoke exit=$exitCode backend=$Backend"
exit $exitCode
