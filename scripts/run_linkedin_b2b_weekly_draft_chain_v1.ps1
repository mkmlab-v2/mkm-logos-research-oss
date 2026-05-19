# Weekly LinkedIn B2B draft chain — assemble-only + copy guard (no publish).
param(
    [string]$WorkspaceRoot = "",
    [switch]$Gemini,
    [switch]$WithChart,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = if ($WorkspaceRoot) { (Resolve-Path -LiteralPath $WorkspaceRoot).Path } else { Split-Path -Parent $PSScriptRoot }
$dotenv = Join-Path $root "scripts\Import-WorkspaceDotEnv_v1.ps1"
if (Test-Path -LiteralPath $dotenv) {
    . $dotenv -WorkspaceRoot $root
}
$queue = Join-Path $root "data\marketing\linkedin_queue.json"
$example = Join-Path $root "data\marketing\linkedin_queue_v1.example.json"
$gen = Join-Path $root "scripts\generate_linkedin_b2b_copy_v1.py"
$guard = Join-Path $root "scripts\check_linkedin_b2b_draft_copy_v1.py"
$no1k = Join-Path $root "projects\no1kmedi"

if (-not (Test-Path -LiteralPath $queue)) {
    Copy-Item -LiteralPath $example -Destination $queue -Force
    Write-Host "init queue from example: $queue"
}

if ($WhatIfOnly) {
    & py $gen --queue $queue --dry-run
    exit $LASTEXITCODE
}

$genArgs = @($gen, "--queue", $queue, "--strict-compliance")
if ($Gemini) { $genArgs += "--gemini" } else { $genArgs += "--assemble-only" }
if ($WithChart) { $genArgs += "--with-chart" }
& py @genArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py $guard --drafts-dir (Join-Path $root "reports\marketing\linkedin_drafts")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (Test-Path -LiteralPath (Join-Path $no1k "package.json")) {
    Push-Location $no1k
    try {
        npm run check:marketing-copy --if-present
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

Write-Host "OK: LinkedIn B2B drafts in reports/marketing/linkedin_drafts — human publish only."
exit 0
