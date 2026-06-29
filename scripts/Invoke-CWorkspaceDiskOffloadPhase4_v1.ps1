<#
.SYNOPSIS
  C: disk offload Phase4 — hiberfil off, WSL distro move to F:, Nemotron junction offload.

.NOTES
  [HYPO] infra lane · research_only · junctions preserve /mnt/c/workspace paths for WSL.
#>
param(
    [switch]$WhatIfOnly,
    [switch]$SkipHibernate,
    [switch]$SkipWsl,
    [switch]$SkipNemotron
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location $root

$wslRoot = "F:\workspace_offload\wsl"
$nemotronRoot = "F:\workspace_offload\nemotron"
$outJson = Join-Path $root "reports\c_workspace_disk_offload_phase4_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

function Get-CFreeGb {
    [math]::Round((Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB, 2)
}

function Add-Step([System.Collections.Generic.List[object]]$steps, $name, $exitCode, $note) {
    $steps.Add([ordered]@{
        name      = $name
        exit_code = $exitCode
        note      = $note
    }) | Out-Null
}

function Ensure-Dir($path) {
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

function Move-TreeWithJunction {
    param(
        [string]$Source,
        [string]$Dest,
        [string]$StepName,
        [System.Collections.Generic.List[object]]$Steps,
        [bool]$DryRun
    )
    if (-not (Test-Path -LiteralPath $Source)) {
        Add-Step $Steps $StepName 0 "skipped_missing_source"
        return
    }
    $item = Get-Item -LiteralPath $Source -Force
    if ($item.LinkType -eq "Junction") {
        Add-Step $Steps $StepName 0 "already_junction target=$($item.Target)"
        return
    }
    if ($DryRun) {
        Add-Step $Steps $StepName 0 "whatif_would_move_to=$Dest"
        return
    }
    Ensure-Dir (Split-Path -Parent $Dest)
    if (Test-Path -LiteralPath $Dest) {
        throw "Dest already exists: $Dest"
    }
    $robolog = Join-Path $root "reports\robocopy_phase4_$(($StepName -replace '[^a-zA-Z0-9]','_')).log"
    & robocopy $Source $Dest /E /MOVE /R:2 /W:2 /NFL /NDL /NP /LOG:$robolog | Out-Null
    $rc = $LASTEXITCODE
    if ($rc -ge 8) {
        Add-Step $Steps $StepName $rc "robocopy_failed rc=$rc log=$robolog"
        throw "robocopy failed for $Source rc=$rc"
    }
    if (Test-Path -LiteralPath $Source) {
        Remove-Item -LiteralPath $Source -Recurse -Force -ErrorAction SilentlyContinue
    }
    cmd /c "mklink /J `"$Source`" `"$Dest`"" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "mklink failed for $Source"
    }
    Add-Step $Steps $StepName 0 "junction_ok robocopy_rc=$rc dest=$Dest"
}

$steps = [System.Collections.Generic.List[object]]::new()
$before = Get-CFreeGb

# 1) Hibernate off
if (-not $SkipHibernate) {
    Write-Host "[1/3] powercfg /h off..." -ForegroundColor Cyan
    if ($WhatIfOnly) {
        Add-Step $steps "hibernate_off" 0 "whatif_skipped"
    } else {
        & powercfg /h off
        Add-Step $steps "hibernate_off" $LASTEXITCODE "powercfg_h_off"
    }
} else {
    Add-Step $steps "hibernate_off" 0 "skipped_flag"
}

# 2) WSL move
if (-not $SkipWsl) {
    Write-Host "[2/3] WSL distro move to $wslRoot ..." -ForegroundColor Cyan
    if ($WhatIfOnly) {
        Add-Step $steps "wsl_shutdown" 0 "whatif_skipped"
        Add-Step $steps "wsl_move" 0 "whatif_skipped"
    } else {
        & wsl --shutdown
        Start-Sleep -Seconds 3
        Add-Step $steps "wsl_shutdown" $LASTEXITCODE "wsl_shutdown"
        Ensure-Dir $wslRoot
        $distros = @("Ubuntu-24.04", "Ubuntu-22.04")
        foreach ($d in $distros) {
            $listed = & wsl --list --quiet 2>$null
            if ($listed -notcontains $d) {
                Add-Step $steps "wsl_move_$d" 0 "distro_not_installed"
                continue
            }
            $dest = Join-Path $wslRoot $d
            Ensure-Dir $dest
            & wsl --manage $d --move $dest
            Add-Step $steps "wsl_move_$d" $LASTEXITCODE "dest=$dest"
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "wsl move failed for $d exit=$LASTEXITCODE"
            }
        }
    }
} else {
    Add-Step $steps "wsl_move" 0 "skipped_flag"
}

# 3) Nemotron junction offload
if (-not $SkipNemotron) {
    Write-Host "[3/3] Nemotron trees -> $nemotronRoot (junction)..." -ForegroundColor Cyan
    Ensure-Dir $nemotronRoot
    Move-TreeWithJunction `
        -Source (Join-Path $root "storage\hf_cache\nemotron_wsl") `
        -Dest (Join-Path $nemotronRoot "nemotron_wsl") `
        -StepName "nemotron_hf_cache_junction" `
        -Steps $steps `
        -DryRun:$WhatIfOnly
    Move-TreeWithJunction `
        -Source (Join-Path $root "data\nvidia") `
        -Dest (Join-Path $nemotronRoot "data_nvidia") `
        -StepName "nemotron_data_nvidia_junction" `
        -Steps $steps `
        -DryRun:$WhatIfOnly
} else {
    Add-Step $steps "nemotron_offload" 0 "skipped_flag"
}

$after = Get-CFreeGb
$report = [ordered]@{
    schema             = "c_workspace_disk_offload_phase4_v1"
    generated_at_utc   = $utc
    research_only      = $true
    hypothesis_tag     = "[HYPO]"
    c_free_gb_before   = $before
    c_free_gb_after    = $after
    c_free_delta_gb    = [math]::Round($after - $before, 2)
    wsl_root           = $wslRoot
    nemotron_root      = $nemotronRoot
    steps              = $steps
    boundary_ack       = "infra_only_no_track_a_live"
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outJson -Encoding UTF8
Write-Host "Phase4 report: $outJson" -ForegroundColor Green
Write-Host "C: free ${before}GB -> ${after}GB (delta $([math]::Round($after - $before, 2))GB)"

$fatal = $steps | Where-Object {
    $_.exit_code -ne 0 -and $_.name -notin @('hibernate_off')
}
if ($fatal) { exit 1 }
exit 0
