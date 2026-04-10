param(
    [string]$DeviceProfile = "generic_lab",
    [switch]$IncludeObsidianContext,
    [switch]$StrictMirror,
    [switch]$AllowLegacyObsoleteSources,
    [switch]$SkipNotebookDedupe
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

Write-Host "=== [1/5] NotebookLM source mirror ===" -ForegroundColor Cyan
$syncArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $workspaceRoot "scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1")
)
if ($IncludeObsidianContext) { $syncArgs += "-IncludeObsidianContext" }
if ($StrictMirror) { $syncArgs += "-Strict" }
& powershell @syncArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== [2/5] Hub B weekly mirror log chain ===" -ForegroundColor Cyan
$hubArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $workspaceRoot "scripts\Invoke-HubBWeeklyMirror.ps1")
)
if ($StrictMirror) { $hubArgs += "-Strict" }
& powershell @hubArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== [3/5] Compression weekly governance chain ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $workspaceRoot "scripts\run_compression_weekly_governance_chain.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== [4/5] RS channel policy gate ($DeviceProfile) ===" -ForegroundColor Cyan
& py (Join-Path $workspaceRoot "scripts\check_mkm_l1_rs_policy_gate.py") "--device-profile" $DeviceProfile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== [5/6] L1 codebook bypass smoke bench ===" -ForegroundColor Cyan
$l1BypassBenchScript = Join-Path $workspaceRoot "scripts\run_l1_codebook_bypass_bench.py"
$l1BypassBenchOutPath = Join-Path $workspaceRoot "docs\final\artifacts\l1_codebook_bypass_bench_latest.json"
$l1Bench = $null
$l1BenchStatus = "NOT_RUN"
if (Test-Path -LiteralPath $l1BypassBenchScript) {
    & py $l1BypassBenchScript "--out" $l1BypassBenchOutPath
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $l1BypassBenchOutPath)) {
        $l1Bench = Get-Content -LiteralPath $l1BypassBenchOutPath -Raw | ConvertFrom-Json
        $l1BenchStatus = "OK"
    }
    else {
        $l1BenchStatus = "RUN_FAIL"
    }
}
else {
    $l1BenchStatus = "SCRIPT_MISSING"
}

Write-Host "=== [6/6] Final status digest ===" -ForegroundColor Cyan
$digestPath = Join-Path $workspaceRoot "docs\final\artifacts\notebook_compression_full_chain_status_latest.json"
$briefPath = Join-Path $workspaceRoot "docs\final\artifacts\notebook_compression_daily_brief_latest.md"
$compressionPath = Join-Path $workspaceRoot "docs\final\artifacts\compression_weekly_governance_report_latest.json"
$policyPath = Join-Path $workspaceRoot "docs\final\artifacts\mkm_l1_rs_policy_gate_latest.json"
$hubLogPath = Join-Path $workspaceRoot "reports\hub_b_weekly_mirror_log.jsonl"
$hygienePath = Join-Path $workspaceRoot "docs\final\artifacts\notebook_source_hygiene_latest.json"
$dedupeScriptPath = Join-Path $workspaceRoot "scripts\notebooklm_dedupe_sources_by_title.ps1"
$l1BypassLiteralMin = 1.0
$l1SideChannelSpikePath = Join-Path $workspaceRoot "docs\final\artifacts\l1_permutation_channel_integrated_spike_latest.json"
$l1SideChannelSpikeBriefLine = "- [FACT] L1 permutation side-channel integrated spike: artifact not found at docs/final/artifacts/l1_permutation_channel_integrated_spike_latest.json — run ``py scripts\run_l1_permutation_channel_integrated_spike.py`` to generate."
if (Test-Path -LiteralPath $l1SideChannelSpikePath) {
    try {
        $l1Sc = Get-Content -LiteralPath $l1SideChannelSpikePath -Raw | ConvertFrom-Json
        $minRestore = ($l1Sc.rows | ForEach-Object { [double]$_.exact_restore_rate } | Measure-Object -Minimum).Minimum
        $modes = ($l1Sc.rows | ForEach-Object { $_.mode }) -join ", "
        $wireExtra = "[HYPO] JSON UTF-8 overhead is baseline wire proxy; install msgpack+zstandard and refresh spike for msgpack/zstd byte rows (schema v2)."
        if ($l1Sc.wire_codecs -and $l1Sc.wire_codecs.msgpack_available) {
            $wireExtra = "[FACT] Artifact includes msgpack byte stats; zstd if zstandard_available (research_only — see claims.payload_wire_format)."
        }
        $l1SideChannelSpikeBriefLine = "- [FACT] L1 permutation side-channel integrated spike (as of $($l1Sc.generated_at_utc)): min exact_restore_rate=$minRestore across modes ($modes) with side metadata; inverse order oov→typo→swap. $wireExtra docs/final/artifacts/l1_permutation_channel_integrated_spike_latest.json"
    }
    catch {
        $l1SideChannelSpikeBriefLine = "- [FACT] L1 permutation side-channel integrated spike: could not parse $l1SideChannelSpikePath — refresh with ``py scripts\run_l1_permutation_channel_integrated_spike.py``."
    }
}

