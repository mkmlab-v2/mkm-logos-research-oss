#Requires -Version 5.1
<#
.SYNOPSIS
  Azure OpenAI LLM 1st-priority readiness: .env keys, optional chat smoke, prod router-status.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-AzureOpenAiLlmReadiness_v1.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-AzureOpenAiLlmReadiness_v1.ps1 -ApplyEnvTemplate
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$ApiBase = "https://api.no1kmedi.com",
    [switch]$ApplyEnvTemplate,
    [switch]$SkipProdProbe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-DotEnvKeys {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $map }
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -match '^\s*#' -or [string]::IsNullOrWhiteSpace($line)) { return }
        if ($line -match '^\s*export\s+') { $line = ($line -replace '^\s*export\s+', '') }
        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { return }
        $k = $line.Substring(0, $idx).Trim()
        $v = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
        if ($k) { $map[$k] = $v }
    }
    return $map
}

function Ensure-EnvBlock {
    param([string]$Path)
    $block = @(
        ""
        "# --- Azure OpenAI (MKM all domains · LLM 1st · Microsoft for Startups credits) ---"
        "MKM_LLM_PRIORITY=azure_first"
        "# Fill after Portal: Azure OpenAI resource -> Keys and Endpoint + Deployments"
        "# AZURE_OPENAI_ENDPOINT=https://YOUR_RESOURCE.openai.azure.com"
        "# AZURE_OPENAI_API_KEY="
        "# AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini"
        "# AZURE_OPENAI_API_VERSION=2024-08-01-preview"
        "# AZURE_OPENAI_FETCH_TIMEOUT_MS=60000"
    )
    $text = if (Test-Path -LiteralPath $Path) { Get-Content -LiteralPath $Path -Raw -Encoding UTF8 } else { "" }
    if ($text -match 'MKM_LLM_PRIORITY\s*=') {
        Write-Host "[skip] .env already has MKM_LLM_PRIORITY"
        return
    }
    Add-Content -LiteralPath $Path -Value ($block -join "`n") -Encoding UTF8
    Write-Host "[ok] appended Azure OpenAI LLM block to $Path"
}

$envPath = Join-Path $RepoRoot ".env"
$outPath = Join-Path $RepoRoot "reports\azure_openai_llm_readiness_latest.json"

if ($ApplyEnvTemplate) {
    Ensure-EnvBlock -Path $envPath
}

$required = @("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
$envMap = Read-DotEnvKeys -Path $envPath
$missing = @($required | Where-Object { -not $envMap.ContainsKey($_) -or [string]::IsNullOrWhiteSpace($envMap[$_]) })

$smokeExit = $null
$smokeOk = $false
if ($missing.Count -eq 0) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        Push-Location $RepoRoot
        try {
            & py scripts/check_azure_openai_chat_smoke_v1.py
            $smokeExit = $LASTEXITCODE
            $smokeOk = ($smokeExit -eq 0)
        }
        finally { Pop-Location }
    }
}

$prodRouter = $null
if (-not $SkipProdProbe) {
    try {
        $uri = "$($ApiBase.TrimEnd('/'))/api/ai/router-status"
        $prodRouter = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 20
    }
    catch {
        $prodRouter = @{ error = $_.Exception.Message }
    }
}

$codeDeployed = $false
if ($prodRouter -and $prodRouter.PSObject.Properties.Name -contains "backends") {
    $codeDeployed = $prodRouter.backends.PSObject.Properties.Name -contains "azure"
}

$manual = @(
    "Azure Portal -> Azure OpenAI / Cognitive Services -> Create resource (region e.g. koreacentral)",
    "Model deployments -> Add deployment (e.g. gpt-4o-mini) -> copy deployment name",
    "Keys and Endpoint -> copy Endpoint + Key into .env (AZURE_OPENAI_*)",
    "VPS payapp-api: git pull && ./deploy-vps-local-llm.sh && curl api.../api/ai/router-status (backends.azure=true)",
    "jema-ai.com PM2 no1kmedi-com: restart after .env update"
)

$readinessOk = ($missing.Count -eq 0) -and $smokeOk

$doc = [ordered]@{
    schema                = "azure_openai_llm_readiness_v1"
    checked_at_utc        = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    readiness_ok          = $readinessOk
    env_path              = $envPath
    mkm_llm_priority      = $envMap["MKM_LLM_PRIORITY"]
    missing_env_keys      = $missing
    azure_chat_smoke_ok   = $smokeOk
    azure_chat_smoke_exit = $smokeExit
    prod_api_base         = $ApiBase
    prod_router_status    = $prodRouter
    prod_code_has_azure   = $codeDeployed
    manual_remainder      = $manual
}

$reportsDir = Split-Path -Parent $outPath
if (-not (Test-Path -LiteralPath $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}
$doc | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Host ""
Write-Host "=== Azure OpenAI LLM readiness ===" -ForegroundColor Cyan
Write-Host "readiness_ok: $readinessOk"
Write-Host "missing_env: $($missing -join ', ')"
Write-Host "prod backends.azure field: $codeDeployed (false = VPS needs git pull + deploy)"
Write-Host "report: $outPath"

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Next: Portal에서 Endpoint/Key/Deployment 채운 뒤:" -ForegroundColor Yellow
    Write-Host "  powershell -File scripts\Invoke-AzureOpenAiLlmReadiness_v1.ps1"
    exit 2
}
if (-not $smokeOk) { exit 1 }
exit 0
