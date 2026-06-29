#Requires -Version 5.1
<#
.SYNOPSIS
  B-track daily hero board chain — 5 slots morning/evening [HYPO].

.EXAMPLE
  pwsh -File scripts\Run-BtrackDailyHeroBoardChain_v1.ps1 -Phase All
  pwsh -File scripts\Run-BtrackDailyHeroBoardChain_v1.ps1 -Phase Evening -SkipLlmInsight
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [ValidateSet("Morning", "Evening", "All")]
    [string]$Phase = "All",
    [string]$YearMonth = "",
    [switch]$SkipLlmInsight,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$phaseArg = $Phase.ToLower()
$args = @("scripts/run_btrack_daily_hero_board_chain_v1.py", "--phase", $phaseArg)
if ($YearMonth) { $args += @("--year-month", $YearMonth) }
if ($SkipLlmInsight) { $args += "--skip-llm-insight" }

& $py @args
if ($LASTEXITCODE -ne 0 -and $Strict) { exit $LASTEXITCODE }
exit 0
