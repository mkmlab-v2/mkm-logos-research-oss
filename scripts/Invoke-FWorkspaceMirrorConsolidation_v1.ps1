<#
.SYNOPSIS
  F: workspace full-copy consolidation — inventory, dated legacy mirror tree, empty-shell cleanup.

.DESCRIPTION
  Active tiers (DO NOT MOVE — junction/cold paths):
    F:\workspace_offload, F:\workspace_cold_storage

  Legacy full copies consolidated under:
    F:\MKM_DISK_SSOT_V1\legacy_mirrors\

  Default: inventory + plan JSON only. -Apply moves legacy copies; -RemoveEmptyShells drops 0-byte roots.

.NOTES
  [HYPO] infra · research_only · no Track A / live coupling.
#>
param(
    [switch]$Apply,
    [switch]$RemoveEmptyShells,
    [string]$SsotRoot = "F:\MKM_DISK_SSOT_V1",
    [string]$CanonicalWorkspace = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$repo = "C:\workspace"
Set-Location $repo

$outJson = Join-Path $repo "reports\f_workspace_mirror_consolidation_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

function Get-DirBytes([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    $out = robocopy $path 'C:\__null__' /L /E /BYTES /NFL /NDL /NJH /XJ /R:0 /W:0 | Select-String 'Bytes :'
    if (-not $out) { return 0 }
    return [int64](($out.ToString() -split '\s+')[3])
}

$activePreserve = @(
    @{ path = "F:\workspace_offload"; role = "phase1_hf_ollama_junction_target" },
    @{ path = "F:\workspace_cold_storage"; role = "phase3_cold_archive" }
)

$legacySources = @(
    @{ key = "workspace_backups"; path = "F:\workspace_backups"; strategy = "move_children" },
    @{ key = "workspace_archive"; path = "F:\workspace_archive"; strategy = "move_whole" },
    @{ key = "MKM_Archive"; path = "F:\MKM_Archive"; strategy = "move_children" }
)

$emptyShellCandidates = @(
    "F:\workspace",
    "F:\workspace_offload_probe",
    "F:\workspace-20251222.backup_20251222_044410"
)

$inventory = [System.Collections.Generic.List[object]]::new()
foreach ($item in ($activePreserve + $legacySources)) {
    $p = $item.path
    $bytes = Get-DirBytes $p
    $inventory.Add([ordered]@{
        path       = $p
        bytes      = $bytes
        gb         = if ($null -ne $bytes) { [math]::Round($bytes / 1GB, 2) } else { $null }
        role       = if ($item.role) { $item.role } else { "legacy_full_copy" }
        exists     = (Test-Path -LiteralPath $p)
    }) | Out-Null
}

$steps = [System.Collections.Generic.List[object]]::new()
function Add-Step($name, $exitCode, $note) {
    $script:steps.Add([ordered]@{ name = $name; exit_code = $exitCode; note = $note }) | Out-Null
}

$legacyDest = Join-Path $SsotRoot "legacy_mirrors"
if ($Apply) {
    New-Item -ItemType Directory -Path $legacyDest -Force | Out-Null
}

Write-Host "[plan] F: mirror consolidation (apply=$Apply)" -ForegroundColor Cyan

foreach ($src in $legacySources) {
    if (-not (Test-Path -LiteralPath $src.path)) {
        Add-Step "skip_$($src.key)" 0 "missing"
        continue
    }
    if ($src.strategy -eq "move_whole") {
        $dest = Join-Path $legacyDest $src.key
        if ($Apply) {
            if (-not (Test-Path -LiteralPath $dest)) {
                robocopy $src.path $dest /E /MOVE /R:1 /W:2 /NFL /NDL /NP | Out-Null
                Add-Step "move_$($src.key)" $LASTEXITCODE "dest=$dest"
            } else {
                Add-Step "move_$($src.key)" 0 "dest_exists_skipped"
            }
        } else {
            Write-Host "  whatif MOVE $($src.path) -> $dest"
            Add-Step "move_$($src.key)" 0 "whatif dest=$dest"
        }
    } else {
        Get-ChildItem -LiteralPath $src.path -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $dest = Join-Path $legacyDest ("{0}_{1}" -f $src.key, $_.Name)
            if ($Apply) {
                if (-not (Test-Path -LiteralPath $dest)) {
                    robocopy $_.FullName $dest /E /MOVE /R:1 /W:2 /NFL /NDL /NP | Out-Null
                    Add-Step "move_$($src.key)_$($_.Name)" $LASTEXITCODE "dest=$dest"
                } else {
                    Add-Step "move_$($src.key)_$($_.Name)" 0 "dest_exists_skipped"
                }
            } else {
                Write-Host "  whatif MOVE $($_.FullName) -> $dest"
                Add-Step "move_$($src.key)_$($_.Name)" 0 "whatif dest=$dest"
            }
        }
        if ($Apply) {
            $left = @(Get-ChildItem -LiteralPath $src.path -Recurse -Force -ErrorAction SilentlyContinue).Count
            if ($left -eq 0) {
                Remove-Item -LiteralPath $src.path -Recurse -Force -ErrorAction SilentlyContinue
                Add-Step "rmdir_empty_$($src.key)" 0 "removed_parent"
            }
        }
    }
}

if ($RemoveEmptyShells) {
    foreach ($shell in $emptyShellCandidates) {
        if (-not (Test-Path -LiteralPath $shell)) { continue }
        $bytes = Get-DirBytes $shell
        if ($bytes -eq 0) {
            if ($Apply) {
                Remove-Item -LiteralPath $shell -Recurse -Force -ErrorAction SilentlyContinue
                Add-Step "remove_shell" 0 $shell
            } else {
                Add-Step "remove_shell" 0 "whatif $shell"
            }
        } else {
            Add-Step "remove_shell_skip" 0 "nonempty $shell gb=$([math]::Round($bytes/1GB,2))"
        }
    }
}

$fFree = if (Test-Path F:\) { [math]::Round((Get-Volume -DriveLetter F).SizeRemaining / 1GB, 1) } else { $null }

$doc = [ordered]@{
    schema                  = "f_workspace_mirror_consolidation_v1"
    generated_at_utc        = $utc
    research_only           = $true
    hypothesis_tag          = "[HYPO]"
    canonical_workspace     = $CanonicalWorkspace
    ssot_root               = $SsotRoot
    active_preserve_paths   = $activePreserve.path
    inventory               = $inventory
    consolidation_actions   = $steps
    future_backup_command   = 'powershell -File scripts\backup_workspace_mirror.ps1 -DestinationRoot F:\MKM_DISK_SSOT_V1\dated_mirrors\YYYYMMDD_workspace'
    stale_mirror_delete_note = 'legacy_mirrors 20260401 full copy ~73GB: human verify vs C:\workspace SSOT before delete for ~73GB F: recovery'
    f_free_gb               = $fFree
    boundary_ack            = "infra_only_no_track_a_live_merge"
}

($doc | ConvertTo-Json -Depth 8) | Set-Content -Path $outJson -Encoding utf8
Write-Host "Wrote $outJson" -ForegroundColor Green
if ($null -ne $fFree) { Write-Host "F: free ${fFree} GB" -ForegroundColor Green }

$fail = ($steps | Where-Object { $_.exit_code -ge 8 }).Count
if ($fail -gt 0) { exit 1 }
exit 0
