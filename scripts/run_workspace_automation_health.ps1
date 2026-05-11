param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipVaultMirror,
    [switch]$SkipMkmMemoryInventory,
    [switch]$SkipPhase1Readiness,
    [switch]$StrictPhase1Readiness,
    [switch]$StrictReconcile,
    [switch]$IncludeCompressionKpi,
    # Optional: rebuild fallback trigger 24h summary (compression stub telemetry).
    [switch]$IncludeFallbackTriggerTelemetry,
    [double]$FallbackPostCutoffWarnRate = 0.15,
    [switch]$IncludeLiteralTrack,
    [switch]$SkipHydrationMix,
    [switch]$SkipCompressionAlarm,

    [switch]$IncludeExternalDriveGovernance,

    [switch]$IncludeGitSanity,
    [switch]$StrictGitSanity,

    [switch]$IncludeGitOriginMainSync,
    [switch]$StrictGitOriginMainSync,

    # Optional: fast pytest subset for weather B-track triplet + fusion-search-json (not run by default; ~tens of seconds).
    [switch]$IncludeWeatherPipelineSmoke,

    # Optional: prophecy evolution watchdog pytest (staleness + JSONL tail streak/EMA; few hundred ms).
    [switch]$IncludeProphecyEvolutionWatchdogSmoke,

    # Optional: package_b chain smoke (v1 lens + v2 balanced/attack + margins summary).
    [switch]$IncludeMyeongniPackageBSmoke,

    # B-track news_observation contract smoke: on by default after P0 (skip with -SkipNewsObservationContractSmoke; auto-skipped for BioSnpOnly / Otel-smoke-only / TrackCMacroFusionSmokeOnly / McpHygieneProbeOnly / MkmControlIntegritySmokeOnly / KmPhysicianCdsEnvelopeSmokeOnly / VaFusionControlIntegritySmokeOnly profiles).
    [switch]$SkipNewsObservationContractSmoke,

    # Optional: Run-BTrackDomainFeedbackSmoke.ps1 — general_prophecy pytest + weather triplet + news (if default news smoke already ran in this session, wrapper uses -SkipNews).
    [switch]$IncludeBTrackDomainFeedbackSmoke,

    # Optional: bio PMID paper SNP sidecar join smoke (no network; sub-second).
    [switch]$IncludeBioPaperSnpJoinSmoke,
    # Shortcut profile: run only P0 path gate + automation registry reconcile + Bio SNP smoke.
    [switch]$BioSnpOnly,

    # Optional: run full weather external gate (chain -> comparison -> reliability -> go/no-go audit append).
    [switch]$IncludeWeatherFullGate,
    [string]$WeatherFullGateCsvPath = "",
    [string]$WeatherFullGateForecastsJsonlPath = "",
    [string]$WeatherFullGateRunLabel = "external_real_week_health_gate_v1",
    [string]$WeatherFullGateBaselineProfile = "synthetic_hypo_120d",
    [switch]$WeatherFullGateAutoColumnsCsv,
    [switch]$WeatherFullGateStrictSchemaCsv,

    # Optional: bitcoin-trading OpenTelemetry smoke (console or OTLP; few seconds if packages installed).
    [switch]$IncludeBitcoinTradingOtelSmoke,
    # Shortcut profile: run only bitcoin-trading OTel smoke (skip broader health checks).
    [switch]$BitcoinTradingOtelSmokeOnly,

    # Shortcut profile: P0 paths + Track C fusion smoke only (skip vault/memory/phase1/news defaults).
    [switch]$TrackCMacroFusionSmokeOnly,
    # Shortcut profile: P0 paths + XAI contract daily gate only.
    [switch]$XaiContractGateOnly,

    # Optional: secure envelope external_kms readiness checks (env/command hook; optional HTTP smoke).
    [switch]$IncludeSecureEnvelopeExternalKmsReadiness,
    [string]$SecureEnvelopeExternalKmsBaseUrl = "",

    # Optional: MKM AI v2 final promotion readiness gate.
    [switch]$IncludeMkmAiV2Readiness,

    # Optional: MKM AI final ops guard check (hard fail if final posture degraded).
    [switch]$IncludeMkmAiFinalOpsGuard,

    # Optional: MKM Track C client handoff guard (hard fail if delivery packet degrades).
    [switch]$IncludeMkmAiTrackCHandoffGuard,

    # Optional: BL-004 gate - fail on A/B rail contamination in A-track decision inputs.
    [switch]$IncludeMkmABContaminationGate,

    # Optional: BL-005 alert - detect prolonged Track C WATCH streak.
    [switch]$IncludeMkmTrackCWatchProlongedAlert,

    # Optional: fail when Track C dashboard forward pipeline health is not PASS.
    [switch]$IncludeMacroRiskForwardPipelineHealth,

    # Optional: run full Track C macro fusion chain (network for Fragility/exodus proxy legs; ~1–3+ min). Uses -SkipGateAlert -SkipExodusSourceFetch.
    [switch]$IncludeTrackCMacroFusionSmoke,

    # Optional: Operational readiness checklist builder (Judge-ready done-condition snapshot).
    [switch]$IncludeOperationalReadinessChecklist,

    # Optional: fail when central-memory read acknowledgement is missing/stale.
    [switch]$IncludeCentralMemoryReadCheck,
    [double]$CentralMemoryReadMaxAgeHours = 24.0,

    # Optional: Day1 secret exposure survey gate (strict exit on findings).
    [switch]$IncludeSecretExposureSurvey,

    # Optional: XAI output-contract daily gate (pass-rate + failures artifact + HOLD alert path).
    [switch]$IncludeXaiContractDailyGate,
    [double]$XaiContractMinPassRate = 0.95,

    # Optional: 1+3 threshold daily gate (7d/14d + warning/critical).
    [switch]$IncludeOnePlusThreeDailyGate,
    # Shortcut profile: P0 paths + 1+3 threshold daily gate only.
    [switch]$OnePlusThreeGateOnly,

    # Optional: MKM Control-Integrity Golden/LoRA pipeline pytest (aggregate, promotion gate, oracle inference timing; no GPU).
    [switch]$IncludeMkmControlIntegritySmoke,
    # Shortcut profile: P0 paths + Control-Integrity smoke pytest only.
    [switch]$MkmControlIntegritySmokeOnly,

    # Optional: KM physician CDS assist envelope v1 pytest quartet (+ automation_registry MKM tasks; jsonschema; few seconds).
    [switch]$IncludeKmPhysicianCdsEnvelopeSmoke,
    # Shortcut profile: P0 paths + CDS envelope pytest pair only.
    [switch]$KmPhysicianCdsEnvelopeSmokeOnly,

    # Optional: VA trajectory -> cross-lens fusion -> control-integrity audit chain smoke.
    [switch]$IncludeVaFusionControlIntegritySmoke,
    # Shortcut profile: P0 paths + VA fusion control-integrity chain smoke only.
    [switch]$VaFusionControlIntegritySmokeOnly,

    # Optional: NotebookLM MCP hygiene probe (prereq + JSON; no MCP get_health in probe).
    [switch]$IncludeMcpHygieneProbe,
    [switch]$IncludeMcpHygieneProbeRepair,
    # Shortcut profile: P0 + MCP probe only (skip vault/memory/phase1/news/reconcile by default).
    [switch]$McpHygieneProbeOnly,

    # Optional: VPS SSH disk smoke (Invoke-VpsOpsSmoke_v1.ps1; unset MKM_VPS_HOST = skip).
    [switch]$IncludeVpsOpsSmoke,
    # With IncludeVpsOpsSmoke: SSH failure fails health (default is SoftFail).
    [switch]$IncludeVpsOpsSmokeHardFail,

    # Safe ops surface (Invoke-SafeOpsSurfaceCheck.ps1): recommended ON for full runs (OFF for shortcut profiles). Use -SkipSafeOpsSurfaceCheck to omit. Use -IncludeSafeOpsSurfaceCheck / -IncludeSafeOpsSurfaceCheckWithVps to force from ProbeOnly or add VPS.
    [switch]$SkipSafeOpsSurfaceCheck,
    [switch]$IncludeSafeOpsSurfaceCheck,
    [switch]$IncludeSafeOpsSurfaceCheckWithVps,

    # Optional: heartbeat / bundle-cycle JSON staleness (runs outside bundle success tail; see scripts/check_amsaeng_eosa_artifact_staleness_v1.py).
    [switch]$IncludeAmsaengArtifactStaleness
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot

