param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipVaultMirror,
    [switch]$SkipMkmMemoryInventory,
    [switch]$SkipPhase1Readiness,
    [switch]$StrictPhase1Readiness,
    [switch]$StrictReconcile,
    [switch]$IncludeCompressionKpi,
    [switch]$IncludeLiteralTrack,
    [switch]$SkipHydrationMix,
    [switch]$SkipCompressionAlarm,

    [switch]$IncludeExternalDriveGovernance
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot

function Step([string]$Name, [scriptblock]$Block) {
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit $LASTEXITCODE)"
    }
}

try {
    Step "P0 / CONSTITUTION paths" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\verify_p0_constitution_gate_paths.ps1") -WorkspaceRoot $root
    }

    if (-not $SkipMkmMemoryInventory) {
        $inv = Join-Path $root "scripts\inventory_mkm_memory_report.py"
        if (Test-Path -LiteralPath $inv) {
            Step "MKM memory inventory (.mkm-memory -> reports/memory)" {
                # Default cap keeps health runs fast on large trees; full scan: MKM_MEMORY_INVENTORY_FULL=1
                $extra = @()
                if ($env:MKM_MEMORY_INVENTORY_FULL -eq "1") {
                    $extra = @()
                }
                elseif ($env:MKM_MEMORY_INVENTORY_MAX_FILES -match '^\d+$') {
                    $extra += "--max-files"
                    $extra += $env:MKM_MEMORY_INVENTORY_MAX_FILES
                }
                else {
                    $extra += "--max-files"
                    $extra += "8000"
                }
                & py $inv @extra
            }
        }
        else {
            Write-Host ""
            Write-Host "=== MKM memory inventory ===" -ForegroundColor Yellow
            Write-Host "SKIP: inventory_mkm_memory_report.py not found"
        }
    }

    if (-not $SkipVaultMirror) {
        $vault = $env:MKM_VAULT_ROOT
        if ([string]::IsNullOrWhiteSpace($vault)) {
            $vault = "G:\공유 드라이브\MKM_DATA_VAULT\vault"
        } else {
            $vault = $vault.Trim().TrimEnd('\')
        }
        if (Test-Path -LiteralPath $vault) {
            Step "NotebookLM vault mirror" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1")
            }
        }
        else {
            Write-Host ""
            Write-Host "=== NotebookLM vault mirror ===" -ForegroundColor Yellow
            Write-Host "SKIP: Vault not mounted ($vault)"
        }
    }

    if (-not $SkipPhase1Readiness) {
        $ops = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal"
        $vr = Join-Path $ops "verify_ops_phase1_operational_readiness.ps1"
        if (Test-Path -LiteralPath $vr) {
            Step "Phase 1 operational readiness" {
                if ($StrictPhase1Readiness) {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $vr -Strict
                } else {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $vr
                }
            }
        }
    }

    Write-Host ""
    Write-Host "=== Automation registry reconcile ===" -ForegroundColor Cyan
    $rec = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\reconcile_automation_registry.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $rec
    $re = $LASTEXITCODE
    if ($re -ne 0) {
        $msg = "reconcile_automation_registry exit $re (scheduler drift?)"
        if ($StrictReconcile) { throw $msg }
        Write-Host "WARN: $msg" -ForegroundColor Yellow
    }

    if ($IncludeCompressionKpi) {
        $cc = Join-Path $root "scripts\run_compression_automation_chain.ps1"
        $literalNote = if ($IncludeLiteralTrack) { " + literal track" } else { "" }
        Step "Compression KPI chain (default + KPI summary + hydration mix$literalNote)" {
            # Invoke in-process (avoid nested powershell.exe mangling switch types).
            & $cc -WorkspaceRoot $root -SkipHydrationMix:$SkipHydrationMix -SkipCompressionAlarm:$SkipCompressionAlarm -IncludeLiteralTrack:$IncludeLiteralTrack
        }
    }

    if ($IncludeExternalDriveGovernance) {
        $gov = Join-Path $root "scripts\Invoke-ExternalDrivesGovernance.ps1"
        if (Test-Path -LiteralPath $gov) {
            Step "E:/F: governance (quick)" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $gov -WorkspaceRoot $root
            }
        }
    }

    Write-Host ""
    Write-Host "[run_workspace_automation_health] ALL OK" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
