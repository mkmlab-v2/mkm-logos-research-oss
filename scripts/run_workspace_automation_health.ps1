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
    [switch]$IncludeBitcoinTradingOtelSmoke
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot

if ($BioSnpOnly) {
    $IncludeBioPaperSnpJoinSmoke = $true
    $SkipVaultMirror = $true
    $SkipMkmMemoryInventory = $true
    $SkipPhase1Readiness = $true
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

    Step "P0 / CONSTITUTION paths" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\verify_p0_constitution_gate_paths.ps1") -WorkspaceRoot $root
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

    Write-Host ""
    Write-Host "[run_workspace_automation_health] ALL OK" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