if ($BioSnpOnly) {
    $IncludeBioPaperSnpJoinSmoke = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
}

if ($BitcoinTradingOtelSmokeOnly) {
    $IncludeBitcoinTradingOtelSmoke = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
}

if ($TrackCMacroFusionSmokeOnly) {
    $IncludeTrackCMacroFusionSmoke = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
    $SkipNewsObservationContractSmoke = $true
}

if ($XaiContractGateOnly) {
    $IncludeXaiContractDailyGate = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
    $SkipNewsObservationContractSmoke = $true
}

if ($OnePlusThreeGateOnly) {
    $IncludeOnePlusThreeDailyGate = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
    $SkipNewsObservationContractSmoke = $true
}

if ($MkmControlIntegritySmokeOnly) {
    $IncludeMkmControlIntegritySmoke = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
    $SkipNewsObservationContractSmoke = $true
}

if ($KmPhysicianCdsEnvelopeSmokeOnly) {
    $IncludeKmPhysicianCdsEnvelopeSmoke = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
    $SkipNewsObservationContractSmoke = $true
}

if ($VaFusionControlIntegritySmokeOnly) {
    $IncludeVaFusionControlIntegritySmoke = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
    $SkipNewsObservationContractSmoke = $true
}

if ($McpHygieneProbeOnly) {
    $IncludeMcpHygieneProbe = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
    $SkipNewsObservationContractSmoke = $true
    $IncludeBTrackDomainFeedbackSmoke = $false
}

# Recommended default: run SafeOps on full health runs; shortcut profiles skip unless explicit Include* / IncludeWithVps.
$shortcutForSafeOps = $BioSnpOnly -or $BitcoinTradingOtelSmokeOnly -or $TrackCMacroFusionSmokeOnly -or $XaiContractGateOnly -or $OnePlusThreeGateOnly -or $MkmControlIntegritySmokeOnly -or $KmPhysicianCdsEnvelopeSmokeOnly -or $VaFusionControlIntegritySmokeOnly
$runSafeOps = $false
$runSafeOpsWithVps = $false
if (-not $SkipSafeOpsSurfaceCheck) {
    if ($IncludeSafeOpsSurfaceCheckWithVps) {
        $runSafeOps = $true
        $runSafeOpsWithVps = $true
    }
    elseif ($IncludeSafeOpsSurfaceCheck) {
        $runSafeOps = $true
    }
    elseif (-not $shortcutForSafeOps -and -not $McpHygieneProbeOnly) {
        $runSafeOps = $true
    }
}

function Step([string]$Name, [scriptblock]$Block) {
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit $LASTEXITCODE)"
    }
}

function Test-DecisionLoggedToday {
    param(
        [string]$DecisionsLogPath,
        [string]$MissionId,
        [string]$Stage,
        [string]$Decision,
        [string]$Actor
    )
    if (-not (Test-Path -LiteralPath $DecisionsLogPath)) {
        return $false
    }
    $todayUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
    try {
        $lines = Get-Content -LiteralPath $DecisionsLogPath -Encoding UTF8
        foreach ($line in $lines) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $obj = $line | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($null -eq $obj) { continue }
            $ts = [string]$obj.timestamp
            if ([string]::IsNullOrWhiteSpace($ts)) { continue }
            if (-not $ts.StartsWith($todayUtc)) { continue }
            if (($obj.mission_id -eq $MissionId) -and ($obj.stage -eq $Stage) -and ($obj.decision -eq $Decision) -and ($obj.actor -eq $Actor)) {
                return $true
            }
        }
    }
    catch {
        return $false
    }
    return $false
}

