<#
.SYNOPSIS
  PID/command-line radar: classify workspace-related Python processes as Memory / Trading / Other.

.DESCRIPTION
  Get-Process does not expose command-line arguments. This script uses Win32_Process.CommandLine
  so the same python.exe can be distinguished (e.g. athena_memory_server vs bitcoin-trading).

  Buckets:
  - Memory: command line matches athena_memory_server (MCP memory server hosts UFT-heavy paths)
  - Trading: command line references projects/.../bitcoin-trading path, or dual_regime_api / integration/dual_regime (reduces false positives vs bare "dual_regime" text)
  - Other: other Python/py invocations under WorkspaceRoot or matching mcp-servers / tools

.PARAMETER Watch
  Refresh every IntervalSeconds until Ctrl+C.

.PARAMETER ShowAllWorkspacePython
  Include any process whose CommandLine contains WorkspaceRoot and looks like Python/py (noisier).

.EXAMPLE
  & c:\workspace\scripts\diag_pid_tracker.ps1
.EXAMPLE
  & c:\workspace\scripts\diag_pid_tracker.ps1 -Watch -IntervalSeconds 3
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Watch,
    [ValidateRange(1, 60)]
    [int]$IntervalSeconds = 2,
    [switch]$ShowAllWorkspacePython
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Resolve-WorkspaceRoot {
    param([string]$Path)
    try {
        return (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
    } catch {
        return $Path
    }
}

function Test-LooksLikePythonCommandLine {
    param([string]$CommandLine)
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $false }
    return $CommandLine -match '(?i)(pythonw?\.exe|py\.exe)(\s|")'
}

function Test-IsTradingCommandLine {
    param([string]$CommandLine)
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $false }
    $c = $CommandLine
    # Path segment .../projects/bitcoin-trading/... (avoid loose "projects" + "bitcoin-trading" anywhere in string)
    if ($c -match '(?i)projects[\\/]bitcoin-trading(?:[\\/]|"|$)') { return $true }
    # Directory name bitcoin-trading with path separators (not substring inside other tokens)
    if ($c -match '(?i)[\\/]bitcoin-trading[\\/]') { return $true }
    # Explicit module paths (avoid matching unrelated "dual_regime" substrings)
    if ($c -match '(?i)dual_regime_api(\.py)?') { return $true }
    if ($c -match '(?i)integration[\\/]dual_regime') { return $true }
    return $false
}

function Get-DiagCategory {
    param(
        [string]$CommandLine,
        [string]$WorkspaceRootResolved
    )
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return 'Other' }
    $c = $CommandLine
    if ($c -match '(?i)athena_memory_server') { return 'Memory' }
    if (Test-IsTradingCommandLine -CommandLine $c) { return 'Trading' }
    return 'Other'
}

function Format-CommandLinePreview {
    param(
        [string]$CommandLine,
        [int]$MaxLength = 120
    )
    if ($null -eq $CommandLine) { return '(null)' }
    if ($CommandLine.Length -le $MaxLength) { return $CommandLine }
    return $CommandLine.Substring(0, $MaxLength) + [char]0x2026 # ellipsis
}

function Get-TrackedProcessRows {
    param(
        [string]$WorkspaceRootResolved,
        [bool]$ShowAllWorkspacePython
    )

    $rootNorm = $WorkspaceRootResolved.TrimEnd('\', '/')
    $rootPattern = [regex]::Escape($rootNorm) -replace '\\', '[\\/]'

    $all = Get-CimInstance -ClassName Win32_Process -ErrorAction SilentlyContinue
    if (-not $all) { return @() }

    $rows = foreach ($p in $all) {
        $cl = $p.CommandLine
        if ([string]::IsNullOrWhiteSpace($cl)) { continue }

        $hasKeyScript = ($cl -match '(?i)athena_memory_server') -or (Test-IsTradingCommandLine -CommandLine $cl)
        $hasMcpPath = $cl -match '(?i)mcp-servers'
        $underRoot = $cl -match $rootPattern
        $isPy = Test-LooksLikePythonCommandLine -CommandLine $cl

        if ($ShowAllWorkspacePython) {
            if (-not ($underRoot -and $isPy)) { continue }
        } else {
            if (-not ($hasKeyScript -or $hasMcpPath -or ($underRoot -and $isPy))) { continue }
        }

        [PSCustomObject]@{
            Category            = Get-DiagCategory -CommandLine $cl -WorkspaceRootResolved $WorkspaceRootResolved
            ProcessId           = [int]$p.ProcessId
            Name                = $p.Name
            CommandLinePreview  = Format-CommandLinePreview -CommandLine $cl
            CommandLine         = $cl
        }
    }

    return @($rows | Sort-Object Category, ProcessId)
}

function Show-DiagDashboard {
    param(
        [string]$WorkspaceRootResolved,
        [bool]$ShowAllWorkspacePython,
        [bool]$ClearScreen
    )

    if ($ClearScreen) { Clear-Host }
    Write-Host "diag_pid_tracker - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "WorkspaceRoot: $WorkspaceRootResolved" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "FACT: UFT-heavy memory paths run in whichever process hosts athena_memory_server (see Memory bucket)." -ForegroundColor DarkYellow
    Write-Host ""

    $rows = Get-TrackedProcessRows -WorkspaceRootResolved $WorkspaceRootResolved -ShowAllWorkspacePython $ShowAllWorkspacePython

    foreach ($bucket in @('Memory', 'Trading', 'Other')) {
        $color = switch ($bucket) {
            'Memory' { 'Green' }
            'Trading' { 'Yellow' }
            default { 'Gray' }
        }
        Write-Host "=== $bucket ===" -ForegroundColor $color
        $sub = @($rows | Where-Object { $_.Category -eq $bucket })
        if ($sub.Count -eq 0) {
            Write-Host "  (none matched)" -ForegroundColor DarkGray
            Write-Host ""
            continue
        }
        $sub | Select-Object ProcessId, Name, CommandLinePreview | Format-Table -AutoSize
    }

    Write-Host "Tip: -Watch refreshes every IntervalSeconds. -ShowAllWorkspacePython widens the net." -ForegroundColor DarkGray
}

$workspaceResolved = Resolve-WorkspaceRoot -Path $WorkspaceRoot

if ($Watch) {
    while ($true) {
        Show-DiagDashboard -WorkspaceRootResolved $workspaceResolved -ShowAllWorkspacePython:([bool]$ShowAllWorkspacePython) -ClearScreen $true
        Start-Sleep -Seconds $IntervalSeconds
    }
} else {
    Show-DiagDashboard -WorkspaceRootResolved $workspaceResolved -ShowAllWorkspacePython:([bool]$ShowAllWorkspacePython) -ClearScreen $false
}