$compression = Get-Content -LiteralPath $compressionPath -Raw | ConvertFrom-Json
$policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
$hubLast = Get-Content -LiteralPath $hubLogPath | Select-Object -Last 1
$hub = $null
if ($hubLast) { $hub = $hubLast | ConvertFrom-Json }

$status = [ordered]@{
    schema = "notebook_compression_full_chain_status_v1"
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
    inputs = [ordered]@{
        device_profile = $DeviceProfile
        include_obsidian_context = [bool]$IncludeObsidianContext
        strict_mirror = [bool]$StrictMirror
        allow_legacy_obsolete_sources = [bool]$AllowLegacyObsoleteSources
        skip_notebook_dedupe = [bool]$SkipNotebookDedupe
    }
    notebook = [ordered]@{
        hub_b_weekly_mirror_exit_code = if ($hub) { $hub.exit_code } else { $null }
        hub_b_weekly_mirror_ts_utc = if ($hub) { $hub.ts_utc } else { $null }
    }
    compression = [ordered]@{
        go_no_go = $compression.decision_snapshot.go_no_go
        rollout_policy = $compression.decision_snapshot.rollout_policy
        track_a_jaccard_guardrail_ok = $compression.headline.track_a_universal.jaccard_guardrail_ok
        track_b_literal_jaccard_guardrail_ok = $compression.headline.track_b_literal.jaccard_guardrail_ok
    }
    rs_policy_gate = [ordered]@{
        status = $policy.status
        block_ratio = $policy.metrics.block_ratio
        selected_profile = $policy.inputs.device_profile
    }
    l1_codebook_bypass_bench = [ordered]@{
        status = $l1BenchStatus
        out_path = $l1BypassBenchOutPath
        literal_exact_rate = if ($l1Bench) { $l1Bench.metrics.literal_exact_rate } else { $null }
        full_exact_rate = if ($l1Bench) { $l1Bench.metrics.full_exact_rate } else { $null }
        literal_exact_min_required = $l1BypassLiteralMin
        soft_gate = "PASS"
    }
    notebook_dedupe = [ordered]@{
        enabled = [bool](-not $SkipNotebookDedupe)
        status = "NOT_RUN"
        details = @()
    }
    note = "Research/operations chain only. No production auto-promotion."
}

if (-not $SkipNotebookDedupe) {
    if (-not (Test-Path -LiteralPath $dedupeScriptPath)) {
        $status.notebook_dedupe.status = "SCRIPT_MISSING"
    } else {
        $dedupeNotebookIds = @(
            "347e5cbe-0ade-4615-9aac-8747d4fa644e", # 작전지휘부
            "c5f9aef1-6cd6-4c3b-9c57-d1f2a62e3201", # 압축
            "b79929a2-8742-42a8-a4d7-06523e12935d"  # 비트코인
        )
        $dedupeErrors = 0
        foreach ($nbId in $dedupeNotebookIds) {
            $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $dedupeScriptPath -NotebookId $nbId -Confirm 2>&1
            $ok = ($LASTEXITCODE -eq 0)
            if (-not $ok) { $dedupeErrors++ }
            $status.notebook_dedupe.details += [ordered]@{
                notebook_id = $nbId
                ok = $ok
                output = ($out | Out-String).Trim()
            }
        }
        $status.notebook_dedupe.status = if ($dedupeErrors -eq 0) { "OK" } else { "PARTIAL_FAIL" }
    }
}