try {
    if ($IncludeGitSanity) {
        $gitSan = Join-Path $root "scripts\Verify-GitWorkspaceSanity.ps1"
        if (Test-Path -LiteralPath $gitSan) {
            Step "Git / exclude / remote sanity" {
                if ($StrictGitSanity) {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $gitSan -WorkspaceRoot $root -Strict
                }
                else {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $gitSan -WorkspaceRoot $root
                }
            }
        }
    }

    if ($IncludeGitOriginMainSync) {
        $gitSan = Join-Path $root "scripts\Verify-GitWorkspaceSanity.ps1"
        if (Test-Path -LiteralPath $gitSan) {
            Step "Git origin/main drift check (fetch + compare)" {
                if ($StrictGitOriginMainSync) {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $gitSan -WorkspaceRoot $root -CheckOriginMainSync -Strict
                }
                else {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $gitSan -WorkspaceRoot $root -CheckOriginMainSync
                }
            }
        }
    }

    if (-not $BitcoinTradingOtelSmokeOnly) {
        Step "P0 / CONSTITUTION paths" {
            & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\verify_p0_constitution_gate_paths.ps1") -WorkspaceRoot $root
        }
    }

    if ($IncludeMcpHygieneProbe) {
        $mcpProbe = Join-Path $root "scripts\Invoke-McpHygieneProbe.ps1"
        $mcpOut = Join-Path $root "reports\mcp_hygiene_probe_latest.json"
        if (Test-Path -LiteralPath $mcpProbe) {
            $mcpLabel = "NotebookLM MCP hygiene probe (prereq JSON"
            if ($IncludeMcpHygieneProbeRepair) { $mcpLabel += " + repair" }
            $mcpLabel += ")"
            Step $mcpLabel {
                if ($IncludeMcpHygieneProbeRepair) {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $mcpProbe -WorkspaceRoot $root -OutJson $mcpOut -Repair
                }
                else {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $mcpProbe -WorkspaceRoot $root -OutJson $mcpOut
                }
            }
        }
        else {
            Write-Host ""
            Write-Host "=== NotebookLM MCP hygiene probe ===" -ForegroundColor Yellow
            Write-Host "SKIP: Invoke-McpHygieneProbe.ps1 not found"
        }
    }

    if ($IncludeVpsOpsSmoke) {
        $vpsSmoke = Join-Path $root "scripts\Invoke-VpsOpsSmoke_v1.ps1"
        if (Test-Path -LiteralPath $vpsSmoke) {
            $vpsLabel = "VPS ops smoke (SSH disk JSON"
            if (-not $IncludeVpsOpsSmokeHardFail) { $vpsLabel += "; SoftFail" }
            $vpsLabel += ")"
            Step $vpsLabel {
                if ($IncludeVpsOpsSmokeHardFail) {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $vpsSmoke -WorkspaceRoot $root
                }
                else {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $vpsSmoke -WorkspaceRoot $root -SoftFail
                }
            }
        }
        else {
            Write-Host ""
            Write-Host "=== VPS ops smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: Invoke-VpsOpsSmoke_v1.ps1 not found"
        }
    }

    if ($runSafeOps) {
        $safeOps = Join-Path $root "scripts\Invoke-SafeOpsSurfaceCheck.ps1"
        if (Test-Path -LiteralPath $safeOps) {
            Write-Host ""
            $safeLabel = "Safe ops surface (verify + staleness + reports/safe_ops_surface_check_latest.json"
            if ($runSafeOpsWithVps) { $safeLabel += "; +VPS smoke" }
            $safeLabel += ")"
            Write-Host "=== $safeLabel ===" -ForegroundColor Cyan
            if ($runSafeOpsWithVps) {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $safeOps -WorkspaceRoot $root -IncludeVpsSmoke
            }
            else {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $safeOps -WorkspaceRoot $root
            }
            $safeExit = $LASTEXITCODE
            if ($safeExit -eq 2) {
                throw "Safe ops surface CRITICAL (exit 2). See reports/safe_ops_surface_check_latest.json"
            }
            if ($safeExit -eq 1) {
                Write-Host "WARN: Safe ops surface degraded (exit 1). See reports/safe_ops_surface_check_latest.json" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host ""
            Write-Host "SKIP: Invoke-SafeOpsSurfaceCheck.ps1 not found" -ForegroundColor Yellow
        }
    }

    if ($IncludeAmsaengArtifactStaleness) {
        $stalenessPy = Join-Path $root "scripts\check_amsaeng_eosa_artifact_staleness_v1.py"
        if (Test-Path -LiteralPath $stalenessPy) {
            Write-Host ""
            Write-Host "=== Amsaeng-Eosa artifact staleness probe (heartbeat / bundle cycle JSON) ===" -ForegroundColor Cyan
            & py $stalenessPy --workspace-root $root
            $stExit = $LASTEXITCODE
            if ($stExit -eq 2) {
                throw "Amsaeng artifact staleness CRITICAL (exit 2). See reports/amsaeng_eosa_staleness_probe_latest.json"
            }
            if ($stExit -eq 1) {
                Write-Host "WARN: Amsaeng artifacts stale or degraded (exit 1). See reports/amsaeng_eosa_staleness_probe_latest.json" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host ""
            Write-Host "SKIP: check_amsaeng_eosa_artifact_staleness_v1.py not found" -ForegroundColor Yellow
        }
    }

    if ($McpHygieneProbeOnly) {
        $probeDone = "[run_workspace_automation_health] McpHygieneProbeOnly: finished after P0 + MCP probe"
        if ($IncludeVpsOpsSmoke) { $probeDone += " + VPS ops smoke" }
        if ($runSafeOps) { $probeDone += " + Safe ops surface" }
        $probeDone += "."
        Write-Host ""
        Write-Host $probeDone -ForegroundColor Green
        exit 0
    }

    if (-not $SkipNewsObservationContractSmoke -and -not $BioSnpOnly -and -not $BitcoinTradingOtelSmokeOnly -and -not $TrackCMacroFusionSmokeOnly -and -not $McpHygieneProbeOnly -and -not $MkmControlIntegritySmokeOnly -and -not $KmPhysicianCdsEnvelopeSmokeOnly -and -not $VaFusionControlIntegritySmokeOnly) {
        $ns = Join-Path $root "scripts\Run-NewsObservationContractSmoke.ps1"
        if (Test-Path -LiteralPath $ns) {
            Step "B-track news_observation contract smoke (default)" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $ns
            }
        }
        else {
            Write-Host ""
            Write-Host "=== News observation contract smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: Run-NewsObservationContractSmoke.ps1 not found"
        }
    }

    $btProfileSkip = $BioSnpOnly -or $BitcoinTradingOtelSmokeOnly -or $TrackCMacroFusionSmokeOnly -or $McpHygieneProbeOnly -or $MkmControlIntegritySmokeOnly -or $KmPhysicianCdsEnvelopeSmokeOnly -or $VaFusionControlIntegritySmokeOnly
    if ($IncludeBTrackDomainFeedbackSmoke -and -not $btProfileSkip) {
        $bt = Join-Path $root "scripts\Run-BTrackDomainFeedbackSmoke.ps1"
        if (Test-Path -LiteralPath $bt) {
            $newsRanThisSession = (-not $SkipNewsObservationContractSmoke) -and (-not $btProfileSkip)
            if ($newsRanThisSession) {
                Step "B-track domain feedback smoke (general_prophecy + weather; news covered above)" {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $bt -SkipNews
                }
            }
            else {
                Step "B-track domain feedback smoke (full)" {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $bt
                }
            }
        }
        else {
            Write-Host ""
            Write-Host "=== B-track domain feedback smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: Run-BTrackDomainFeedbackSmoke.ps1 not found"
        }
    }

    if (-not $SkipMkmMemoryInventory) {
        $inv = Join-Path $root "scripts\inventory_mkm_memory_report.py"
        if (Test-Path -LiteralPath $inv) {
            Step "MKM memory inventory (.mkm-memory -> reports/memory)" {
                # Default cap keeps health runs fast on large trees; full scan: MKM_MEMORY_INVENTORY_FULL=1
                $extra = @()
                if ($env:MKM_MEMORY_INVENTORY_FULL -eq "1") {
                    $extra = @()
                }
                elseif ($env:MKM_MEMORY_INVENTORY_MAX_FILES -match '^\d+$') {
                    $extra += "--max-files"
                    $extra += $env:MKM_MEMORY_INVENTORY_MAX_FILES
                }
                else {
                    $extra += "--max-files"
                    $extra += "8000"
                }
                & py $inv @extra
            }
        }
        else {
            Write-Host ""
            Write-Host "=== MKM memory inventory ===" -ForegroundColor Yellow
            Write-Host "SKIP: inventory_mkm_memory_report.py not found"
        }
    }

    if (-not $SkipVaultMirror) {
        $vault = $env:MKM_VAULT_ROOT
        if ([string]::IsNullOrWhiteSpace($vault)) {
            $vault = "G:\공유 드라이브\MKM_DATA_VAULT\vault"
        } else {
            $vault = $vault.Trim().TrimEnd('\')
        }
        if (Test-Path -LiteralPath $vault) {
            Step "NotebookLM vault mirror" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1")
            }
        }
        else {
            Write-Host ""
            Write-Host "=== NotebookLM vault mirror ===" -ForegroundColor Yellow
            Write-Host "SKIP: Vault not mounted ($vault)"
        }
    }

    if (-not $SkipPhase1Readiness) {
        $ops = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal"
        $vr = Join-Path $ops "verify_ops_phase1_operational_readiness.ps1"
        if (Test-Path -LiteralPath $vr) {
            Step "Phase 1 operational readiness" {
                if ($StrictPhase1Readiness) {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $vr -Strict
                } else {
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $vr
                }
            }
        }
    }

    if (-not $BitcoinTradingOtelSmokeOnly -and -not $TrackCMacroFusionSmokeOnly -and -not $McpHygieneProbeOnly) {
        Write-Host ""
        Write-Host "=== Automation registry reconcile ===" -ForegroundColor Cyan
        $rec = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\reconcile_automation_registry.ps1"
        & powershell -NoProfile -ExecutionPolicy Bypass -File $rec
        $re = $LASTEXITCODE
        if ($re -ne 0) {
            $msg = "reconcile_automation_registry exit $re (scheduler drift?)"
            if ($StrictReconcile) { throw $msg }
            Write-Host "WARN: $msg" -ForegroundColor Yellow
        }
    }

    if ($IncludeCompressionKpi) {
        $cc = Join-Path $root "scripts\run_compression_automation_chain.ps1"
        $literalNote = if ($IncludeLiteralTrack) { " + literal track" } else { "" }
        Step "Compression KPI chain (default + KPI summary + hydration mix$literalNote)" {
            # Invoke in-process (avoid nested powershell.exe mangling switch types).
            & $cc -WorkspaceRoot $root -SkipHydrationMix:$SkipHydrationMix -SkipCompressionAlarm:$SkipCompressionAlarm -IncludeLiteralTrack:$IncludeLiteralTrack
        }
    }

    if ($IncludeFallbackTriggerTelemetry -or $IncludeCompressionKpi) {
        $fb = Join-Path $root "scripts\build_fallback_trigger_daily_summary_v1.py"
        if (Test-Path -LiteralPath $fb) {
            $fallbackProfile = Join-Path $root "docs\final\artifacts\fallback_trigger_threshold_profile_latest.json"
            $prevCutoff = $env:FALLBACK_TRIGGER_CUTOFF_UTC
            $cutoffApplied = $false
            if (Test-Path -LiteralPath $fallbackProfile) {
                try {
                    $fp = Get-Content -LiteralPath $fallbackProfile -Raw -Encoding UTF8 | ConvertFrom-Json
                    $cutoffRaw = [string]$fp.generated_at_utc
                    if (-not [string]::IsNullOrWhiteSpace($cutoffRaw)) {
                        $env:FALLBACK_TRIGGER_CUTOFF_UTC = $cutoffRaw
                        $cutoffApplied = $true
                    }
                }
                catch {
                    Write-Host "WARN: fallback profile parse failed for cutoff propagation ($($_.Exception.Message))" -ForegroundColor Yellow
                }
            }
            Step "Fallback trigger telemetry (24h summary)" {
                & py $fb
            }
            if ($cutoffApplied) {
                if ([string]::IsNullOrWhiteSpace($prevCutoff)) {
                    Remove-Item Env:FALLBACK_TRIGGER_CUTOFF_UTC -ErrorAction SilentlyContinue
                }
                else {
                    $env:FALLBACK_TRIGGER_CUTOFF_UTC = $prevCutoff
                }
            }
            $fbOut = Join-Path $root "docs\final\artifacts\fallback_trigger_daily_summary_latest.json"
            if (-not (Test-Path -LiteralPath $fbOut)) {
                throw "missing $fbOut after build_fallback_trigger_daily_summary_v1.py"
            }
            try {
                $fbDoc = Get-Content -LiteralPath $fbOut -Raw -Encoding UTF8 | ConvertFrom-Json
                $pcs = $fbDoc.post_cutoff_summary
                if ($null -ne $pcs) {
                    $postWarnThresholdRaw = $env:FALLBACK_POST_CUTOFF_WARN_RATE
                    $postWarnThreshold = $FallbackPostCutoffWarnRate
                    if (-not [string]::IsNullOrWhiteSpace($postWarnThresholdRaw)) {
                        try { $postWarnThreshold = [double]$postWarnThresholdRaw } catch { $postWarnThreshold = $FallbackPostCutoffWarnRate }
                    }
                    $postRate = [double]$pcs.fallback_trigger_rate
                    if ($postRate -gt $postWarnThreshold) {
                        Write-Host "WARN: post_cutoff fallback_trigger_rate high ($postRate > $postWarnThreshold)" -ForegroundColor Yellow
                        $decisionLogger = Join-Path $root "scripts\log_agent_decision.py"
                        $decisionsLog = Join-Path $root "reports\agent_decisions_log.jsonl"
                        if ((Test-Path -LiteralPath $decisionLogger) -and -not (Test-DecisionLoggedToday -DecisionsLogPath $decisionsLog -MissionId "fallback_post_cutoff_watch_v1" -Stage "fallback_post_cutoff_watch" -Decision "WARN_POST_CUTOFF_RATE_HIGH" -Actor "workspace-health-runner")) {
                            & py $decisionLogger --repo-root $root --mission-id "fallback_post_cutoff_watch_v1" --stage "fallback_post_cutoff_watch" --decision "WARN_POST_CUTOFF_RATE_HIGH" --evidence-path $fbOut --actor "workspace-health-runner" --risk-level "medium" --note ("post_cutoff_rate={0};threshold={1}" -f $postRate, $postWarnThreshold) | Out-Null
                        }
                    }
                }
            }
            catch {
                Write-Host "WARN: unable to parse fallback summary for post-cutoff warning ($($_.Exception.Message))" -ForegroundColor Yellow
            }

            $fallbackWatchReport = Join-Path $root "scripts\build_fallback_post_cutoff_watch_report_v1.py"
            if (Test-Path -LiteralPath $fallbackWatchReport) {
                $fallbackProfile = Join-Path $root "docs\final\artifacts\fallback_trigger_threshold_profile_latest.json"
                $prevBaselineReset = $env:FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC
                $baselineResetApplied = $false
                if (Test-Path -LiteralPath $fallbackProfile) {
                    try {
                        $fpWatch = Get-Content -LiteralPath $fallbackProfile -Raw -Encoding UTF8 | ConvertFrom-Json
                        $baselineRaw = [string]$fpWatch.generated_at_utc
                        if (-not [string]::IsNullOrWhiteSpace($baselineRaw)) {
                            $env:FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC = $baselineRaw
                            $baselineResetApplied = $true
                        }
                    }
                    catch {
                        Write-Host "WARN: fallback profile parse failed for baseline reset propagation ($($_.Exception.Message))" -ForegroundColor Yellow
                    }
                }
                & py $fallbackWatchReport | Out-Null
                if ($baselineResetApplied) {
                    if ([string]::IsNullOrWhiteSpace($prevBaselineReset)) {
                        Remove-Item Env:FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC -ErrorAction SilentlyContinue
                    }
                    else {
                        $env:FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC = $prevBaselineReset
                    }
                }
                $watchJson = Join-Path $root "docs\final\artifacts\fallback_post_cutoff_watch_report_latest.json"
                if (Test-Path -LiteralPath $watchJson) {
                    try {
                        $watch = Get-Content -LiteralPath $watchJson -Raw -Encoding UTF8 | ConvertFrom-Json
                        $signal = [string](($watch.summary).signal)
                        if ($signal -eq "CRITICAL") {
                            Write-Host "WARN: fallback post-cutoff watch signal is CRITICAL - escalation recommended." -ForegroundColor Yellow
                            $decisionLogger = Join-Path $root "scripts\log_agent_decision.py"
                            $decisionsLog = Join-Path $root "reports\agent_decisions_log.jsonl"
                            if ((Test-Path -LiteralPath $decisionLogger) -and -not (Test-DecisionLoggedToday -DecisionsLogPath $decisionsLog -MissionId "fallback_post_cutoff_watch_v1" -Stage "fallback_post_cutoff_escalation" -Decision "CRITICAL_SIGNAL_ESCALATION" -Actor "workspace-health-runner")) {
                                & py $decisionLogger --repo-root $root --mission-id "fallback_post_cutoff_watch_v1" --stage "fallback_post_cutoff_escalation" --decision "CRITICAL_SIGNAL_ESCALATION" --evidence-path $watchJson --actor "workspace-health-runner" --risk-level "high" --note "signal=CRITICAL from fallback post-cutoff watch report" | Out-Null
                            }
                            $criticalFailRaw = [string]$env:FALLBACK_POST_CUTOFF_CRITICAL_FAIL
                            if ($criticalFailRaw -match '^(1|true|yes)$') {
                                throw "fallback post-cutoff signal is CRITICAL (FALLBACK_POST_CUTOFF_CRITICAL_FAIL=$criticalFailRaw)"
                            }
                        }
                    }
                    catch {
                        Write-Host "WARN: fallback post-cutoff watch parse failed ($($_.Exception.Message))" -ForegroundColor Yellow
                    }
                }
                $fallbackDiagnosis = Join-Path $root "scripts\build_fallback_post_cutoff_diagnosis_v1.py"
                if (Test-Path -LiteralPath $fallbackDiagnosis) {
                    & py $fallbackDiagnosis | Out-Null
                }

                $fallbackObservationStatus = Join-Path $root "scripts\build_fallback_post_cutoff_observation_status_v1.py"
                if (Test-Path -LiteralPath $fallbackObservationStatus) {
                    & py $fallbackObservationStatus | Out-Null
                    $obsJson = Join-Path $root "docs\final\artifacts\fallback_post_cutoff_observation_status_latest.json"
                    if (Test-Path -LiteralPath $obsJson) {
                        try {
                            $obs = Get-Content -LiteralPath $obsJson -Raw -Encoding UTF8 | ConvertFrom-Json
                            $obsDecision = [string]$obs.decision
                            if ($obsDecision -eq "GO_OBSERVATION_COMPLETE") {
                                Write-Host "Fallback post-cutoff observation status: GO (observation complete)"
                            }
                            elseif ($obsDecision -eq "HOLD_OBSERVATION_CONTINUE") {
                                Write-Host "WARN: fallback post-cutoff observation status is HOLD (observation continue)." -ForegroundColor Yellow
                            }
                        }
                        catch {
                            Write-Host "WARN: fallback post-cutoff observation status parse failed ($($_.Exception.Message))" -ForegroundColor Yellow
                        }
                    }
                }
            }
        }
        else {
            Write-Host "SKIP: build_fallback_trigger_daily_summary_v1.py not found" -ForegroundColor Yellow
        }
    }

    if ($IncludeExternalDriveGovernance) {
        $gov = Join-Path $root "scripts\Invoke-ExternalDrivesGovernance.ps1"
        if (Test-Path -LiteralPath $gov) {
            Step "E:/F: governance (quick)" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $gov -WorkspaceRoot $root
            }
        }
    }

    if ($IncludeWeatherPipelineSmoke) {
        $wt = Join-Path $root "tests\test_weather_gt_triplet_chain_smoke.py"
        if (Test-Path -LiteralPath $wt) {
            Step "Weather triplet pipeline smoke (fusion-search-json + optimizer)" {
                & py -m pytest $wt -k "fusion_search_json or optimize_weather_lens_fusion" -q --tb=line
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Weather pipeline smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: test_weather_gt_triplet_chain_smoke.py not found"
        }
    }

    if ($IncludeProphecyEvolutionWatchdogSmoke) {
        $wd = Join-Path $root "tests\test_check_prophecy_evolution_watchdog_v1.py"
        if (Test-Path -LiteralPath $wd) {
            Step "Prophecy evolution watchdog smoke (check_prophecy_evolution_watchdog_v1 contract)" {
                & py -m pytest $wd -q --tb=short
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Prophecy evolution watchdog smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: test_check_prophecy_evolution_watchdog_v1.py not found"
        }
    }

    if ($IncludeMkmControlIntegritySmoke) {
        $cit = Join-Path $root "tests\test_mkm_control_integrity_pipeline_smoke_v1.py"
        if (Test-Path -LiteralPath $cit) {
            Step "MKM Control-Integrity pipeline smoke (aggregate, promotion gate, oracle inference timing)" {
                & py -m pytest $cit -q --tb=short
            }
        }
        else {
            Write-Host ""
            Write-Host "=== MKM Control-Integrity pipeline smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: test_mkm_control_integrity_pipeline_smoke_v1.py not found"
        }
    }

    if ($IncludeKmPhysicianCdsEnvelopeSmoke) {
        $cds1 = Join-Path $root "tests\test_km_physician_cds_assist_envelope_v1.py"
        $cds2 = Join-Path $root "tests\test_build_km_physician_cds_assist_envelope_v1.py"
        $cds3 = Join-Path $root "tests\test_run_km_physician_cds_assist_envelope_batch_v1.py"
        $cds4 = Join-Path $root "tests\test_automation_registry_json_v1.py"
        if ((Test-Path -LiteralPath $cds1) -and (Test-Path -LiteralPath $cds2) -and (Test-Path -LiteralPath $cds3) -and (Test-Path -LiteralPath $cds4)) {
            Step "KM physician CDS assist envelope v1 (schema + builder + JSONL batch + automation registry pytest; dual-regime / fact-lock parity)" {
                & py -m pytest $cds1 $cds2 $cds3 $cds4 -q --tb=short
            }
        }
        else {
            Write-Host ""
            Write-Host "=== KM physician CDS envelope smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: CDS envelope pytest file(s) missing"
        }
    }

    if ($IncludeVaFusionControlIntegritySmoke) {
        $vaChain = Join-Path $root "tests\test_va_fusion_control_integrity_chain_v1.py"
        if (Test-Path -LiteralPath $vaChain) {
            Step "VA->fusion->control-integrity chain smoke (B-track, CONSTITUTION 3.8.4)" {
                & py -m pytest $vaChain -q --tb=short
            }
        }
        else {
            Write-Host ""
            Write-Host "=== VA->fusion->control-integrity chain smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: test_va_fusion_control_integrity_chain_v1.py not found"
        }
    }

    if ($IncludeMyeongniPackageBSmoke) {
        $pkgb = Join-Path $root "scripts\run_myeongni_package_b_smoke_v1.ps1"
        if (Test-Path -LiteralPath $pkgb) {
            Step "Myeongni package_b chain smoke" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $pkgb -WorkspaceRoot $root
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Myeongni package_b chain smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: run_myeongni_package_b_smoke_v1.ps1 not found"
        }
    }

    if ($IncludeBioPaperSnpJoinSmoke) {
        $bio = Join-Path $root "tests\test_bio_paper_snp_join_chain_smoke_v1.py"
        $bioChainCli = Join-Path $root "tests\test_run_bio_paper_snp_sidecar_export_and_apply_v1_cli.py"
        $bioEpmcCli = Join-Path $root "tests\test_run_bio_epmc_catalog_and_label_merge_v1_cli.py"
        $bioGeno = Join-Path $root "tests\test_check_bio_genotype_paper_snp_overlap_v1.py"
        $bioNorm = Join-Path $root "tests\test_normalize_bio_genotype_long_v1.py"
        $bioReady = Join-Path $root "tests\test_build_bio_dna_promotion_readiness_v1.py"
        $bioReadyChain = Join-Path $root "tests\test_run_bio_dna_readiness_chain_v1.py"
        $bioSweep = Join-Path $root "tests\test_run_bio_dna_promotion_threshold_sweep_v1.py"
        if (Test-Path -LiteralPath $bio) {
            Step "Bio paper SNP join smoke (join/apply + chain CLI + EPMC CLI + genotype overlap + readiness gate)" {
                $tests = @($bio)
                if (Test-Path -LiteralPath $bioChainCli) {
                    $tests += $bioChainCli
                }
                else {
                    Write-Host "WARN: missing CLI guard test ($bioChainCli)" -ForegroundColor Yellow
                }
                if (Test-Path -LiteralPath $bioEpmcCli) {
                    $tests += $bioEpmcCli
                }
                else {
                    Write-Host "WARN: missing CLI guard test ($bioEpmcCli)" -ForegroundColor Yellow
                }
                if (Test-Path -LiteralPath $bioGeno) {
                    $tests += $bioGeno
                }
                else {
                    Write-Host "WARN: missing genotype overlap test ($bioGeno)" -ForegroundColor Yellow
                }
                if (Test-Path -LiteralPath $bioNorm) {
                    $tests += $bioNorm
                }
                else {
                    Write-Host "WARN: missing genotype normalize test ($bioNorm)" -ForegroundColor Yellow
                }
                if (Test-Path -LiteralPath $bioReady) {
                    $tests += $bioReady
                }
                else {
                    Write-Host "WARN: missing DNA readiness gate test ($bioReady)" -ForegroundColor Yellow
                }
                if (Test-Path -LiteralPath $bioReadyChain) {
                    $tests += $bioReadyChain
                }
                else {
                    Write-Host "WARN: missing DNA readiness chain test ($bioReadyChain)" -ForegroundColor Yellow
                }
                if (Test-Path -LiteralPath $bioSweep) {
                    $tests += $bioSweep
                }
                else {
                    Write-Host "WARN: missing DNA threshold sweep test ($bioSweep)" -ForegroundColor Yellow
                }
                & py -m pytest @tests -q --tb=line
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Bio paper SNP join smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: test_bio_paper_snp_join_chain_smoke_v1.py not found"
        }
    }

    if ($IncludeWeatherFullGate) {
        $full = Join-Path $root "scripts\run_weather_btrack_external_real_week_full_gate_v1.ps1"
        if (Test-Path -LiteralPath $full) {
            $csv = $WeatherFullGateCsvPath
            if ([string]::IsNullOrWhiteSpace($csv)) {
                $csv = Join-Path $root "tests\fixtures\weather_ground_truth_synthetic_120d_input.csv"
            }
            $fc = $WeatherFullGateForecastsJsonlPath
            if ([string]::IsNullOrWhiteSpace($fc)) {
                $fc = Join-Path $root "tests\fixtures\weather_synthetic_120d_external_lens_hypo_v1.jsonl"
            }
            Step "Weather full gate (external chain + reliability + go/no-go audit)" {
                $args = @(
                    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $full,
                    "-CsvPath", $csv,
                    "-ForecastsJsonlPath", $fc,
                    "-RunLabel", $WeatherFullGateRunLabel,
                    "-BaselineProfile", $WeatherFullGateBaselineProfile
                )
                if ($WeatherFullGateAutoColumnsCsv) { $args += "-AutoColumnsCsv" }
                if ($WeatherFullGateStrictSchemaCsv) { $args += "-StrictSchemaCsv" }
                & powershell @args
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Weather full gate ===" -ForegroundColor Yellow
            Write-Host "SKIP: run_weather_btrack_external_real_week_full_gate_v1.ps1 not found"
        }
    }

    if ($IncludeBitcoinTradingOtelSmoke) {
        $otelSmoke = Join-Path $root "projects\bitcoin-trading\ops\metrics\smoke_otel.ps1"
        if (Test-Path -LiteralPath $otelSmoke) {
            Step "Bitcoin trading OTel smoke (ops/metrics/smoke_otel.ps1)" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $otelSmoke
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Bitcoin trading OTel smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: smoke_otel.ps1 not found at $otelSmoke"
        }
    }

    if ($IncludeSecureEnvelopeExternalKmsReadiness) {
        $sec = Join-Path $root "scripts\check_secure_envelope_external_kms_readiness_v1.py"
        if (Test-Path -LiteralPath $sec) {
            Step "Secure envelope external_kms readiness" {
                $args = @($sec)
                if (-not [string]::IsNullOrWhiteSpace($SecureEnvelopeExternalKmsBaseUrl)) {
                    $args += "--base-url"
                    $args += $SecureEnvelopeExternalKmsBaseUrl
                }
                & py @args
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Secure envelope external_kms readiness ===" -ForegroundColor Yellow
            Write-Host "SKIP: check_secure_envelope_external_kms_readiness_v1.py not found"
        }
    }

    if ($IncludeMkmAiV2Readiness) {
        $mkmV2 = Join-Path $root "scripts\run_mkm_ai_v2_readiness_check.ps1"
        if (Test-Path -LiteralPath $mkmV2) {
            Step "MKM AI v2 readiness gate" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $mkmV2 -WorkspaceRoot $root
            }
        }
        else {
            Write-Host ""
            Write-Host "=== MKM AI v2 readiness gate ===" -ForegroundColor Yellow
            Write-Host "SKIP: run_mkm_ai_v2_readiness_check.ps1 not found"
        }
    }

    if ($IncludeMkmAiFinalOpsGuard) {
        $guard = Join-Path $root "scripts\check_mkm_ai_final_ops_guard.py"
        if (Test-Path -LiteralPath $guard) {
            Step "MKM AI final ops guard" {
                & py $guard --workspace-root $root --min-pass-rate 95 --min-sample-count 3
            }
        }
        else {
            Write-Host ""
            Write-Host "=== MKM AI final ops guard ===" -ForegroundColor Yellow
            Write-Host "SKIP: check_mkm_ai_final_ops_guard.py not found"
        }
    }

    if ($IncludeMkmAiTrackCHandoffGuard) {
        $trackcGuard = Join-Path $root "scripts\check_mkm_trackc_client_handoff_guard.py"
        if (Test-Path -LiteralPath $trackcGuard) {
            Step "MKM AI Track C client handoff guard" {
                & py $trackcGuard --workspace-root $root
            }
        }
        else {
            Write-Host ""
            Write-Host "=== MKM AI Track C client handoff guard ===" -ForegroundColor Yellow
            Write-Host "SKIP: check_mkm_trackc_client_handoff_guard.py not found"
        }
    }

    if ($IncludeMkmABContaminationGate) {
        $abGate = Join-Path $root "scripts\check_mkm_atrack_btrack_contamination_gate_v1.py"
        if (Test-Path -LiteralPath $abGate) {
            Step "MKM A/B contamination gate (BL-004)" {
                & py $abGate --a-track-json (Join-Path $root "docs\final\artifacts\a_track_go_nogo_status_latest.json") --output-json (Join-Path $root "docs\final\artifacts\mkm_atrack_btrack_contamination_gate_latest.json")
            }
        }
        else {
            Write-Host ""
            Write-Host "=== MKM A/B contamination gate (BL-004) ===" -ForegroundColor Yellow
            Write-Host "SKIP: check_mkm_atrack_btrack_contamination_gate_v1.py not found"
        }
    }

    if ($IncludeMkmTrackCWatchProlongedAlert) {
        $watchAlert = Join-Path $root "scripts\alert_mkm_trackc_watch_prolonged_v1.py"
        if (Test-Path -LiteralPath $watchAlert) {
            Step "MKM Track C prolonged WATCH alert (BL-005)" {
                & py $watchAlert --dashboard-json (Join-Path $root "docs\final\artifacts\mkm_trackc_ops_dashboard_latest.json") --kpi-contract-json (Join-Path $root "docs\final\artifacts\mkm_trackc_watch_exit_kpi_contract_latest.json") --state-log-jsonl (Join-Path $root "reports\mkm_trackc_watch_state_log.jsonl") --output-json (Join-Path $root "docs\final\artifacts\mkm_trackc_watch_prolonged_alert_latest.json")
            }
        }
        else {
            Write-Host ""
            Write-Host "=== MKM Track C prolonged WATCH alert (BL-005) ===" -ForegroundColor Yellow
            Write-Host "SKIP: alert_mkm_trackc_watch_prolonged_v1.py not found"
        }
    }

    if ($IncludeMacroRiskForwardPipelineHealth) {
        $forwardGate = Join-Path $root "scripts\check_macro_risk_forward_pipeline_health_v1.py"
        if (Test-Path -LiteralPath $forwardGate) {
            Step "Macro risk forward pipeline health gate" {
                & py $forwardGate --dashboard-json (Join-Path $root "docs\final\artifacts\mkm_trackc_ops_dashboard_latest.json") --output-json (Join-Path $root "docs\final\artifacts\macro_risk_forward_pipeline_health_gate_latest.json")
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Macro risk forward pipeline health gate ===" -ForegroundColor Yellow
            Write-Host "SKIP: check_macro_risk_forward_pipeline_health_v1.py not found"
        }
    }

    if ($IncludeTrackCMacroFusionSmoke) {
        $fusionSmoke = Join-Path $root "scripts\Invoke-TrackCMacroDailyFusion_v1.ps1"
        if (Test-Path -LiteralPath $fusionSmoke) {
            Step "Track C macro daily fusion smoke (Invoke-TrackCMacroDailyFusion_v1 -SkipGateAlert -SkipExodusSourceFetch)" {
                & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $fusionSmoke -SkipGateAlert -SkipExodusSourceFetch
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Track C macro daily fusion smoke ===" -ForegroundColor Yellow
            Write-Host "SKIP: Invoke-TrackCMacroDailyFusion_v1.ps1 not found"
        }
    }

    if ($IncludeOperationalReadinessChecklist) {
        $opsChecklist = Join-Path $root "scripts\build_operational_readiness_checklist_v1.py"
        if (Test-Path -LiteralPath $opsChecklist) {
            Step "Operational readiness checklist build" {
                & py $opsChecklist --workspace-root $root
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Operational readiness checklist build ===" -ForegroundColor Yellow
            Write-Host "SKIP: build_operational_readiness_checklist_v1.py not found"
        }
    }

    if ($IncludeCentralMemoryReadCheck) {
        $cmr = Join-Path $root "scripts\check_central_memory_read_ack_v1.py"
        if (Test-Path -LiteralPath $cmr) {
            Step "Central memory read acknowledgement check" {
                & py $cmr --workspace-root $root --max-age-hours $CentralMemoryReadMaxAgeHours
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Central memory read acknowledgement check ===" -ForegroundColor Yellow
            Write-Host "SKIP: check_central_memory_read_ack_v1.py not found"
        }
    }

    if ($IncludeSecretExposureSurvey) {
        $secretSurvey = Join-Path $root "scripts\run_security_secret_exposure_survey_v1.py"
        if (Test-Path -LiteralPath $secretSurvey) {
            Step "Secret exposure survey gate (strict)" {
                & py $secretSurvey --strict-exit --dispatch-on warning
            }
        }
        else {
            Write-Host ""
            Write-Host "=== Secret exposure survey gate ===" -ForegroundColor Yellow
            Write-Host "SKIP: run_security_secret_exposure_survey_v1.py not found"
        }
    }

    if ($IncludeXaiContractDailyGate) {
        $xaiGate = Join-Path $root "scripts\run_xai_contract_daily_gate_v1.ps1"
        if (Test-Path -LiteralPath $xaiGate) {
            Step "XAI contract daily gate (min pass-rate=$XaiContractMinPassRate)" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $xaiGate -WorkspaceRoot $root -MinPassRate $XaiContractMinPassRate -BootstrapIfMissing
            }
        }
        else {
            Write-Host ""
            Write-Host "=== XAI contract daily gate ===" -ForegroundColor Yellow
            Write-Host "SKIP: run_xai_contract_daily_gate_v1.ps1 not found"
        }
    }

    if ($IncludeOnePlusThreeDailyGate) {
        $onePlusThreeGate = Join-Path $root "scripts\run_one_plus_three_daily_gate_v1.ps1"
        if (Test-Path -LiteralPath $onePlusThreeGate) {
            Step "1+3 threshold daily gate (7d/14d + warning/critical)" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $onePlusThreeGate -WorkspaceRoot $root
            }
        }
        else {
            Write-Host ""
            Write-Host "=== 1+3 threshold daily gate ===" -ForegroundColor Yellow
            Write-Host "SKIP: run_one_plus_three_daily_gate_v1.ps1 not found"
        }
    }

    $signalLight = Join-Path $root "scripts\build_security_signal_light_v1.py"
    if (Test-Path -LiteralPath $signalLight) {
        Step "Security signal light snapshot" {
            & py $signalLight
        }
    }
    else {
        Write-Host ""
        Write-Host "=== Security signal light snapshot ===" -ForegroundColor Yellow
        Write-Host "SKIP: build_security_signal_light_v1.py not found"
    }

    Write-Host ""
    Write-Host "[run_workspace_automation_health] ALL OK" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
