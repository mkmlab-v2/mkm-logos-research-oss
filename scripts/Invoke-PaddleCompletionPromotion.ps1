param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Apply,
    [string]$Note = "Paddle onboarding finished and verified."
)

$ErrorActionPreference = "Stop"

function Step([string]$Name, [scriptblock]$Block) {
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit $LASTEXITCODE)"
    }
}

try {
    $promoter = Join-Path $WorkspaceRoot "scripts\promote_paddle_onboarding_completed_v1.py"
    if (-not (Test-Path -LiteralPath $promoter)) {
        throw "Missing script: $promoter"
    }

    Step "Paddle completion promotion (dry-run)" {
        & py $promoter --workspace-root $WorkspaceRoot
    }

    if ($Apply) {
        Step "Paddle completion promotion (apply)" {
            & py $promoter --workspace-root $WorkspaceRoot --apply --note $Note
        }

        $acceptance = Join-Path $WorkspaceRoot "scripts\run_mkm_trackc_operational_acceptance.ps1"
        Step "Post-promotion acceptance" {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $acceptance -WorkspaceRoot $WorkspaceRoot
        }
    }

    Write-Host ""
    Write-Host "Paddle completion promotion chain finished." -ForegroundColor Green
    if ($Apply) {
        Write-Host "Mode: APPLY + acceptance recheck"
    }
    else {
        Write-Host "Mode: DRY-RUN only"
    }
    exit 0
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
