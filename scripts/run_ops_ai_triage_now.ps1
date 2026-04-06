param(
    [string]$TaskName = "\Bitcoin-Ops-Phase1-Chain-Daily",
    [int]$WaitSeconds = 20,
    [string]$OutPath = "C:\workspace\docs\final\artifacts\ai_triage_report_latest.md"
)

$ErrorActionPreference = "Stop"
$workspace = "C:\workspace"
Set-Location -LiteralPath $workspace

function Read-TailText {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$Tail = 120
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        return "(missing) $Path"
    }
    try {
        return (Get-Content -LiteralPath $Path -Tail $Tail -ErrorAction Stop) -join "`n"
    } catch {
        return "(read_error) $Path :: $($_.Exception.Message)"
    }
}

function Read-JsonCompact {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return "(missing) $Path"
    }
    try {
        $obj = Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json
        return ($obj | ConvertTo-Json -Depth 8)
    } catch {
        return "(parse_error) $Path :: $($_.Exception.Message)"
    }
}

Write-Host "[ai-triage] Running task: $TaskName"
schtasks /Run /TN $TaskName | Out-Null
Start-Sleep -Seconds $WaitSeconds

$taskSnapshot = schtasks /Query /TN $TaskName /V /FO LIST | Out-String
$readinessPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_readiness_latest.json"
$allGreenPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_latest.json"
$reconcilePath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\automation_registry_reconcile_latest.json"
$phase1ReportPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_chain_report_latest.json"
$wqLogPath = "C:\workspace\docs\final\artifacts\waiting_queue_btc_binance_daily_task.log"
$wqDualLogPath = "C:\workspace\docs\final\artifacts\waiting_queue_dual_market_daily_task.log"

$triageBundle = @"
Task snapshot (raw):
$taskSnapshot

ops_phase1_readiness_latest.json:
$(Read-JsonCompact -Path $readinessPath)

all_green_latest.json:
$(Read-JsonCompact -Path $allGreenPath)

automation_registry_reconcile_latest.json:
$(Read-JsonCompact -Path $reconcilePath)

ops_phase1_chain_report_latest.json:
$(Read-JsonCompact -Path $phase1ReportPath)

waiting_queue_btc_binance_daily_task.log (tail):
$(Read-TailText -Path $wqLogPath -Tail 80)

waiting_queue_dual_market_daily_task.log (tail):
$(Read-TailText -Path $wqDualLogPath -Tail 80)
"@

$bundlePath = "C:\workspace\docs\final\artifacts\ai_triage_bundle_latest.md"
Set-Content -LiteralPath $bundlePath -Value $triageBundle -Encoding UTF8

$prompt = @"
You are an operations triage assistant.
Analyze the evidence in this file: C:\workspace\docs\final\artifacts\ai_triage_bundle_latest.md

Goal:
1) Explain why Task Scheduler may show non-zero last_result while chain reports can still be healthy.
2) Identify the top 3 likely root causes from evidence only.
3) Provide no-edit mitigations first, then minimal code-level fixes if needed.
4) End with a short Go/No-Go recommendation for tomorrow 08:30 run.

Output format:
- ## Findings
- ## Root causes (ranked)
- ## Immediate mitigations (no code)
- ## Minimal code fixes (optional)
- ## Go/No-Go
"@

$agentCmd = Get-Command agent -ErrorAction SilentlyContinue
$cursorCmd = Get-Command cursor -ErrorAction SilentlyContinue
if (-not $agentCmd -and -not $cursorCmd) {
    $fallback = @"
## Findings
Cursor CLI agent command (`agent`) is not available in PATH on this host.

## Root causes (ranked)
1. Cannot run AI triage automatically because `agent` command is missing.

## Immediate mitigations (no code)
- Run `where.exe agent` and install/configure Cursor CLI agent.
- Re-run this script after CLI availability is confirmed.

## Minimal code fixes (optional)
- None required.

## Go/No-Go
NO_GO for AI triage automation until `agent` command is available.
"@
    Set-Content -LiteralPath $OutPath -Value $fallback -Encoding UTF8
    Write-Host "[ai-triage] Wrote fallback report: $OutPath"
    exit 2
}

$triageText = $null
if ($agentCmd) {
    $triageText = & agent -p $prompt --output-format text
} else {
    $triageText = & cursor agent -p $prompt --output-format text
}
if ($LASTEXITCODE -ne 0) {
    throw "agent triage failed with exit code $LASTEXITCODE"
}
if ([string]::IsNullOrWhiteSpace([string]$triageText)) {
    $triageText = @"
## Findings
Cursor CLI agent invocation returned no text output in non-interactive mode.

## Root causes (ranked)
1. This host resolves cursor but not standalone agent, and cursor agent -p ... appears to run without structured stdout.
2. Non-interactive prompt mode may require different CLI flags/version than currently installed (`Cursor 3.0.9`).
3. Ops evidence bundle was generated successfully, so only the AI handoff leg is degraded.

## Immediate mitigations (no code)
- Keep generating ai_triage_bundle_latest.md each run as a deterministic evidence packet.
- Run manual triage in current chat by attaching that bundle when needed.
- Validate supported non-interactive flags for `cursor agent` on this machine.

## Minimal code fixes (optional)
- Install/enable a CLI variant that supports agent -p ... --output-format text in terminal mode.
- Once confirmed, replace the fallback path with that exact command.

## Go/No-Go
GO for evidence capture automation, NO_GO for fully automated AI triage output until CLI output mode is confirmed.
"@
}

$header = @"
# AI Triage Report (Latest)

- task: $TaskName
- generated_utc: $([DateTimeOffset]::UtcNow.ToString("o"))
- mode: read-only analysis

"@

Set-Content -LiteralPath $OutPath -Value ($header + $triageText) -Encoding UTF8
Write-Host "[ai-triage] Wrote report: $OutPath"
exit 0
