param(
    [string]$S2Dir = "",
    [string]$OutputName = "mkmlab_consistency_pro_master_latest.mp4",
    [switch]$WithNarration,
    [switch]$WithSubtitles,
    [switch]$WithSrtSubtitles,
    [switch]$WithEndCard,
    [double]$EndCardSec = 2.5,
    [string]$EndLogoPath = "data/분자한의학연구소로고.png",
    [string]$EndCardTitle = "MKM LAB",
    [string]$EndCardSubtitle = "Safe Today, Companion Tomorrow",
    [string]$EndCardFontFile = "",
    [double]$MasterGainDb = 14.0,
    [string]$ScenarioFile = "docs/final/artifacts/cinematic_scenario_sample_v1.txt",
    [string]$TtsVoice = "slt",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path

$AudioProfile = Join-Path $Root "docs\final\artifacts\athena_pro_audio_profile_v1.json"
$VideoProfile = Join-Path $Root "docs\final\artifacts\athena_pro_video_profile_v1.json"
$RenderScript = Join-Path $Root "scripts\render_s2_preset_v2.py"
$ProAudioScript = Join-Path $Root "scripts\cinematic\pro_audio_engine.py"
$ScenarioPath = if ([System.IO.Path]::IsPathRooted($ScenarioFile)) { $ScenarioFile } else { Join-Path $Root $ScenarioFile }
$EndLogoResolved = if ([System.IO.Path]::IsPathRooted($EndLogoPath)) { $EndLogoPath } else { Join-Path $Root $EndLogoPath }
$EndLogoFallback = Join-Path $Root "_hotfix_deploy\projects\mkm\mkm-life\public\mkmlife-logo.png"

function Test-S2Ready {
    param([string]$Dir)
    if (-not (Test-Path $Dir)) { return $false }
    $clips = Join-Path $Dir "clips"
    $audio = Join-Path $Dir "audio\bgm.wav"
    if (-not (Test-Path $clips)) { return $false }
    $shotCount = (Get-ChildItem $clips -Filter "shot_*.mp4" -File -ErrorAction SilentlyContinue | Measure-Object).Count
    return ($shotCount -ge 3 -and (Test-Path $audio))
}

function Resolve-S2Dir {
    param([string]$UserS2)
    if ($UserS2 -and $UserS2.Trim().Length -gt 0) {
        if ([System.IO.Path]::IsPathRooted($UserS2)) { return $UserS2 }
        return (Join-Path $Root $UserS2)
    }

    $preferred = @(
        (Join-Path $Root "docs\final\artifacts\cinematic_s2_input_editor_v1_consistency"),
        (Join-Path $Root "docs\final\artifacts\cinematic_s2_input_editor_v1"),
        (Join-Path $Root "docs\final\artifacts\cinematic_s2_input")
    )
    foreach ($p in $preferred) {
        if (Test-S2Ready $p) { return $p }
    }

    $art = Join-Path $Root "docs\final\artifacts"
    $dirs = Get-ChildItem $art -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "cinematic_s2_input*" } |
        Sort-Object LastWriteTime -Descending
    foreach ($d in $dirs) {
        if (Test-S2Ready $d.FullName) { return $d.FullName }
    }
    throw "No render-ready cinematic S2 directory found under docs/final/artifacts."
}

