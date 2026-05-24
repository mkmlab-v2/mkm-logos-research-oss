# Non-synthetic historical era blind eval ([HYPO], NON_GATING)
param(
    [switch]$TextBlind,
    [switch]$IncludeHardsetNews,
    [switch]$AppendRevalidation
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) { $py = "python" }

$args = @("$root\scripts\eval_logos_chronology_era_blind_v1.py")
if ($AppendRevalidation) {
    $args += "--append-revalidation", "$root\docs\final\artifacts\logos_symbolic_revalidation_report_latest.json"
}
if ($TextBlind) { $args += "--tag-mode", "text_blind" }
if ($IncludeHardsetNews) { $args += "--include-hardset-news" }

& $py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OK: docs/final/artifacts/logos_chronology_era_blind_eval_v1_latest.json"