if ($status.l1_codebook_bypass_bench.status -eq "OK") {
    $literalExact = $status.l1_codebook_bypass_bench.literal_exact_rate
    if ($null -eq $literalExact -or [double]$literalExact -lt $l1BypassLiteralMin) {
        $status.l1_codebook_bypass_bench.soft_gate = "HOLD_RESEARCH"
    }
}
else {
    $status.l1_codebook_bypass_bench.soft_gate = "HOLD_RESEARCH"
}

$status | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $digestPath -Encoding utf8
Write-Host "WROTE: $digestPath" -ForegroundColor Green

$hygiene = [ordered]@{
    schema = "notebook_source_hygiene_v1"
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
    policy = [ordered]@{
        ssot = "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
        claims_boundary_note = "docs/final/MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md"
        legacy_obsolete_handling = if ($AllowLegacyObsoleteSources) { "allowed_with_explicit_hypo_label" } else { "excluded_by_default" }
    }
    mandatory_labels = @("[FACT]", "[HYPO]", "[VISION]")
    reminder = "Historical/obsolete sources must be cited as [HYPO] historical reference, never as current [FACT]."
}
$hygiene | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $hygienePath -Encoding utf8
Write-Host "WROTE: $hygienePath" -ForegroundColor Green

$briefLines = @(
    "# Notebook Compression Daily Brief",
    "",
    "- generated_at_utc: $($status.generated_at_utc)",
    "- device_profile: $($status.inputs.device_profile)",
    "- include_obsidian_context: $($status.inputs.include_obsidian_context)",
    "- strict_mirror: $($status.inputs.strict_mirror)",
    "- allow_legacy_obsolete_sources: $($status.inputs.allow_legacy_obsolete_sources)",
    "- skip_notebook_dedupe: $($status.inputs.skip_notebook_dedupe)",
    "",
    "## Fact Boundary (Mandatory)",
    "- SSOT: docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "- Claims boundary note: docs/final/MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md",
    "- Historical/obsolete documents must be marked as [HYPO] historical reference, never as current [FACT].",
    "",
    "## Notebook Mirror",
    "- hub_b_weekly_mirror_exit_code: $($status.notebook.hub_b_weekly_mirror_exit_code)",
    "- hub_b_weekly_mirror_ts_utc: $($status.notebook.hub_b_weekly_mirror_ts_utc)",
    "",
    "## Notebook Dedupe",
    "- enabled: $($status.notebook_dedupe.enabled)",
    "- status: $($status.notebook_dedupe.status)",
    "",
    "## Compression Governance",
    "- go_no_go: $($status.compression.go_no_go)",
    "- rollout_policy: $($status.compression.rollout_policy)",
    "- track_a_jaccard_guardrail_ok: $($status.compression.track_a_jaccard_guardrail_ok)",
    "- track_b_literal_jaccard_guardrail_ok: $($status.compression.track_b_literal_jaccard_guardrail_ok)",
    "",
    "## RS Policy Gate",
    "- status: $($status.rs_policy_gate.status)",
    "- block_ratio: $($status.rs_policy_gate.block_ratio)",
    "- selected_profile: $($status.rs_policy_gate.selected_profile)",
    "",
    "## L1 Codebook Bypass Bench",
    "- status: $($status.l1_codebook_bypass_bench.status)",
    "- literal_exact_rate: $($status.l1_codebook_bypass_bench.literal_exact_rate)",
    "- literal_exact_min_required: $($status.l1_codebook_bypass_bench.literal_exact_min_required)",
    "- full_exact_rate: $($status.l1_codebook_bypass_bench.full_exact_rate)",
    "- soft_gate: $($status.l1_codebook_bypass_bench.soft_gate)",
    "- out_path: $($status.l1_codebook_bypass_bench.out_path)",
    "",
    "## L1 Permutation Side-Channel Spike",
    $l1SideChannelSpikeBriefLine,
    "",
    "## Notes",
    "- Research/operations chain only. No production auto-promotion.",
    "- If legacy/obsolete sources are intentionally enabled, add explicit [HYPO] and 'historical reference' markers in the notebook brief."
)
$briefLines -join "`r`n" | Set-Content -LiteralPath $briefPath -Encoding utf8
Write-Host "WROTE: $briefPath" -ForegroundColor Green

Write-Host "=== notebook+compression full chain OK ===" -ForegroundColor Green
exit 0