function Convert-ToFfmpegTextPath {
    param([string]$PathLike)
    $p = $PathLike.Replace("\", "/")
    if ($p.Length -gt 1 -and $p[1] -eq ":") {
        $p = $p.Substring(0, 1) + "\:" + $p.Substring(2)
    }
    return $p
}

function Format-SrtTimestampFromMs {
    param([int]$TotalMs)
    $totalMs = [Math]::Max(0, $TotalMs)
    $h = [int][Math]::Floor($totalMs / 3600000)
    $m = [int][Math]::Floor(($totalMs % 3600000) / 60000)
    $s = [int][Math]::Floor(($totalMs % 60000) / 1000)
    $ms = [int]($totalMs % 1000)
    return ("{0:D2}:{1:D2}:{2:D2},{3:D3}" -f $h, $m, $s, $ms)
}

# ASS timestamps: H:MM:SS.cc (centiseconds)
function Format-AssTimestampFromMs {
    param([int]$TotalMs)
    $totalMs = [Math]::Max(0, $TotalMs)
    $h = [int][Math]::Floor($totalMs / 3600000)
    $m = [int][Math]::Floor(($totalMs % 3600000) / 60000)
    $s = [int][Math]::Floor(($totalMs % 60000) / 1000)
    $cs = [int][Math]::Floor(($totalMs % 1000) / 10)
    return ("{0}:{1:D2}:{2:D2}.{3:D2}" -f $h, $m, $s, $cs)
}

function Escape-AssDialogueText {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    # ASS text field is the last field in Dialogue; commas do not need escaping here.
    # Escaping comma produced visible backslash-glyph artifacts in some renderers.
    return $Text.Replace('\', '\\').Replace("`r`n", "\N").Replace("`n", "\N")
}

function Resolve-EndCardFontPath {
    param([string]$Candidate)
    if ($Candidate -and (Test-Path -LiteralPath $Candidate)) {
        return $Candidate
    }
    $winFonts = ${env:WINDIR}
    if (-not $winFonts) { $winFonts = "C:\Windows" }
    foreach ($name in @("malgunbd.ttf", "malgun.ttf", "arialbd.ttf", "arial.ttf")) {
        $p = Join-Path $winFonts "Fonts\$name"
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}

function Convert-ToFfmpegFilterPath {
    param([string]$PathLike)
    # drawtext/fontfile uses ':' as option separator — escape drive colon
    $p = $PathLike.Replace("\", "/")
    if ($p.Length -gt 1 -and $p[1] -eq ":") {
        $p = $p.Substring(0, 1) + "\:" + $p.Substring(2)
    }
    return $p.Replace("'", "\\'")
}

$ResolvedS2 = Resolve-S2Dir -UserS2 $S2Dir
if (-not (Test-S2Ready $ResolvedS2)) {
    throw "S2 directory is not render-ready (need clips/shot_*.mp4 and audio/bgm.wav): $ResolvedS2"
}

Write-Host "[mkmlab] S2 dir: $ResolvedS2"
Write-Host "[mkmlab] Output : $OutputName"
Write-Host "[mkmlab] DryRun : $DryRun"

$clipsDir = Join-Path $ResolvedS2 "clips"
$audioDir = Join-Path $ResolvedS2 "audio"
$subsDir = Join-Path $ResolvedS2 "subtitles"
$clipFiles = Get-ChildItem $clipsDir -Filter "shot_*.mp4" -File | Sort-Object Name
$clipCount = ($clipFiles | Measure-Object).Count
if ($clipCount -lt 1) { throw "No shot_*.mp4 clips found in $clipsDir" }

$shotDurationRaw = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $clipFiles[0].FullName
$shotDurationSec = [double]($shotDurationRaw | Select-Object -First 1)
if ($shotDurationSec -le 0.0) { $shotDurationSec = 8.0 }
$shotDurationMs = [Math]::Max(1, [int][Math]::Round($shotDurationSec * 1000.0))

if ($WithNarration -or $WithSubtitles) {
    if (-not (Test-Path $ScenarioPath)) {
        throw "Scenario file not found: $ScenarioPath"
    }
    $scenarioLines = Get-Content -Path $ScenarioPath -Encoding UTF8 | Where-Object { $_.Trim().Length -gt 0 }
    if (($scenarioLines | Measure-Object).Count -lt 1) {
        $scenarioLines = @("MKM LAB companion intelligence demo.")
    }
    $expandedLines = @()
    for ($i = 0; $i -lt $clipCount; $i++) {
        $expandedLines += $scenarioLines[$i % $scenarioLines.Count].Trim()
    }

    if ($WithNarration) {
        New-Item -ItemType Directory -Path $audioDir -Force | Out-Null
        $narrTextPath = Join-Path $audioDir "_narration_input.txt"
        ($expandedLines -join " ") + "`n" | Set-Content -Path $narrTextPath -Encoding UTF8
        $narrOut = Join-Path $audioDir "narration.wav"
        $ffTxt = Convert-ToFfmpegTextPath -PathLike $narrTextPath
        & ffmpeg -y -f lavfi -i "flite=textfile='$ffTxt':voice=$TtsVoice" -ar 48000 -ac 2 $narrOut | Out-Null
        Write-Host "[mkmlab] narration generated: $narrOut"
    }

    if ($WithSubtitles) {
        New-Item -ItemType Directory -Path $subsDir -Force | Out-Null
        if ($WithSrtSubtitles) {
            Remove-Item -Path (Join-Path $subsDir "main.ass") -ErrorAction SilentlyContinue
            $srtPath = Join-Path $subsDir "main.srt"
            $blocks = @()
            for ($i = 0; $i -lt $clipCount; $i++) {
                $t0ms = $i * $shotDurationMs
                $t1ms = ($i + 1) * $shotDurationMs
                $blocks += @(
                    ($i + 1).ToString(),
                    "$(Format-SrtTimestampFromMs $t0ms) --> $(Format-SrtTimestampFromMs $t1ms)",
                    $expandedLines[$i],
                    ""
                )
            }
            $blocks -join "`n" | Set-Content -Path $srtPath -Encoding UTF8
            Write-Host "[mkmlab] subtitles (SRT): $srtPath"
        } else {
            Remove-Item -Path (Join-Path $subsDir "main.srt") -ErrorAction SilentlyContinue
            $assPath = Join-Path $subsDir "main.ass"
            $assHeader = @"
[Script Info]
Title: MKM Lab
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Malgun Gothic,52,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,2,2,80,80,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"@
            $assLines = New-Object System.Collections.Generic.List[string]
            [void]$assLines.Add($assHeader.TrimEnd())
            for ($i = 0; $i -lt $clipCount; $i++) {
                $t0ms = $i * $shotDurationMs
                $t1ms = ($i + 1) * $shotDurationMs
                $esc = Escape-AssDialogueText $expandedLines[$i]
                $line = "Dialogue: 0,$(Format-AssTimestampFromMs $t0ms),$(Format-AssTimestampFromMs $t1ms),Default,,0,0,0,,${esc}"
                [void]$assLines.Add($line)
            }
            $utf8NoBom = New-Object System.Text.UTF8Encoding $false
            [System.IO.File]::WriteAllLines($assPath, $assLines.ToArray(), $utf8NoBom)
            Write-Host "[mkmlab] subtitles (ASS): $assPath"
        }
    }
}

if (-not $DryRun) {
    & py $ProAudioScript normalize-stems --audio-dir (Join-Path $ResolvedS2 "audio") --profile-json $AudioProfile
}

$cmd = @(
    "py", $RenderScript,
    "--input-dir", $ResolvedS2,
    "--ducking",
    "--output-name", $OutputName,
    "--audio-profile-json", $AudioProfile,
    "--video-profile-json", $VideoProfile
)
if ($DryRun) { $cmd += "--dry-run" }

Write-Host "[mkmlab] render cmd: $($cmd -join ' ')"
& $cmd[0] @($cmd[1..($cmd.Length - 1)])

$out = Join-Path $ResolvedS2 "output\$OutputName"
if ((-not $DryRun) -and $WithEndCard -and (Test-Path $out)) {
    $logoForCard = $EndLogoResolved
    if (-not (Test-Path -LiteralPath $logoForCard)) {
        if (Test-Path -LiteralPath $EndLogoFallback) {
            $logoForCard = $EndLogoFallback
            Write-Host "[mkmlab] end-card logo fallback: $logoForCard"
        }
    }
    if (-not (Test-Path -LiteralPath $logoForCard)) {
        Write-Host "[mkmlab] end-card skipped (no logo at primary or fallback): $EndLogoResolved"
    } else {
        $tmpDir = Join-Path $ResolvedS2 "output\_tmp_endcard"
        New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
        $slate = Join-Path $tmpDir "_end_slate.mp4"
        $mainNoExt = [System.IO.Path]::GetFileNameWithoutExtension($OutputName)
        $mainExt = [System.IO.Path]::GetExtension($OutputName)
        if (-not $mainExt) { $mainExt = ".mp4" }
        $body = Join-Path $ResolvedS2 "output\$mainNoExt.body$mainExt"
        Move-Item -Force $out $body

        $fontResolved = Resolve-EndCardFontPath -Candidate $EndCardFontFile
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        $titleFile = Join-Path $tmpDir "_end_title.txt"
        $subFile = Join-Path $tmpDir "_end_subtitle.txt"
        [System.IO.File]::WriteAllText($titleFile, ($EndCardTitle -replace "`r`n", " " -replace "`n", " ").Trim(), $utf8NoBom)
        [System.IO.File]::WriteAllText($subFile, ($EndCardSubtitle -replace "`r`n", " " -replace "`n", " ").Trim(), $utf8NoBom)

        # filter_complex: crop logo to monogram area (drop mkmlife text), then draw refined text
        if ($fontResolved -and ($EndCardTitle.Trim().Length -gt 0 -or $EndCardSubtitle.Trim().Length -gt 0)) {
            $chain = "[1:v]scale=760:-1,format=rgba,colorchannelmixer=aa=0.98[logo];[0:v][logo]overlay=(W-w)/2:H*0.34-h/2:format=auto[tmp];[tmp]drawbox=x=(iw-760)/2:y=390:w=760:h=230:color=0x0f172a@1:t=fill[base]"
            $last = "base"
            $next = 1
            if ($EndCardTitle.Trim().Length -gt 0) {
                $n = "t$next"; $next++
                $ffFont = (Convert-ToFfmpegFilterPath -PathLike $fontResolved)
                $ffTitle = (Convert-ToFfmpegFilterPath -PathLike $titleFile)
                $chain += ";[$last]drawtext=fontfile='$ffFont':textfile='$ffTitle':fontsize=56:fontcolor=white:x=(w-text_w)/2:y=h*0.62:borderw=2:bordercolor=black@0.55[$n]"
                $last = $n
            }
            if ($EndCardSubtitle.Trim().Length -gt 0) {
                $n = "t$next"
                $ffFont = (Convert-ToFfmpegFilterPath -PathLike $fontResolved)
                $ffSub = (Convert-ToFfmpegFilterPath -PathLike $subFile)
                $chain += ";[$last]drawtext=fontfile='$ffFont':textfile='$ffSub':fontsize=30:fontcolor=white@0.90:x=(w-text_w)/2:y=h*0.70:borderw=2:bordercolor=black@0.45[$n]"
                $last = $n
            }
            $chain += ";[$last]format=yuv420p[v]"
            $fc = $chain
        } else {
            if (-not $fontResolved) {
                Write-Host "[mkmlab] end-card: no font found; logo only (set -EndCardFontFile or install Malgun/Arial)."
            }
            $fc = "[1:v]scale=900:-1[logo];[0:v][logo]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p[v]"
        }

        & ffmpeg -y `
            -f lavfi -i "color=c=0x0f172a:s=1920x1080:d=$EndCardSec" `
            -i $logoForCard `
            -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=48000" `
            -filter_complex $fc `
            -map "[v]" -map "2:a" -t "$EndCardSec" `
            -r 30 -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k `
            $slate | Out-Null

        $concatList = Join-Path $tmpDir "_end_concat.txt"
        @(
            "file '$($body.Replace("'", "''").Replace('\','/'))'",
            "file '$($slate.Replace("'", "''").Replace('\','/'))'"
        ) | Set-Content -Path $concatList -Encoding Ascii

        & ffmpeg -y -f concat -safe 0 -i $concatList -c copy $out | Out-Null
        if (Test-Path $out) {
            Remove-Item -Force $body -ErrorAction SilentlyContinue
            Write-Host "[mkmlab] end-card appended (logo + optional text): $logoForCard"
        } else {
            Move-Item -Force $body $out
            Write-Host "[mkmlab] end-card failed; restored body render without end-card."
        }
    }
}

if (Test-Path $out) {
    if ((-not $DryRun) -and [Math]::Abs($MasterGainDb) -gt 0.01) {
        $mainNoExt = [System.IO.Path]::GetFileNameWithoutExtension($OutputName)
        $mainExt = [System.IO.Path]::GetExtension($OutputName)
        if (-not $mainExt) { $mainExt = ".mp4" }
        $gainTmp = Join-Path $ResolvedS2 "output\$mainNoExt.gain$mainExt"
        & ffmpeg -y `
            -i $out `
            -map 0:v -map 0:a `
            -c:v copy `
            -af "volume=${MasterGainDb}dB,alimiter=limit=0.95:level=disabled" `
            -c:a aac -b:a 192k `
            $gainTmp | Out-Null
        if (Test-Path $gainTmp) {
            Move-Item -Force $gainTmp $out
            Write-Host "[mkmlab] master gain applied: +$MasterGainDb dB"
        } else {
            Write-Host "[mkmlab] master gain step failed, keeping previous mix."
        }
    }
    Write-Host "[mkmlab] done: $out"
} else {
    Write-Host "[mkmlab] completed (dry-run or output name differs)."
}
