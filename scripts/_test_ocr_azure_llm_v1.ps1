# One-off OCR Azure connectivity probe — reads .env, never echoes secrets.
$ErrorActionPreference = 'Stop'
$envPath = Join-Path (Split-Path $PSScriptRoot -Parent) '.env'
if (-not (Test-Path $envPath)) { Write-Error 'missing .env'; exit 2 }

$map = @{}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $parts = $_ -split '=', 2
    $map[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
}

$endpoint = ($map['AZURE_OPENAI_ENDPOINT'] -replace '/$', '').Trim()
$dep = $map['AZURE_OPENAI_DEPLOYMENT'].Trim()
$key = $map['AZURE_OPENAI_API_KEY'].Trim()
$ver = if ($map['AZURE_OPENAI_API_VERSION']) { $map['AZURE_OPENAI_API_VERSION'].Trim() } else { '2024-08-01-preview' }

if (-not ($endpoint -and $dep -and $key)) {
    Write-Output 'AZURE_INCOMPLETE'
    exit 2
}

# Azure OpenAI v1-compatible base (OCR appends /chat/completions). api-version not in path.
$env:OCR_LLM_URL = "$endpoint/openai/v1"
$env:OCR_LLM_TOKEN = $key
$env:OCR_LLM_MODEL = $dep
$env:OCR_USE_ANTHROPIC = 'false'

Write-Output "probe: deployment=$dep api_version=$ver"
& ocr llm test
exit $LASTEXITCODE
