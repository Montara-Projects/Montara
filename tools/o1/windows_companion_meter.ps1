# O1 ORBITA - Windows Companion process meter (opt-in, read-only).
# Works in Windows PowerShell 5.1 without Python, packages, Administrator or network.
# Does not capture command lines, usernames, file paths, token values or media contents.
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')]
    [string]$RunId = 'o1-stage-win-001',
    [ValidateRange(5,3600)]
    [int]$DurationSeconds = 600,
    [ValidateRange(1,10)]
    [int]$IntervalSeconds = 2,
    [string]$OutputPath = ''
)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $env:TEMP ('o1-companion-' + $RunId + '.json')
}
if (Test-Path -LiteralPath $OutputPath) {
    throw 'The output already exists. Choose a new RunId or OutputPath; existing reports are never overwritten.'
}
if (-not (Test-Path -LiteralPath (Split-Path -Parent $OutputPath) -PathType Container)) {
    throw 'The report directory does not exist.'
}
function Get-CompanionProcesses {
    # Metadata only, no command-line or executable-path fields.
    @(Get-CimInstance -ClassName Win32_Process -Property Name,ProcessId,ParentProcessId,CreationDate |
        Select-Object Name,ProcessId,ParentProcessId,CreationDate)
}
$all = Get-CompanionProcesses
$roots = @($all | Where-Object { $_.Name -eq 'Montara.Companion.Service.exe' })
if ($roots.Count -ne 1) {
    Write-Host ('Detected service processes: ' + $roots.Count)
    Write-Host 'Start the packaged Montara Companion and retry. No measurement or report was created.'
    throw 'Expected exactly one Montara.Companion.Service.exe process.'
}
$root = $roots[0]
$rootId = [int]$root.ProcessId
$rootStart = [string]$root.CreationDate
Write-Host ('O1 Companion located. PID: ' + $rootId)
Write-Host ('Measuring for up to ' + $DurationSeconds + ' seconds, every ' + $IntervalSeconds + ' seconds.')
Write-Host 'Use this window while following the normal Stage flow. No changes are made to Companion.'
$startedUtc = [DateTime]::UtcNow
$clock = [Diagnostics.Stopwatch]::StartNew()
$lastCpu = @{}
$cpuSeconds = 0.0
$rssPeak = [long]0
$rssMedianSamples = New-Object 'System.Collections.Generic.List[long]'
$samples = 0
$exited = $false
while ($clock.Elapsed.TotalSeconds -lt $DurationSeconds -or $samples -eq 0) {
    $all = Get-CompanionProcesses
    $liveRoot = @($all | Where-Object { [int]$_.ProcessId -eq $rootId -and [string]$_.CreationDate -eq $rootStart })
    if ($liveRoot.Count -ne 1) {
        $exited = $true
        break
    }
    $ids = New-Object 'System.Collections.Generic.HashSet[int]'
    [void]$ids.Add($rootId)
    $changed = $true
    while ($changed) {
        $changed = $false
        foreach ($item in $all) {
            $id = [int]$item.ProcessId
            if (-not $ids.Contains($id) -and $ids.Contains([int]$item.ParentProcessId)) {
                [void]$ids.Add($id)
                $changed = $true
            }
        }
    }
    $currentCpu = @{}
    $rss = [long]0
    foreach ($id in $ids) {
        try {
            $p = Get-Process -Id $id -ErrorAction Stop
            $key = [string]$id + ':' + [string]$p.StartTime.ToUniversalTime().Ticks
            $cpu = [double]$p.CPU
            $rss += [long]$p.WorkingSet64
            if ($lastCpu.ContainsKey($key)) {
                $cpuSeconds += [Math]::Max(0.0, $cpu - [double]$lastCpu[$key])
            }
            $currentCpu[$key] = $cpu
        } catch {
            # A child may exit between inventory and sampling.
        }
    }
    $lastCpu = $currentCpu
    if ($rss -gt $rssPeak) { $rssPeak = $rss }
    $rssMedianSamples.Add($rss)
    $samples++
    $remaining = [Math]::Max(0.0, $DurationSeconds - $clock.Elapsed.TotalSeconds)
    if ($remaining -gt 0) {
        Start-Sleep -Milliseconds ([int]([Math]::Min($remaining, $IntervalSeconds) * 1000))
    }
}
$clock.Stop()
$endedUtc = [DateTime]::UtcNow
$orderedRss = @($rssMedianSamples | Sort-Object)
$medianRss = $null
if ($orderedRss.Count -gt 0) {
    $medianRss = [long]$orderedRss[[int][Math]::Floor(($orderedRss.Count - 1) / 2)]
}
$report = [ordered]@{
    schema = 'urano-distributed-node-v1'
    run_id = $RunId
    host_label = 'win-o1'
    host_label_source = 'operator-self-declared-not-verified'
    role = 'client_companion'
    scenario_clients = 1
    project_count = 1
    workload = 'controlled-real'
    platform = 'windows'
    logical_cpus = [Environment]::ProcessorCount
    started_at_utc = $startedUtc.ToString('o')
    ended_at_utc = $endedUtc.ToString('o')
    sample = [ordered]@{
        method = 'psutil-pid-tree-sampled'
        observation_seconds = [Math]::Round($clock.Elapsed.TotalSeconds,3)
        samples = $samples
        root_exited_during_observation = $exited
        cpu_seconds_observed_lower_bound = [Math]::Round($cpuSeconds,3)
        rss_bytes_sampled_peak = $rssPeak
        rss_bytes_sampled_median = $medianRss
    }
    transport = [ordered]@{
        proxy_upload_bytes = $null
        recipe_download_bytes = $null
        original_upload_bytes = $null
        latency_ms_p50 = $null
    }
    remote_server_verified = $false
    physical_machine_distinctness_verified = $false
    no_media_or_secrets_collected = $true
    measurement_implementation = 'powershell-cim-getprocess'
}
# Use an exclusive new-file handle to avoid accidental replacement.
$json = $report | ConvertTo-Json -Depth 8
$bytes = [Text.Encoding]::UTF8.GetBytes($json + [Environment]::NewLine)
$file = [IO.File]::Open($OutputPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
try { $file.Write($bytes, 0, $bytes.Length) } finally { $file.Dispose() }
Write-Host ('O1 report created: ' + $OutputPath)
Write-Host ('Samples: ' + $samples + '; observed CPU-s: ' + [Math]::Round($cpuSeconds,3))
Write-Host 'This report does not prove network bytes or completed end-to-end rendering.'
