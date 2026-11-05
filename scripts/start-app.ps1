<#
.SYNOPSIS
    Starts (or stops) the local TruthLens app so the browser stops saying
    ERR_CONNECTION_REFUSED.

.DESCRIPTION
    Nothing in this project auto-starts: the Next.js server on :3000 and the
    FastAPI server on :8000 have to be running before you open a URL, and both
    die on a reboot. This script launches them as independent background
    processes (they survive this window closing), skips anything already
    listening so you never get a duplicate, and prints the URLs.

    Ports are held in RAM. On a small machine stop them again with -Stop when
    you are done; -Status shows what is up right now.

.EXAMPLE
    .\scripts\start-app.ps1              # start whatever is missing
    .\scripts\start-app.ps1 -Status      # just report
    .\scripts\start-app.ps1 -Stop        # kill both by owning PID
#>
[CmdletBinding()]
param(
    [switch]$Stop,
    [switch]$Status
)

$ErrorActionPreference = 'Stop'

$root    = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python  = Join-Path $root '.venv\Scripts\python.exe'
$nextBin = Join-Path $frontend 'node_modules\next\dist\bin\next'
$logDir  = Join-Path $env:TEMP 'truthlens'          # outside the repo: keeps git status clean

$apiPort = 8000
$webPort = 3000

function Get-PortOwner([int]$port) {
    $c = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
         Select-Object -First 1
    if ($c) { return $c.OwningProcess }
    return $null
}

function Stop-One([string]$name, [int]$port) {
    # $PID is read-only in PowerShell, so use $owner.
    $owner = Get-PortOwner $port
    if ($owner) {
        Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue
        Write-Host ("  stopped {0} (pid {1})" -f $name, $owner) -ForegroundColor Yellow
    } else {
        Write-Host ("  {0} was not running" -f $name) -ForegroundColor DarkGray
    }
}

function Show-Status {
    foreach ($row in @(
        @{ n = 'backend  FastAPI'; p = $apiPort; u = "http://localhost:$apiPort/docs" },
        @{ n = 'frontend Next.js'; p = $webPort; u = "http://localhost:$webPort/analyze" }
    )) {
        $owner = Get-PortOwner $row.p
        if ($owner) {
            Write-Host ("  {0} : port {1} LISTENING (pid {2})  -> {3}" -f $row.n, $row.p, $owner, $row.u) -ForegroundColor Green
        } else {
            Write-Host ("  {0} : port {1} down" -f $row.n, $row.p) -ForegroundColor Red
        }
    }
}

if ($Stop) {
    Write-Host 'Stopping TruthLens servers:' -ForegroundColor Cyan
    Stop-One 'frontend' $webPort
    Stop-One 'backend'  $apiPort
    return
}

if ($Status) {
    Write-Host 'TruthLens server status:' -ForegroundColor Cyan
    Show-Status
    return
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# ---------------------------------------------------------------- preflight --
$problems = @()
if (-not (Test-Path $python)) {
    $problems += "venv python not found at $python - create it first (see README setup)."
}
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    $problems += "node is not on PATH - install Node.js 18+ or start the backend only."
}
if (Test-Path $nextBin) {
    if (-not (Test-Path (Join-Path $frontend '.next\BUILD_ID'))) {
        $problems += "frontend has no production build - run:  cd frontend; npm run build"
    }
} else {
    $problems += "next binary not found at $nextBin - run:  cd frontend; npm install"
}
if ($problems.Count -gt 0) {
    Write-Host 'Cannot start everything:' -ForegroundColor Red
    $problems | ForEach-Object { Write-Host ("  - " + $_) -ForegroundColor Red }
    Write-Host 'Fix the lines above, then run this script again.' -ForegroundColor Yellow
    exit 1
}

# ------------------------------------------------------------------ backend --
if (Get-PortOwner $apiPort) {
    Write-Host ("backend  already listening on :{0} - left alone" -f $apiPort) -ForegroundColor DarkGray
} else {
    Start-Process -FilePath $python `
        -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', $apiPort) `
        -WorkingDirectory $backend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir 'uvicorn.out.log') `
        -RedirectStandardError  (Join-Path $logDir 'uvicorn.err.log')
    Write-Host ("backend  starting on :{0} (models load in a few seconds)" -f $apiPort)
}

# ----------------------------------------------------------------- frontend --
if (Get-PortOwner $webPort) {
    Write-Host ("frontend already listening on :{0} - left alone" -f $webPort) -ForegroundColor DarkGray
} else {
    $env:NODE_OPTIONS = '--max-old-space-size=2048'   # this machine is RAM-tight
    # the repo path contains spaces, so the script path needs embedded quotes
    Start-Process -FilePath $node.Source `
        -ArgumentList @(('"' + $nextBin + '"'), 'start', '-p', $webPort) `
        -WorkingDirectory $frontend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir 'next.out.log') `
        -RedirectStandardError  (Join-Path $logDir 'next.err.log')
    Write-Host ("frontend starting on :{0}" -f $webPort)
}

# -------------------------------------------------------------- readiness ----
Write-Host 'Waiting for both to answer...' -ForegroundColor DarkGray
$deadline = (Get-Date).AddSeconds(60)
$ready = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    try {
        $h = Invoke-RestMethod ("http://127.0.0.1:{0}/api/health" -f $apiPort) -TimeoutSec 5
        $w = Invoke-WebRequest  "http://127.0.0.1:$webPort/analyze" -UseBasicParsing -TimeoutSec 8
        if ($h.status -eq 'ok' -and $w.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
}

Write-Host ''
if ($ready) {
    Write-Host 'TruthLens is up. Open:' -ForegroundColor Green
    Write-Host ("  app     http://localhost:{0}/analyze" -f $webPort) -ForegroundColor Green
    Write-Host ("  api doc http://localhost:{0}/docs"    -f $apiPort) -ForegroundColor Green
    Write-Host ("  health  http://localhost:{0}/api/health" -f $apiPort) -ForegroundColor Green
    Write-Host ("  pages   /batch  /model-lab  /history  /how-it-works") -ForegroundColor DarkGray
    Write-Host ''
    Write-Host 'The UI build is in mock mode (NEXT_PUBLIC_USE_MOCK=true in frontend\.env.local),' -ForegroundColor DarkGray
    Write-Host 'so it simulates responses in the browser. To hit the real API, set it to false' -ForegroundColor DarkGray
    Write-Host 'and rebuild:  cd frontend; npm run build' -ForegroundColor DarkGray
    Write-Host ("Logs: {0}" -f $logDir) -ForegroundColor DarkGray
    Write-Host 'Done? Run .\scripts\start-app.ps1 -Stop to free the RAM.' -ForegroundColor DarkGray
} else {
    Write-Host 'Still not answering after 60s. Check the logs:' -ForegroundColor Red
    Write-Host ("  {0}" -f (Join-Path $logDir 'uvicorn.err.log')) -ForegroundColor Red
    Write-Host ("  {0}" -f (Join-Path $logDir 'next.err.log')) -ForegroundColor Red
    Show-Status
}
