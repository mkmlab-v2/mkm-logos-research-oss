param(
    [string]$GatesConfigPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\constitution_gates_v1.json",
    [string]$Phase1ReportPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_chain_report_latest.json",
    [string]$RiskProfilePath = "C:\workspace\projects\bitcoin-trading\memory\v2\risk\risk_profile_fact_safe_latest.json",
    [string]$ReconcileScriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\reconcile_automation_registry.ps1",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\constitution_gates_result_latest.json",
    [switch]$SkipPhase1Report,
    [switch]$SkipRegistry,
    [switch]$SkipRiskProfile
)

$ErrorActionPreference = "Stop"

$checks = @()
$allOk = $true

# --- Gate 1: Phase 1 report overall_chain_ok ---
if (-not $SkipPhase1Report) {
    if (-not (Test-Path -LiteralPath $Phase1ReportPath)) {
        $checks += [ordered]@{ gate = "phase1_report"; ok = $false; detail = "missing_report_file" }
        $allOk = $false
    } else {
        try {
            $rep = Get-Content -LiteralPath $Phase1ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $chainOk = $false
            if ($rep.PSObject.Properties.Name -contains "overall_chain_ok") {
                $chainOk = [bool]$rep.overall_chain_ok
            }
            if ($chainOk) {
                $checks += [ordered]@{ gate = "phase1_report"; ok = $true; detail = "overall_chain_ok_true" }
            } else {
                $checks += [ordered]@{ gate = "phase1_report"; ok = $false; detail = "overall_chain_ok_false"; outcome = [string]$rep.outcome }
                $allOk = $false
            }
        } catch {
            $checks += [ordered]@{ gate = "phase1_report"; ok = $false; detail = "parse_error" }
            $allOk = $false
        }
    }
} else {
    $checks += [ordered]@{ gate = "phase1_report"; ok = $null; detail = "skipped" }
}

# --- Gate 2: automation registry reconcile (no drift) ---
if (-not $SkipRegistry) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $ReconcileScriptPath
    $rex = $LASTEXITCODE
    if ($rex -eq 0) {
        $checks += [ordered]@{ gate = "automation_registry_reconcile"; ok = $true; detail = "exit_0_no_drift" }
    } else {
        $checks += [ordered]@{ gate = "automation_registry_reconcile"; ok = $false; detail = "exit_nonzero"; exit_code = $rex }
        $allOk = $false
    }
} else {
    $checks += [ordered]@{ gate = "automation_registry_reconcile"; ok = $null; detail = "skipped" }
}

# --- Gate 3: risk profile allowlist ---
if (-not $SkipRiskProfile) {
    if (-not (Test-Path -LiteralPath $GatesConfigPath)) {
        $checks += [ordered]@{ gate = "risk_profile_allowlist"; ok = $false; detail = "missing_gates_config" }
        $allOk = $false
    } elseif (-not (Test-Path -LiteralPath $RiskProfilePath)) {
        $checks += [ordered]@{ gate = "risk_profile_allowlist"; ok = $false; detail = "missing_risk_profile" }
        $allOk = $false
    } else {
        $cfg = Get-Content -LiteralPath $GatesConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $allowed = @($cfg.allowed_risk_combinations)
        if ($null -eq $allowed -or $allowed.Count -eq 0) {
            $checks += [ordered]@{ gate = "risk_profile_allowlist"; ok = $null; detail = "allowlist_empty_skipped" }
        } else {
            $rp = Get-Content -LiteralPath $RiskProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
            $src = [string]$rp.source
            $mode = [string]$rp.mode
            $matched = $false
            foreach ($pair in $allowed) {
                if ([string]$pair.source -eq $src -and [string]$pair.mode -eq $mode) {
                    $matched = $true
                    break
                }
            }
            if ($matched) {
                $checks += [ordered]@{ gate = "risk_profile_allowlist"; ok = $true; detail = "source_mode_allowed"; source = $src; mode = $mode }
            } else {
                $checks += [ordered]@{ gate = "risk_profile_allowlist"; ok = $false; detail = "source_mode_not_allowed"; source = $src; mode = $mode }
                $allOk = $false
            }
        }
    }
} else {
    $checks += [ordered]@{ gate = "risk_profile_allowlist"; ok = $null; detail = "skipped" }
}

$payload = [ordered]@{
    schema = "constitution_gates_result_v1"
    ts_utc = [DateTimeOffset]::UtcNow.ToString("o")
    runner = "projects/bitcoin-trading/ops/windows-rehearsal/verify_constitution_gates.ps1"
    all_ok = $allOk
    checks = $checks
    notes = "Gate1=ops_phase1_chain_report overall_chain_ok; Gate2=reconcile_automation_registry exit 0; Gate3=risk profile in constitution_gates_v1 allowed_risk_combinations."
}

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
$payload | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Host ("[constitution-gates] WROTE: {0}" -f $OutputPath)

if (-not $allOk) {
    Write-Host "[constitution-gates] FAIL — see checks in result JSON." -ForegroundColor Red
    exit 1
}
Write-Host "[constitution-gates] PASS"
exit 0
