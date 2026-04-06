param(
  [string]$OutJson = "C:\workspace\docs\final\artifacts\cursor_agent_headless_smoke_latest.json",
  [string]$OutMd = "C:\workspace\docs\final\artifacts\cursor_agent_headless_smoke_latest.md"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath "C:\workspace"

function Invoke-TestCase {
  param([string]$Id, [string]$Command)
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $output = (& cmd /c $Command 2>&1 | Out-String)
  $ErrorActionPreference = $prevEap
  $exitCode = $LASTEXITCODE
  $sw.Stop()
  [ordered]@{
    id = $Id
    command = $Command
    exit_code = $exitCode
    ok = ($exitCode -eq 0)
    elapsed_ms = [int]$sw.ElapsedMilliseconds
    output = ($output.Trim())
    output_nonempty = (-not [string]::IsNullOrWhiteSpace($output))
  }
}

$cases = @(
  [ordered]@{ id = "help"; cmd = 'cursor agent --help' },
  [ordered]@{ id = "positional_prompt"; cmd = 'cursor agent "Say only: OK_HEADLESS_TEST"' },
  [ordered]@{ id = "stdin_dash"; cmd = 'echo Say only: OK_HEADLESS_TEST|cursor agent -' },
  [ordered]@{ id = "prompt_flag"; cmd = 'cursor agent -p "Say only: OK_HEADLESS_TEST"' },
  [ordered]@{ id = "prompt_flag_output_format"; cmd = 'cursor agent -p "Say only: OK_HEADLESS_TEST" --output-format text' }
)

$results = @()
foreach ($c in $cases) { $results += Invoke-TestCase -Id $c.id -Command $c.cmd }

$headlessTextCandidates = @($results | Where-Object {
  if (-not $_.ok) { return $false }
  if ($_.id -eq "help") { return $false }
  if (-not $_.output_nonempty) { return $false }
  $out = [string]$_.output
  if ($out -match "Warning:\s+'.+'\s+is not in the list of known options") { return $false }
  if ($out -match "^Reading from stdin via:\s+") { return $false }
  return $true
})
$decision = if ($headlessTextCandidates.Count -gt 0) { "GO" } else { "NO_GO" }
$rationale = if ($decision -eq "GO") { "At least one non-help command produced non-empty stdout." } else { "No non-help command produced reliable stdout text for headless triage." }

$payload = [ordered]@{
  schema = "cursor_agent_headless_smoke_v1"
  generated_utc = [DateTimeOffset]::UtcNow.ToString("o")
  cursor_path = (Get-Command cursor -ErrorAction SilentlyContinue).Source
  decision = $decision
  rationale = $rationale
  results = $results
}
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutJson -Encoding UTF8

$md = @()
$md += "# Cursor Agent Headless Smoke"
$md += ""
$md += "- generated_utc: $($payload.generated_utc)"
$md += "- cursor_path: $($payload.cursor_path)"
$md += "- decision: $decision"
$md += "- rationale: $rationale"
$md += ""
$md += "## Cases"
foreach ($r in $results) {
  $md += "- [$($r.id)] exit=$($r.exit_code) ok=$($r.ok) output_nonempty=$($r.output_nonempty)"
}
$md += ""
$md += "## Raw Outputs (trimmed)"
foreach ($r in $results) {
  $md += ""
  $md += "### $($r.id)"
  $md += "command: $($r.command)"
  if ([string]::IsNullOrWhiteSpace($r.output)) {
    $md += "(empty)"
  } else {
    $text = [string]$r.output
    if ($text.Length -gt 1200) { $text = $text.Substring(0, 1200) + "...(truncated)" }
    $md += '```text'
    $md += $text
    $md += '```'
  }
}
([string]::Join([Environment]::NewLine, $md)) | Set-Content -LiteralPath $OutMd -Encoding UTF8

Write-Host "[smoke] wrote $OutJson"
Write-Host "[smoke] wrote $OutMd"
Write-Host "[smoke] decision=$decision"
exit 0
