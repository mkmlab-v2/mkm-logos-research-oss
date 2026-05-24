# P31d — score prior-day hypothesis log + evolution draft (dry-run)
param(
    [string]$DateKst = "",
    [switch]$SkipScore,
    [switch]$SkipEvolution,
    [string]$GateProfile = "minimal"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath "C:\workspace"

if (-not $SkipScore) {
    $scoreArgs = @("scripts/score_commander_hypothesis_branches_v1.py")
    if ($DateKst) { $scoreArgs += @("--date-kst", $DateKst) }
    & py @scoreArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipEvolution) {
    & py scripts/run_autonomous_evolution_loop_draft_v1.py --rail commander_hypothesis --gate-profile $GateProfile
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK: CommanderHypothesisEvolution v1"
