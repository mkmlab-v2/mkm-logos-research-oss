param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipVaultMirror,
    [switch]$SkipMkmMemoryInventory,
    [switch]$SkipPhase1Readiness,
    [switch]$StrictPhase1Readiness,
    [switch]$StrictReconcile,
    [switch]$IncludeCompressionKpi,
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

    # B-track news_observation contract smoke: on by default after P0 (skip with -SkipNewsObservationContractSmoke; auto-skipped for BioSnpOnly / Otel-smoke-only profiles).
    [switch]$SkipNewsObservationContractSmoke,

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
    [switch]$OnePlusThreeGateOnly
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

function Step([string]$Name, [scriptblock]$Block) {
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit $LASTEXITCODE)"
    }
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

    if (-not $SkipNewsObservationContractSmoke -and -not $BioSnpOnly -and -not $BitcoinTradingOtelSmokeOnly -and -not $TrackCMacroFusionSmokeOnly) {
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

    if (-not $BitcoinTradingOtelSmokeOnly -and -not $TrackCMacroFusionSmokeOnly) {
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
