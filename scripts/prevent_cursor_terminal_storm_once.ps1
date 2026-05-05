param(
    [int]$MaxCursorPwsh = 1
)

$ErrorActionPreference = "SilentlyContinue"

$repoRoot = "C:\workspace"
$repairScript = Join-Path $repoRoot "scripts\repair_cursor_terminal_storm.ps1"
$logPath = Join-Path $repoRoot "reports\terminal_storm_guard_log.jsonl"

if (-not (Test-Path $repairScript)) {
    exit 0
}

$beforeCon = (Get-Process -Name conhost -ErrorAction SilentlyContinue | Measure-Object).Count
$beforePwsh = (Get-Process -Name pwsh -ErrorAction SilentlyContinue | Measure-Object).Count

$output = & powershell -NoProfile -ExecutionPolicy Bypass -File $repairScript -MaxCursorPwsh $MaxCursorPwsh

$afterCon = (Get-Process -Name conhost -ErrorAction SilentlyContinue | Measure-Object).Count
$afterPwsh = (Get-Process -Name pwsh -ErrorAction SilentlyContinue | Measure-Object).Count

$entry = [ordered]@{
    ts = (Get-Date).ToString("o")
    before = @{
        conhost = $beforeCon
        pwsh = $beforePwsh
    }
    after = @{
        conhost = $afterCon
        pwsh = $afterPwsh
    }
    repair_output = @($output)
}

$entry | ConvertTo-Json -Depth 6 -Compress | Add-Content -Path $logPath -Encoding utf8
